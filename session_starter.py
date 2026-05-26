from datetime import datetime


def get_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


def get_crm_snapshot() -> str:
    try:
        from arya.crm import get_all_leads
        all_leads = get_all_leads()
        rows = all_leads[1:]  # skip header

        total = len(rows)
        if total == 0:
            return "📊 CRM is empty — no leads yet."

        status_counts = {}
        for row in rows:
            status = row[3].strip().title() if len(row) > 3 and row[3] else "Unknown"
            status_counts[status] = status_counts.get(status, 0) + 1

        lines = [f"📊 *CRM Snapshot — {total} leads total*"]
        for status, count in sorted(status_counts.items()):
            lines.append(f"• {status}: {count}")

        return "\n".join(lines)
    except Exception:
        return "📊 CRM: Connect Google Sheets to see data"


def get_meetings_snapshot() -> str:
    try:
        from arya.calendar_agent import get_todays_meetings
        return get_todays_meetings()
    except Exception:
        return "📅 Calendar: Connect Google Calendar to see meetings"


def get_followups_snapshot() -> str:
    try:
        from arya.crm import get_todays_followups
        followups = get_todays_followups()
        if followups:
            lines = [f"🔔 *Follow-ups Today — {len(followups)} due:*"]
            for lead in followups:
                name = lead[0] if lead else "Unknown"
                status = lead[3] if len(lead) > 3 else "—"
                lines.append(f"• {name} ({status})")
            return "\n".join(lines)
        else:
            return "🔔 No follow-ups due today"
    except Exception:
        return "🔔 Follow-ups: Connect Google Sheets to see data"


def build_session_message() -> str:
    today = datetime.now().strftime("%A, %d %B %Y")
    greeting = get_greeting()

    meetings = get_meetings_snapshot()
    followup_text = get_followups_snapshot()
    snapshot = get_crm_snapshot()

    message = f"""
👋 *{greeting}, Sagar!*
📅 {today}

━━━━━━━━━━━━━━━━━━━━
{meetings}

━━━━━━━━━━━━━━━━━━━━
{followup_text}

━━━━━━━━━━━━━━━━━━━━
{snapshot}

━━━━━━━━━━━━━━━━━━━━
🤖 *ARYA is ready. What do you want to do?*

Quick commands:
• _Add lead: Raj, raj@gmail.com, 9876543210_
• _Update Raj to Won_
• _Add note for Raj: called today_
• _Book call with Raj on 2026-04-28 at 15:00_
• _Send follow-up to Raj_
• /report — Full daily report
• /help — All commands
"""
    return message.strip()
