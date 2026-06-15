# ARYA Build Log
### Agent Running Your Actions — Complete Project Documentation

**Project:** ARYA CRM Agent  
**Started:** 20 March 2026  
**Last Updated:** 15 June 2026  
**Builder:** Sagar Pathak, AIOS Aikigai, Kolkata  
**Goal:** Personal AI assistant on Telegram — manages CRM, emails, calendar, reminders  

---

## Current Status: ✅ LIVE ON RENDER

**URL:** https://arya-crm.onrender.com  
**Platform:** Render Free Tier (Web Service)  
**Uptime Monitor:** UptimeRobot (pings every 5 min)  
**Python Version:** 3.11.9 (forced via .python-version file)

---

## ARCHITECTURE

```
Telegram (you) 
    ↓ message
bot.py (handler)
    ↓ conversation history (last 10 msgs)
brain.py → Claude claude-opus-4-5 → intent JSON
    ↓
Handler (crm/email/calendar/reminder/export)
    ↓
Google Sheets / Gmail / Calendar
    ↓ response
Telegram (you)
```

---

## FILE MAP

| File | Purpose |
|---|---|
| `main.py` | Entry point — starts health server + bot |
| `requirements.txt` | All Python packages |
| `.python-version` | Forces Python 3.11.9 on Render |
| `arya/bot.py` | Telegram handler — all intents, conversation history, pending states |
| `arya/brain.py` | Claude API — intent detection, email drafting, system prompt |
| `arya/crm.py` | Google Sheets — all CRM operations |
| `arya/email_agent.py` | Gmail — send/read emails |
| `arya/campaign_email.py` | Bulk campaign emails with banner |
| `arya/calendar_agent.py` | Google Calendar — book/read meetings |
| `arya/report.py` | Daily report generator |
| `arya/memory.py` | Long-term memory → Google Sheets "Memory" tab |
| `arya/reminders.py` | Reminders → Google Sheets "Reminders" tab |
| `arya/lead_export.py` | Excel export → email |
| `arya/morning_briefing.py` | Smart 9 AM briefing (Top 5 priority leads) |
| `arya/session_starter.py` | /start and /session messages |
| `google_auth_setup.py` | One-time Google OAuth setup (run locally) |
| `upstox_config.py` | (unused in ARYA — leftover) |

---

## GOOGLE SHEET STRUCTURE

**Sheet: Sheet1** (main CRM)
| Column | Field |
|---|---|
| A | Name |
| B | Email |
| C | Phone |
| D | Status |
| E | Last Contact |
| F | Next Follow-up |
| G | No Show Count |
| H | Notes |
| I+ | Custom columns (e.g. Lead Category) |

**Sheet: Memory** (ARYA's long-term memory)
| Column | Field |
|---|---|
| A | key |
| B | value (JSON) |

Stores: last_lead, last_intent, conversation_history, last_updated

**Sheet: Reminders**
| Column | Field |
|---|---|
| A | date (YYYY-MM-DD) |
| B | time (HH:MM) |
| C | message |
| D | done (yes/no) |

---

## ENVIRONMENT VARIABLES (Render)

| Variable | What it is |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `GOOGLE_SHEET_ID` | From Google Sheet URL |
| `GOOGLE_TOKEN_B64` | Base64 of token_google.pickle |
| `GOOGLE_CREDENTIALS_B64` | Base64 of credentials.json |
| `OWNER_CHAT_ID` | Your Telegram chat ID (5441018719) |
| `OWNER_EMAIL` | aikigai12@gmail.com |

---

## INTENTS ARYA UNDERSTANDS

| Intent | Trigger examples |
|---|---|
| `crm_add` | "add lead Raj, raj@gmail.com" |
| `crm_update` | "update Raj to Won", "add note for Raj" |
| `crm_followup` | "set follow-up for Raj to 20-06-2026" |
| `crm_bulk_update` | "first 3 leads Hot rest Warm in Lead Category" |
| `crm_auto_status` | "update status by date", "auto set status by last contact" |
| `crm_add_column` | "add column Budget" |
| `crm_list` | "show all hot leads", "give me warm leads" |
| `crm_read` | "show Raj's details", "who needs follow-up today?" |
| `email_send` | "send follow-up to Raj" |
| `email_direct` | "mail to raj@gmail.com saying hello" |
| `email_bulk` | "send email to all hot leads" |
| `email_read` | "has Raj replied?" |
| `calendar_book` | "book call with Raj on 20-06-2026 at 3 PM" |
| `calendar_read` | "what's my schedule today?" |
| `reminder_set` | "remind me to call Raj on Friday at 10 AM" |
| `reminder_read` | "show my reminders" |
| `report` | /report command |
| `chat` | anything else — natural conversation |

---

## PENDING STATES (in-memory, per session)

| Dict | Purpose |
|---|---|
| `pending_emails` | Email draft awaiting yes/no/edit |
| `pending_lists` | Lead list awaiting delivery choice (1/2/3) |
| `pending_actions` | Bulk update awaiting confirmation |

---

## FEATURES BUILT ✅

| Feature | Status |
|---|---|
| Telegram bot (polling) | ✅ |
| Claude intent detection | ✅ |
| Add/update/read leads | ✅ |
| Set follow-up dates | ✅ |
| Bulk status update (any column) | ✅ |
| Auto status by last contact date | ✅ |
| Add custom columns to sheet | ✅ |
| List leads with 3 delivery options | ✅ |
| Excel export → email | ✅ |
| Send email to any address (draft+confirm) | ✅ |
| Bulk email to all/filtered leads | ✅ |
| Campaign email with banner | ✅ |
| Check email replies | ✅ |
| Book calendar meetings | ✅ |
| Read calendar schedule | ✅ |
| Set reminders (Google Sheets) | ✅ |
| 9 AM morning briefing (Top 5 leads) | ✅ |
| Daily reminders push at 9 AM | ✅ |
| Long-term memory (Google Sheets) | ✅ |
| Conversation history (RAM + Sheets) | ✅ |
| Context recovery after restart | ✅ |
| Confirmation preview before bulk writes | ✅ |
| Counter-questions on unclear input | ✅ |
| Health server (HTTP) for UptimeRobot | ✅ |
| Bot auto-restart on crash | ✅ |
| Safe imports (never crashes on missing pkg) | ✅ |

---

## HOW TO BUILD ANOTHER ARYA (for a new client)

### Step 1 — Google Cloud
1. Go to console.cloud.google.com → New Project
2. Enable: Gmail API, Google Sheets API, Google Calendar API
3. Create OAuth 2.0 credentials → download `credentials.json`
4. Add client's Gmail as test user (OAuth consent screen)

### Step 2 — Google Sheet
1. Create a new Google Sheet with these headers in row 1:
   `Name | Email | Phone | Status | Last Contact | Next Follow-up | No Show Count | Notes`
2. Copy the Sheet ID from the URL

### Step 3 — Telegram Bot
1. Open Telegram → @BotFather → /newbot
2. Copy the bot token
3. Start the bot → get your chat ID from @userinfobot

### Step 4 — Authenticate Google (run locally once)
```bash
python google_auth_setup.py
```
This creates pickle files. Then encode them:
```bash
python -c "import base64; print(base64.b64encode(open('token_gmail.pickle','rb').read()).decode())"
```
Save output as `GOOGLE_TOKEN_B64`

### Step 5 — Deploy on Render
1. Push code to GitHub
2. New Web Service → connect repo
3. Runtime: Python, Start: `python main.py`
4. Add all env vars (see table above)
5. Deploy

### Step 6 — UptimeRobot
1. uptimerobot.com → New Monitor
2. HTTP(S), URL: `https://your-app.onrender.com`
3. Interval: 5 minutes
4. Add email alert contact

---

## KEY BUGS FIXED (reference for future builds)

| Bug | Fix |
|---|---|
| Python 3.14 breaks python-telegram-bot | Add `.python-version` file with `3.11.9` |
| Google token expires | Re-run `google_auth_setup.py` → update `GOOGLE_TOKEN_B64` on Render |
| Render port binding timeout | Start HTTP health server BEFORE any imports in main.py |
| Bot dies when health server crashes | Make health server non-daemon thread |
| Bot silent (no response) | Wrap all intent handlers in try/except |
| ARYA forgets context after restart | Save conversation history to Google Sheets Memory tab |
| Bulk update writes to wrong column | Expand sheet range from A:H to A:Z |
| Bulk update silently defaults to Status | Return error with column list if column not found |
| Empty values written to sheet | Validate all update values before writing |
| Intent not recognized → silent | All unmatched intents fall to chat with Claude reply |
| yfinance NSE prices wrong | Use auto_adjust=False (TradeIQ note — not ARYA) |

---

## KNOWN LIMITATIONS

| Limitation | Workaround |
|---|---|
| Render free tier sleeps after 15 min | UptimeRobot keeps it awake |
| Conversation history resets on deploy | Now saved to Google Sheets, reloads on restart |
| Google token expires | Re-authenticate and update env var on Render |
| openpyxl needed for Excel export | In requirements.txt — installs on deploy |
| APScheduler needed for 9 AM briefing | Wrapped in try/except — ARYA works even if it fails |

---

## WHAT TO BUILD NEXT

| Feature | Priority |
|---|---|
| DevOps Agent (auto-fix ARYA on crash) | High |
| Lead finder (Google Maps API — Kolkata businesses) | High |
| WhatsApp integration | Medium |
| Payment/invoice tracking | Medium |
| LinkedIn scraper for leads | Medium |
| Voice note understanding | Low |

---

*Last updated: 15 June 2026*
