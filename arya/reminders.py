import os
import pickle
from datetime import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
REMINDERS_SHEET = "Reminders"


def get_sheets_service():
    creds = None
    if os.path.exists('token_sheets.pickle'):
        with open('token_sheets.pickle', 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    return build('sheets', 'v4', credentials=creds)


def _ensure_reminders_sheet():
    try:
        service = get_sheets_service()
        meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheets = [s['properties']['title'] for s in meta['sheets']]
        if REMINDERS_SHEET not in sheets:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": REMINDERS_SHEET}}}]}
            ).execute()
            service.spreadsheets().values().update(
                spreadsheetId=SHEET_ID,
                range=f"{REMINDERS_SHEET}!A1:D1",
                valueInputOption='RAW',
                body={'values': [['date', 'time', 'message', 'done']]}
            ).execute()
    except Exception:
        pass


def save_reminder(date_str: str, time_str: str, message: str) -> str:
    """Save a reminder. date_str = YYYY-MM-DD, time_str = HH:MM or empty."""
    try:
        _ensure_reminders_sheet()
        service = get_sheets_service()
        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"{REMINDERS_SHEET}!A:D",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [[date_str, time_str or "09:00", message, "no"]]}
        ).execute()
        time_part = f" at {time_str}" if time_str else ""
        return f"✅ Reminder set for *{date_str}{time_part}*\n📝 {message}"
    except Exception as e:
        return f"❌ Could not save reminder: {str(e)}"


def get_todays_reminders() -> list:
    """Return all reminders for today that are not done."""
    try:
        _ensure_reminders_sheet()
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{REMINDERS_SHEET}!A:D"
        ).execute()
        rows = result.get('values', [])
        today = datetime.now().strftime('%Y-%m-%d')
        due = []
        for i, row in enumerate(rows[1:], start=2):  # skip header, 1-indexed
            if len(row) >= 3 and row[0] == today and (len(row) < 4 or row[3] != "yes"):
                due.append({"row": i, "date": row[0], "time": row[1], "message": row[2]})
        return due
    except Exception:
        return []


def mark_reminder_done(row_index: int) -> None:
    try:
        service = get_sheets_service()
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{REMINDERS_SHEET}!D{row_index}",
            valueInputOption='RAW',
            body={'values': [['yes']]}
        ).execute()
    except Exception:
        pass


def get_all_pending_reminders() -> str:
    """Return all future/pending reminders as a formatted string."""
    try:
        _ensure_reminders_sheet()
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{REMINDERS_SHEET}!A:D"
        ).execute()
        rows = result.get('values', [])
        today = datetime.now().strftime('%Y-%m-%d')
        pending = [
            row for row in rows[1:]
            if len(row) >= 3 and row[0] >= today and (len(row) < 4 or row[3] != "yes")
        ]
        if not pending:
            return "✅ No pending reminders."
        lines = ["🔔 *Your upcoming reminders:*\n"]
        for row in sorted(pending, key=lambda r: r[0]):
            lines.append(f"📅 {row[0]} {row[1]} — {row[2]}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Could not fetch reminders: {str(e)}"
