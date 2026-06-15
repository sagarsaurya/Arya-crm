import os
import json
import pickle
from datetime import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
MEMORY_SHEET = "Memory"


def get_sheets_service():
    creds = None
    if os.path.exists('token_sheets.pickle'):
        with open('token_sheets.pickle', 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    return build('sheets', 'v4', credentials=creds)


def _ensure_memory_sheet():
    """Create the Memory sheet if it doesn't exist."""
    try:
        service = get_sheets_service()
        sheet_meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheets = [s['properties']['title'] for s in sheet_meta['sheets']]
        if MEMORY_SHEET not in sheets:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": MEMORY_SHEET}}}]}
            ).execute()
            # Write header
            service.spreadsheets().values().update(
                spreadsheetId=SHEET_ID,
                range=f"{MEMORY_SHEET}!A1:B1",
                valueInputOption='RAW',
                body={'values': [['key', 'value']]}
            ).execute()
    except Exception:
        pass


def load_memory() -> dict:
    """Load all memory from the Memory sheet as a dict."""
    try:
        _ensure_memory_sheet()
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{MEMORY_SHEET}!A:B"
        ).execute()
        rows = result.get('values', [])
        memory = {}
        for row in rows[1:]:  # skip header
            if len(row) >= 2:
                key = row[0]
                try:
                    memory[key] = json.loads(row[1])
                except Exception:
                    memory[key] = row[1]
        return memory
    except Exception:
        return {}


def save_memory(key: str, value) -> None:
    """Save or update a single memory key."""
    try:
        _ensure_memory_sheet()
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{MEMORY_SHEET}!A:B"
        ).execute()
        rows = result.get('values', [])

        # Find existing row for this key
        row_num = None
        for i, row in enumerate(rows):
            if row and row[0] == key:
                row_num = i + 1  # 1-indexed
                break

        serialized = json.dumps(value) if not isinstance(value, str) else value

        if row_num:
            service.spreadsheets().values().update(
                spreadsheetId=SHEET_ID,
                range=f"{MEMORY_SHEET}!B{row_num}",
                valueInputOption='RAW',
                body={'values': [[serialized]]}
            ).execute()
        else:
            service.spreadsheets().values().append(
                spreadsheetId=SHEET_ID,
                range=f"{MEMORY_SHEET}!A:B",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [[key, serialized]]}
            ).execute()
    except Exception:
        pass


def remember_lead(name: str, intent: str) -> None:
    """Remember the last lead discussed and the intent."""
    save_memory("last_lead", name)
    save_memory("last_intent", intent)
    save_memory("last_updated", datetime.now().strftime('%Y-%m-%d %H:%M'))


def get_last_lead() -> str:
    """Get the last lead that was discussed."""
    memory = load_memory()
    return memory.get("last_lead", "")
