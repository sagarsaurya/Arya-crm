import os
import pickle
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

COLUMNS = {"name": 0, "email": 1, "phone": 2, "status": 3,
           "last_contact": 4, "next_followup": 5, "no_show_count": 6, "notes": 7}


def get_sheets_service():
    creds = None
    if os.path.exists('token_sheets.pickle'):
        with open('token_sheets.pickle', 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    return build('sheets', 'v4', credentials=creds)


def _parse_date(date_str: str):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except Exception:
            pass
    return None


def _score_lead(lead: list, today: datetime) -> tuple:
    """Score a lead for urgency. Higher = more urgent."""
    score = 0
    reason = []

    status = lead[COLUMNS["status"]].strip().lower() if len(lead) > 3 and lead[3] else ""
    if status == "hot":
        score += 40
    elif status == "warm":
        score += 20

    # Follow-up due today or overdue
    followup_str = lead[COLUMNS["next_followup"]] if len(lead) > 5 else ""
    if followup_str:
        followup_date = _parse_date(followup_str)
        if followup_date:
            days_diff = (today - followup_date).days
            if days_diff == 0:
                score += 50
                reason.append("follow-up due today")
            elif days_diff > 0:
                score += 40 + days_diff
                reason.append(f"follow-up overdue {days_diff} day{'s' if days_diff > 1 else ''}")

    # Last contact
    last_str = lead[COLUMNS["last_contact"]] if len(lead) > 4 else ""
    if last_str:
        last_date = _parse_date(last_str)
        if last_date:
            days_since = (today - last_date).days
            if days_since >= 7:
                score += 15
                reason.append(f"no contact {days_since} days")
    elif status in ("hot", "warm"):
        score += 10
        reason.append("never contacted")

    return score, reason


def build_morning_message() -> str:
    """Build the smart morning briefing message."""
    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range="Sheet1!A:H"
        ).execute()
        rows = result.get('values', [])[1:]  # skip header
    except Exception as e:
        return f"☀️ Good morning Sagar!\n\n❌ Could not load CRM: {str(e)}"

    today = datetime.now()
    today_str = today.strftime('%d/%m/%Y')

    # Count by status
    status_counts = {}
    for row in rows:
        s = row[3].strip().title() if len(row) > 3 and row[3] else "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1

    total = len(rows)

    # Score every lead
    scored = []
    for lead in rows:
        if not lead or not lead[0]:
            continue
        score, reasons = _score_lead(lead, today)
        if score > 0:
            scored.append((score, lead, reasons))

    scored.sort(key=lambda x: x[0], reverse=True)
    top5 = scored[:5]

    # Follow-ups due today
    followups_today = [
        r for r in rows
        if len(r) > 5 and r[5] and _parse_date(r[5]) and _parse_date(r[5]).strftime('%d/%m/%Y') == today_str
    ]

    # Build message
    lines = [f"☀️ *Good morning Sagar!*\n"]
    lines.append(f"📊 *CRM: {total:,} leads*")

    status_line = " | ".join([f"{s}: {c}" for s, c in sorted(status_counts.items())])
    lines.append(f"_{status_line}_\n")

    if top5:
        lines.append("🎯 *Top 5 to action today:*")
        for i, (score, lead, reasons) in enumerate(top5, 1):
            name = lead[0]
            status = lead[3].strip().title() if len(lead) > 3 and lead[3] else ""
            reason_str = ", ".join(reasons) if reasons else "high priority"
            emoji = "🔥" if status.lower() == "hot" else "🌡️"
            lines.append(f"{i}. {emoji} *{name}* — {reason_str}")
        lines.append("")

    if followups_today:
        lines.append(f"🔔 *{len(followups_today)} follow-up{'s' if len(followups_today) > 1 else ''} due today*")
        for r in followups_today[:3]:
            lines.append(f"  • {r[0]}")
        if len(followups_today) > 3:
            lines.append(f"  _...and {len(followups_today) - 3} more_")
        lines.append("")

    lines.append("_Type /help to see all commands_ 💪")

    return "\n".join(lines)
