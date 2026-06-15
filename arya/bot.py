import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from arya.brain import understand_intent, draft_email
from arya.crm import (
    add_lead, update_lead_status, add_note,
    get_todays_followups, get_lead_details, get_crm_summary, set_next_followup, add_column,
    bulk_update_status, get_all_leads
)
from arya.memory import remember_lead, get_last_lead
from arya.reminders import save_reminder, get_all_pending_reminders, get_todays_reminders, mark_reminder_done
from arya.lead_export import send_leads_excel_email
from arya.morning_briefing import build_morning_message
from arya.email_agent import send_followup_email, check_reply, send_bulk_emails, send_direct_email
from arya.campaign_email import send_campaign_to_all
from arya.calendar_agent import book_meeting, get_todays_meetings, get_upcoming_meetings
from arya.report import generate_daily_report
from session_starter import build_session_message

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")

# Pending email approvals store: chat_id -> {to, subject, body}
pending_emails = {}

# Pending list delivery choice: chat_id -> {leads, filter_label, page}
pending_lists = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    message = build_session_message()
    await update.message.reply_text(message, parse_mode='Markdown')


async def session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /session command"""
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    message = build_session_message()
    await update.message.reply_text(message, parse_mode='Markdown')


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    report = generate_daily_report()
    await update.message.reply_text(report, parse_mode='Markdown')


async def campaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /campaign command — sends campaign email to all leads"""
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    from arya.crm import get_leads_by_status
    leads = get_leads_by_status("all")
    if not leads:
        await update.message.reply_text("❌ No leads with email found in CRM.")
        return
    await update.message.reply_text(
        f"📤 Sending campaign email to *{len(leads)} leads* with banner...\nThis will take a few minutes.",
        parse_mode='Markdown'
    )
    response = send_campaign_to_all(leads)
    await update.message.reply_text(response, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🤖 *ARYA — What I can do:*

*CRM Commands:*
• _Add lead: Raj, raj@gmail.com, 9876543210_
• _Update Raj to Won_
• _Add note for Raj: called today, very interested_
• _Show me Raj's details_
• _Who needs follow-up today?_

*Email Commands:*
• _Send follow-up to Raj_
• _Has Raj replied?_

*Calendar Commands:*
• _Book call with Raj on 2026-04-28 at 15:00_
• _What's my schedule today?_
• _Show upcoming meetings_

*Reports:*
• /report — Full daily summary
• /session — Today's briefing

Just type naturally — I'll understand! 💪
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all incoming text messages"""

    user_message = update.message.text
    chat_id = str(update.message.chat_id)

    # Security — only owner can use ARYA
    if chat_id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ Unauthorized access.")
        return

    # ── EMAIL APPROVAL CHECK ──────────────────────────────
    if chat_id in pending_emails:
        msg_lower = user_message.lower().strip()
        pending = pending_emails[chat_id]

        if msg_lower in ["yes", "send", "ok", "approve", "confirmed", "confirm", "haan", "ha"]:
            del pending_emails[chat_id]
            result = send_direct_email(pending["to"], pending["subject"], pending["body"])
            try:
                await update.message.reply_text(result, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(result)
            return

        elif msg_lower in ["no", "cancel", "nahi", "nope", "don't send", "dont send"]:
            del pending_emails[chat_id]
            await update.message.reply_text("❌ Email cancelled. What else can I help you with?")
            return

        elif msg_lower.startswith("edit:") or msg_lower.startswith("change:"):
            edit_instruction = user_message[5:].strip()
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            drafted = draft_email(pending["to"], edit_instruction)
            pending_emails[chat_id] = {"to": pending["to"], "subject": drafted["subject"], "body": drafted["body"]}
            preview = f"✏️ *Revised draft:*\n\n📧 *To:* {pending['to']}\n📌 *Subject:* {drafted['subject']}\n\n{drafted['body']}\n\n✅ Reply *yes* to send or *edit: [changes]* to revise again."
            try:
                await update.message.reply_text(preview, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(preview)
            return

    # ── LEAD LIST DELIVERY CHOICE ─────────────────────────
    if chat_id in pending_lists:
        msg_lower = user_message.lower().strip()
        plist = pending_lists[chat_id]
        leads = plist["leads"]
        label = plist["filter_label"]
        owner_email = os.getenv("OWNER_EMAIL", "aikigai12@gmail.com")

        if msg_lower in ["1", "email", "excel", "send excel", "send to email"]:
            del pending_lists[chat_id]
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            result = send_leads_excel_email(leads, owner_email, label)
            try:
                await update.message.reply_text(result, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(result)
            return

        elif msg_lower in ["2", "show", "show here", "show top 20", "telegram"]:
            pending_lists[chat_id]["page"] = 0
            page = 0
            chunk = leads[page*20:(page+1)*20]
            lines = [f"📋 *{label} leads — showing 1–{len(chunk)} of {len(leads)}:*\n"]
            for i, lead in enumerate(chunk, 1):
                name = lead[0] if lead else "?"
                status = lead[3] if len(lead) > 3 else ""
                lines.append(f"{page*20+i}. {name} — {status}")
            if len(leads) > 20:
                lines.append(f"\n_Reply *next* to see more_")
            else:
                del pending_lists[chat_id]
            try:
                await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
            except Exception:
                await update.message.reply_text("\n".join(lines))
            return

        elif msg_lower in ["next", "more", "show more", "next 20"]:
            plist["page"] = plist.get("page", 0) + 1
            page = plist["page"]
            chunk = leads[page*20:(page+1)*20]
            if not chunk:
                del pending_lists[chat_id]
                await update.message.reply_text("✅ That's all the leads.")
                return
            lines = [f"📋 *{label} leads — showing {page*20+1}–{page*20+len(chunk)} of {len(leads)}:*\n"]
            for i, lead in enumerate(chunk, 1):
                name = lead[0] if lead else "?"
                status = lead[3] if len(lead) > 3 else ""
                lines.append(f"{page*20+i}. {name} — {status}")
            if (page+1)*20 < len(leads):
                lines.append(f"\n_Reply *next* to see more_")
            else:
                del pending_lists[chat_id]
            try:
                await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
            except Exception:
                await update.message.reply_text("\n".join(lines))
            return

        elif msg_lower.startswith("3") or "filter" in msg_lower:
            del pending_lists[chat_id]
            await update.message.reply_text("🔍 Tell me the filter — e.g. *'hot leads not contacted in 7 days'* or *'warm leads with follow-up overdue'*", parse_mode='Markdown')
            return

        elif msg_lower in ["cancel", "no", "nahi"]:
            del pending_lists[chat_id]
            await update.message.reply_text("❌ Cancelled.")
            return

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Understand intent via Claude
    intent_data = understand_intent(user_message)
    intent = intent_data.get("intent", "unknown")
    details = intent_data.get("details", {})

    # If no name provided, fall back to last known lead from long-term memory
    if not details.get("name") and intent in ("crm_update", "crm_followup", "crm_read", "email_send", "email_read"):
        last = get_last_lead()
        if last:
            details["name"] = last

    response = ""

    try:
        # ── ADD LEAD ──────────────────────────────────────────
        if intent == "crm_add":
            name = details.get("name", "").strip()
            email = details.get("email", "").strip()
            phone = details.get("phone", "").strip()
            if not name:
                response = "❌ Please provide at least a name.\nExample: _Add lead: Raj Sharma, raj@gmail.com, 9876543210_"
            else:
                response = add_lead(name, email, phone)
                remember_lead(name, intent)

        # ── UPDATE LEAD ───────────────────────────────────────
        elif intent == "crm_update":
            name = details.get("name", "").strip()
            value = details.get("value", "").strip()
            action = details.get("action", "").lower()
            note = details.get("note", "").strip()
            if not name:
                response = "❌ Which lead? Please mention the name."
            elif "note" in action or note:
                response = add_note(name, note or value)
                remember_lead(name, intent)
            else:
                response = update_lead_status(name, value)
                remember_lead(name, intent)

        # ── SET FOLLOW-UP DATE ────────────────────────────────
        elif intent == "crm_followup":
            name = details.get("name", "").strip()
            date = details.get("date", "").strip()
            if not name:
                response = "❌ Which lead? Please mention the name."
            elif not date:
                response = "❌ Please provide the follow-up date."
            else:
                response = set_next_followup(name, date)
                remember_lead(name, intent)

        # ── READ CRM ──────────────────────────────────────────
        elif intent == "crm_read":
            name = details.get("name", "").strip()
            action = details.get("action", "").lower()
            if "followup" in action or "follow-up" in action or "today" in action:
                if name:
                    response = get_lead_details(name)
                else:
                    leads = get_todays_followups()
                    if leads:
                        response = f"🔔 *Follow-ups due today — {len(leads)} leads:*\n"
                        for i, lead in enumerate(leads, 1):
                            status = lead[3] if len(lead) > 3 else "Unknown"
                            response += f"{i}. {lead[0]} — {status}\n"
                    else:
                        response = "✅ No follow-ups due today!"
            elif "summary" in action or "all" in action or not name:
                response = get_crm_summary()
            else:
                response = get_lead_details(name)

        # ── BULK EMAIL ────────────────────────────────────────
        elif intent == "email_bulk":
            from arya.crm import get_leads_by_status
            status_filter = details.get("value", "all").strip() or "all"
            leads = get_leads_by_status(status_filter)
            if not leads:
                response = f"❌ No leads found with status *{status_filter}* and a valid email."
            else:
                label = f"*{status_filter}*" if status_filter != "all" else "all"
                await update.message.reply_text(
                    f"📤 Starting bulk email to {label} leads — *{len(leads)} emails* queued...\n\nThis may take a few minutes.",
                    parse_mode='Markdown'
                )
                response = send_bulk_emails(leads)

        # ── DIRECT EMAIL (draft + approval) ───────────────────
        elif intent == "email_direct":
            to_email = details.get("email", "").strip()
            instruction = details.get("body", "").strip() or details.get("note", "").strip() or user_message
            if not to_email:
                response = "❌ Please provide an email address to send to."
            else:
                drafted = draft_email(to_email, instruction)
                pending_emails[chat_id] = {"to": to_email, "subject": drafted["subject"], "body": drafted["body"]}
                response = f"📝 *Here's your email draft:*\n\n📧 *To:* {to_email}\n📌 *Subject:* {drafted['subject']}\n\n{drafted['body']}\n\n✅ Reply *yes* to send\n✏️ Reply *edit: [what to change]* to revise\n❌ Reply *no* to cancel"

        # ── SEND EMAIL ────────────────────────────────────────
        elif intent == "email_send":
            from arya.crm import find_lead
            name = details.get("name", "").strip()
            if not name:
                response = "❌ Which lead? Please mention the name."
            else:
                _, lead = find_lead(name)
                if lead:
                    email = lead[1] if len(lead) > 1 else ""
                    response = send_followup_email(name, email)
                else:
                    response = f"❌ Lead '{name}' not found in CRM. Add them first!"

        # ── CHECK REPLY ───────────────────────────────────────
        elif intent == "email_read":
            from arya.crm import find_lead
            name = details.get("name", "").strip()
            if not name:
                response = "❌ Which lead? Please mention the name."
            else:
                _, lead = find_lead(name)
                if lead:
                    email = lead[1] if len(lead) > 1 else ""
                    response = check_reply(name, email)
                else:
                    response = f"❌ Lead '{name}' not found in CRM."

        # ── BOOK MEETING ──────────────────────────────────────
        elif intent == "calendar_book":
            name = details.get("name", "").strip()
            date = details.get("date", "").strip()
            time = details.get("time", "").strip()
            if not name:
                response = "❌ Who is the meeting with?"
            elif not date or not time:
                response = f"❌ Please provide date and time.\nExample: _Book call with {name} on 2026-04-28 at 15:00_"
            else:
                response = book_meeting(name, date, time)

        # ── READ CALENDAR ─────────────────────────────────────
        elif intent == "calendar_read":
            action = details.get("action", "").lower()
            if "today" in action:
                response = get_todays_meetings()
            else:
                response = get_upcoming_meetings(7)

        # ── CAMPAIGN EMAIL ────────────────────────────────────
        elif intent == "unknown" and any(word in user_message.lower() for word in ["campaign", "event email", "send campaign", "aios", "workshop email"]):
            from arya.crm import get_leads_by_status
            leads = get_leads_by_status("all")
            if not leads:
                response = "❌ No leads with email found in CRM."
            else:
                await update.message.reply_text(
                    f"📤 Sending campaign email to *{len(leads)} leads* with banner...\nThis will take a few minutes.",
                    parse_mode='Markdown'
                )
                response = send_campaign_to_all(leads)

        # ── BULK STATUS UPDATE ────────────────────────────────
        elif intent == "crm_bulk_update":
            import json as _json
            value = details.get("value", "")
            note = details.get("note", "")
            updates = []
            if isinstance(value, str) and value.startswith("first_"):
                try:
                    count = int(value.split("_")[1])
                    hot_status = details.get("action", "Hot")
                    rest_status = note or "Warm"
                    all_leads = get_all_leads()[1:]
                    for i, row in enumerate(all_leads):
                        if row and row[0]:
                            status = hot_status if i < count else rest_status
                            updates.append((row[0], status))
                except Exception:
                    pass
            elif isinstance(value, list):
                updates = [(item["name"], item["status"]) for item in value if "name" in item]
            elif isinstance(value, str):
                try:
                    parsed = _json.loads(value)
                    if isinstance(parsed, list):
                        updates = [(item["name"], item["status"]) for item in parsed if "name" in item]
                except Exception:
                    pass
            if updates:
                response = bulk_update_status(updates)
            else:
                response = intent_data.get("reply") or "❌ I couldn't figure out which leads to update. Please list them like: 'mark Raj as Hot and Priya as Warm'"

        # ── ADD COLUMN ────────────────────────────────────────
        elif intent == "crm_add_column":
            col_name = details.get("value", "").strip()
            if not col_name:
                response = "❌ What should the column be called?"
            else:
                response = add_column(col_name)

        # ── LIST LEADS ────────────────────────────────────────
        elif intent == "crm_list":
            from arya.crm import get_leads_by_status
            filter_val = details.get("value", "all").strip() or "all"
            leads = get_leads_by_status(filter_val)
            label = filter_val.title() if filter_val != "all" else "All"
            count = len(leads)
            if count == 0:
                response = f"❌ No *{label}* leads found."
            elif count <= 20:
                lines = [f"📋 *{label} leads — {count} total:*\n"]
                for i, lead in enumerate(leads, 1):
                    name = lead[0] if lead else "?"
                    status = lead[3] if len(lead) > 3 else ""
                    lines.append(f"{i}. {name} — {status}")
                response = "\n".join(lines)
            else:
                pending_lists[chat_id] = {"leads": leads, "filter_label": label, "page": 0}
                response = (
                    f"You have *{count:,} {label}* leads.\n\n"
                    f"How do you want them?\n\n"
                    f"1️⃣ Send to your email as Excel file\n"
                    f"2️⃣ Show top 20 here in Telegram\n"
                    f"3️⃣ Filter further — e.g. 'hot leads not contacted in 7 days'"
                )

        # ── SET REMINDER ──────────────────────────────────────
        elif intent == "reminder_set":
            date = details.get("date", "").strip()
            time = details.get("time", "").strip()
            message = details.get("note", "").strip() or user_message
            if not date:
                response = "❌ Please mention the date for the reminder."
            else:
                response = save_reminder(date, time, message)

        # ── READ REMINDERS ────────────────────────────────────
        elif intent == "reminder_read":
            response = get_all_pending_reminders()

        # ── REPORT ────────────────────────────────────────────
        elif intent == "report":
            response = generate_daily_report()

        # ── CHAT / UNKNOWN ────────────────────────────────────
        else:
            response = intent_data.get("reply", "🤔 I didn't understand that. Type /help to see what I can do!")

    except Exception as e:
        response = f"⚠️ Something went wrong: {str(e)}\n\nPlease try again."

    if not response or not response.strip():
        response = intent_data.get("reply") or "🤔 I'm not sure what you meant — could you rephrase? For example, tell me the lead name and what you'd like to do."

    try:
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception:
        await update.message.reply_text(response)


async def send_morning_briefing(app):
    """Called every day at 9 AM — sends morning briefing + reminders to Sagar."""
    owner_id = os.getenv("OWNER_CHAT_ID")
    if not owner_id:
        return

    # Morning briefing
    briefing = build_morning_message()
    try:
        await app.bot.send_message(chat_id=owner_id, text=briefing, parse_mode='Markdown')
    except Exception:
        await app.bot.send_message(chat_id=owner_id, text=briefing)

    # Reminders for today
    due = get_todays_reminders()
    if due:
        lines = ["🔔 *Reminders for today:*\n"]
        for r in due:
            time_part = f" at {r['time']}" if r['time'] and r['time'] != "09:00" else ""
            lines.append(f"📝 {r['message']}{time_part}")
            mark_reminder_done(r["row"])
        reminders_msg = "\n".join(lines)
        try:
            await app.bot.send_message(chat_id=owner_id, text=reminders_msg, parse_mode='Markdown')
        except Exception:
            await app.bot.send_message(chat_id=owner_id, text=reminders_msg)


def run_bot():
    """Start ARYA bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env")

    app = Application.builder().token(token).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("session", session_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("campaign", campaign_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 9 AM daily reminder scheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(send_morning_briefing, 'cron', hour=9, minute=0, args=[app])
    scheduler.start()

    print("🤖 ARYA is running... Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
