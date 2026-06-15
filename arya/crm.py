import os
import pickle
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
RANGE = "Sheet1!A:H"

# Column mapping
COLUMNS = {
    "name": 0,
    "email": 1,
    "phone": 2,
    "status": 3,
    "last_contact": 4,
    "next_followup": 5,
    "no_show_count": 6,
    "notes": 7
}


def get_sheets_service():
    """Authenticate and return Google Sheets service"""
    creds = None
    if os.path.exists('token_sheets.pickle'):
        with open('token_sheets.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token_sheets.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('sheets', 'v4', credentials=creds)


def get_all_leads() -> list:
    """Get all leads from Google Sheet"""
    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=RANGE
        ).execute()
        return result.get('values', [])
    except Exception as e:
        return []


def find_lead(name: str) -> tuple:
    """Find a lead by name and return (row_index, lead_data)"""
    leads = get_all_leads()
    for i, row in enumerate(leads):
        if row and row[0].lower() == name.lower():
            return i + 1, row  # +1 because sheets are 1-indexed
    return None, None


def add_lead(name: str, email: str = "", phone: str = "", status: str = "New") -> str:
    """Add a new lead to Google Sheet"""
    try:
        # Check if lead already exists
        _, existing = find_lead(name)
        if existing:
            return f"⚠️ Lead '{name}' already exists in CRM. Use update to change their info."

        service = get_sheets_service()
        today = datetime.now().strftime('%d/%m/%Y')

        new_row = [
            name,
            email,
            phone,
            status,
            today,   # last_contact = today
            "",      # next_followup
            "0",     # no_show_count
            ""       # notes
        ]

        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range="Sheet1!A:H",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [new_row]}
        ).execute()

        return f"✅ New lead added: *{name}*\n📧 {email or 'No email'} | 📞 {phone or 'No phone'} | Status: {status}"
    except Exception as e:
        return f"❌ Error adding lead: {str(e)}"


def update_lead_status(name: str, status: str) -> str:
    """Update lead status"""
    try:
        row_index, lead = find_lead(name)
        if not lead:
            return f"❌ Lead '{name}' not found in CRM"

        service = get_sheets_service()
        today = datetime.now().strftime('%d/%m/%Y')

        # Update status and last_contact date
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SHEET_ID,
            body={
                'valueInputOption': 'RAW',
                'data': [
                    {'range': f"Sheet1!D{row_index}", 'values': [[status]]},
                    {'range': f"Sheet1!E{row_index}", 'values': [[today]]},
                ]
            }
        ).execute()

        return f"✅ *{name}* status updated to *{status}*"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def add_note(name: str, note: str) -> str:
    """Add a note to a lead"""
    try:
        row_index, lead = find_lead(name)
        if not lead:
            return f"❌ Lead '{name}' not found in CRM"

        service = get_sheets_service()

        # Append to existing notes
        existing_notes = lead[COLUMNS["notes"]] if len(lead) > COLUMNS["notes"] else ""
        today = datetime.now().strftime('%d/%m/%Y')
        new_note = f"{today}: {note}"
        updated_notes = f"{existing_notes}\n{new_note}".strip() if existing_notes else new_note

        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SHEET_ID,
            body={
                'valueInputOption': 'RAW',
                'data': [
                    {'range': f"Sheet1!H{row_index}", 'values': [[updated_notes]]},
                    {'range': f"Sheet1!E{row_index}", 'values': [[today]]},  # update last_contact
                ]
            }
        ).execute()

        return f"✅ Note added for *{name}*"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def set_next_followup(name: str, date_str: str) -> str:
    """Set next follow-up date for a lead"""
    try:
        row_index, lead = find_lead(name)
        if not lead:
            return f"❌ Lead '{name}' not found in CRM"

        service = get_sheets_service()
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"Sheet1!F{row_index}",
            valueInputOption='RAW',
            body={'values': [[date_str]]}
        ).execute()

        return f"✅ Next follow-up for *{name}* set to {date_str}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def get_todays_followups() -> list:
    """Get all leads that need follow-up today"""
    today = datetime.now().strftime('%d/%m/%Y')
    leads = get_all_leads()
    due_today = []

    for row in leads[1:]:  # Skip header row
        if len(row) > COLUMNS["next_followup"]:
            if row[COLUMNS["next_followup"]] == today:
                due_today.append(row)

    return due_today


def get_lead_details(name: str) -> str:
    """Get full details of a lead"""
    row_index, lead = find_lead(name)
    if not lead:
        return f"❌ Lead '{name}' not found in CRM"

    details = f"""
📋 *Lead: {lead[0]}*

📧 Email: {lead[1] if len(lead) > 1 and lead[1] else 'Not set'}
📞 Phone: {lead[2] if len(lead) > 2 and lead[2] else 'Not set'}
📊 Status: {lead[3] if len(lead) > 3 and lead[3] else 'Not set'}
📅 Last Contact: {lead[4] if len(lead) > 4 and lead[4] else 'Never'}
🔔 Next Follow-up: {lead[5] if len(lead) > 5 and lead[5] else 'Not set'}
❌ No-shows: {lead[6] if len(lead) > 6 and lead[6] else '0'}
📝 Notes: {lead[7] if len(lead) > 7 and lead[7] else 'None'}
"""
    return details.strip()


def get_leads_by_status(status_filter: str = "all") -> list:
    """Get leads filtered by status. Pass 'all' for all leads."""
    leads = get_all_leads()
    rows = leads[1:]  # skip header

    if status_filter.lower() == "all":
        return [row for row in rows if len(row) > 1 and row[1]]  # must have email

    return [
        row for row in rows
        if len(row) > 3
        and row[3].strip().lower() == status_filter.strip().lower()
        and len(row) > 1 and row[1]  # must have email
    ]


def bulk_update_status(updates: list) -> str:
    """Update status for multiple leads. updates = [(name, status), ...]"""
    try:
        service = get_sheets_service()
        leads = get_all_leads()
        today = datetime.now().strftime('%d/%m/%Y')
        results = []
        data = []
        for name, status in updates:
            for i, row in enumerate(leads):
                if row and row[0].lower() == name.lower():
                    row_index = i + 1
                    data.append({'range': f"Sheet1!D{row_index}", 'values': [[status]]})
                    data.append({'range': f"Sheet1!E{row_index}", 'values': [[today]]})
                    results.append(f"✅ {row[0]} → {status}")
                    break
            else:
                results.append(f"❌ {name} not found")
        if data:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={'valueInputOption': 'RAW', 'data': data}
            ).execute()
        return "\n".join(results)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def add_column(column_name: str) -> str:
    """Add a new column header to the CRM sheet."""
    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="Sheet1!1:1"
        ).execute()
        headers = result.get('values', [[]])[0]
        # Check if column already exists
        if column_name.lower() in [h.lower() for h in headers]:
            return f"⚠️ Column *{column_name}* already exists in the sheet."
        # Append new header at end
        next_col_index = len(headers) + 1
        col_letter = chr(ord('A') + len(headers))  # works up to column Z
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"Sheet1!{col_letter}1",
            valueInputOption='RAW',
            body={'values': [[column_name]]}
        ).execute()
        return f"✅ Column *{column_name}* added to your CRM sheet!"
    except Exception as e:
        return f"❌ Error adding column: {str(e)}"


def get_crm_summary() -> str:
    """Get a summary count of all leads by status"""
    leads = get_all_leads()
    rows = leads[1:]  # skip header

    if not rows:
        return "📊 CRM is empty — no leads yet."

    total = len(rows)
    status_counts = {}
    for row in rows:
        status = row[3].strip().title() if len(row) > 3 and row[3] else "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1

    lines = [f"📊 *CRM Summary — {total} leads total*"]
    for status, count in sorted(status_counts.items()):
        lines.append(f"• {status}: {count}")

    return "\n".join(lines)
