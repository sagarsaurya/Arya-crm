from datetime import datetime
from arya.crm import get_todays_followups, get_all_leads
from arya.calendar_agent import get_todays_meetings


def generate_daily_report() -> str:
    """Generate full daily report for owner"""

    today = datetime.now().strftime('%d %B %Y')

    # Meetings
    meetings = get_todays_meetings()

    # Follow-ups
    followups = get_todays_followups()
    if followups:
        followup_text = f"🔔 *Follow-ups Due Today — {len(followups)} leads:*\n"
        for lead in followups:
            name = lead[0] if lead else "Unknown"
            status = lead[3] if len(lead) > 3 else "Unknown"
            followup_text += f"• {name} ({status})\n"
    else:
        followup_text = "🔔 No follow-ups due today"

    # CRM stats
    all_leads = get_all_leads()
    rows = all_leads[1:]  # skip header
    total = len(rows)

    status_counts = {}
    stale_leads = []
    today_dt = datetime.now()

    for row in rows:
        # Status count
        status = row[3].strip().title() if len(row) > 3 and row[3] else "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1

        # Stale leads (no contact in 7+ days)
        if len(row) > 4 and row[4]:
            try:
                last_contact = datetime.strptime(row[4], '%d/%m/%Y')
                days_since = (today_dt - last_contact).days
                if days_since >= 7:
                    stale_leads.append((row[0], days_since))
            except:
                pass

    # CRM summary lines
    crm_lines = [f"📊 *CRM — {total} leads total*"]
    for status, count in sorted(status_counts.items()):
        crm_lines.append(f"• {status}: {count}")
    crm_summary = "\n".join(crm_lines)

    # Stale leads
    stale_text = ""
    if stale_leads:
        stale_leads.sort(key=lambda x: x[1], reverse=True)
        stale_text = f"\n⚠️ *Stale Leads (7+ days no contact):*\n"
        for name, days in stale_leads[:5]:
            stale_text += f"• {name} — {days} days ago\n"

    report = f"""
🌅 *ARYA Daily Report*
📅 {today}

━━━━━━━━━━━━━━━━━━━━
{meetings}

━━━━━━━━━━━━━━━━━━━━
{followup_text}
━━━━━━━━━━━━━━━━━━━━
{crm_summary}
{stale_text}
━━━━━━━━━━━━━━━━━━━━
Have a productive day! 💪
"""
    return report.strip()
