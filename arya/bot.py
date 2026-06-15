import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from arya.brain import understand_intent, draft_email
from arya.crm import (
    add_lead, update_lead_status, add_note,
    get_todays_followups, get_lead_details, get_crm_summary, set_next_followup, add_column
)
from arya.memory import remember_lead, get_last_lead
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
                # Asking about a specific lead's follow-up date
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
            # Send confirmation first
            label = f"*{status_filter}*" if status_filter != "all" else "all"
            await update.message.reply_text(
                f"📤 Starting bulk email to {label} leads — *{len(leads)} emails* queued...\n\nThis may take a few minutes.",
                parse_mode='Markdown'
            )

            # Progress callback
            async def progress(msg):
                await update.message.reply_text(msg)

            import asyncio
            loop = asyncio.get_event_loop()

            def sync_callback(msg):
                loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(update.message.reply_text(msg))
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

    # ── ADD COLUMN ────────────────────────────────────────
    elif intent == "crm_add_column":
        col_name = details.get("value", "").strip()
        if not col_name:
            response = "❌ What should the column be called?"
        else:
            response = add_column(col_name)

    # ── REPORT ────────────────────────────────────────────
    elif intent == "report":
        response = generate_daily_report()

    # ── CHAT / UNKNOWN ────────────────────────────────────
    else:
        response = intent_data.get("reply", "🤔 I didn't understand that. Type /help to see what I can do!")

    if not response or not response.strip():
        response = intent_data.get("reply") or "🤔 I didn't understand that. Type /help to see what I can do!"

    try:
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception:
        await update.message.reply_text(response)


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

    print("🤖 ARYA is running... Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
