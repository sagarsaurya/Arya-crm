# ARYA — Full Workflow on n8n
### How ARYA Would Be Built on n8n

---

## What is n8n?
n8n is a visual automation tool where you connect blocks (called nodes) together like a flowchart. Each block does one job — receive a message, call an API, send a reply etc.

---

## ARYA Full n8n Architecture

```
[Telegram Trigger] 
       ↓
[Extract Message]
       ↓
[Claude API — Understand Intent]
       ↓
       ├── CRM Command → [Google Sheets Node]
       ├── Email Command → [Gmail Node]
       ├── Calendar Command → [Google Calendar Node]
       └── Unknown → [Reply: "I didn't understand"]
       ↓
[Claude API — Generate Reply]
       ↓
[Telegram — Send Reply to User]
```

---

## Workflow 1: Main ARYA Brain

### Nodes Used:
1. **Telegram Trigger** — listens for any message you send
2. **Set Node** — extracts your message text
3. **HTTP Request Node** — sends message to Claude API
4. **Switch Node** — routes to correct workflow based on intent
5. **Telegram Node** — sends reply back to you

### How it works:
```
You send: "Update Raj to Won"
       ↓
Telegram Trigger receives message
       ↓
Claude API identifies intent: "CRM Update"
       ↓
Switch Node routes to CRM Workflow
       ↓
Google Sheets updated
       ↓
Telegram sends: "Done! Raj updated to Won ✅"
```

---

## Workflow 2: CRM Agent (Google Sheets)

### Nodes Used:
1. **Google Sheets Node** — read/write lead data
2. **IF Node** — check if lead exists
3. **Claude API** — decide what to update
4. **Google Sheets Node** — write updated data
5. **Telegram Node** — confirm action

### Commands it handles:
| Command | Action |
|---|---|
| "Update [name] to Won" | Find row → change status column |
| "Add note for [name]" | Find row → add note in notes column |
| "Show me [name]'s details" | Find row → read all columns → reply |
| "Who needs follow-up today?" | Scan all rows → filter by follow-up date |

---

## Workflow 3: Email Agent (Gmail)

### Nodes Used:
1. **Gmail Node** — read email history
2. **Claude API** — write personalised email
3. **Gmail Node** — send email
4. **Google Sheets Node** — update "last contacted" date
5. **Telegram Node** — confirm email sent

### Commands it handles:
| Command | Action |
|---|---|
| "Send follow-up to [name]" | Read Gmail history → write email → send |
| "Has [name] replied?" | Search Gmail for emails from that contact |
| "Draft email to [name]" | Write draft → save in Gmail drafts |

---

## Workflow 4: Calendar Agent (Google Calendar)

### Nodes Used:
1. **Google Calendar Node** — check availability
2. **Claude API** — understand date/time from message
3. **Google Calendar Node** — create event
4. **Google Sheets Node** — update next follow-up date
5. **Telegram Node** — confirm booking

### Commands it handles:
| Command | Action |
|---|---|
| "Book call with [name] Friday 3PM" | Create calendar event → update Sheets |
| "What's my schedule today?" | Read today's events → list them |
| "Move [name]'s call to Monday" | Find event → reschedule it |
| "Cancel call with [name]" | Find event → delete it |

---

## Workflow 5: Daily Report (Scheduled)

### Nodes Used:
1. **Schedule Trigger** — runs every day at 9AM
2. **Google Sheets Node** — get today's follow-ups
3. **Google Calendar Node** — get today's meetings
4. **Claude API** — format report nicely
5. **Telegram Node** — send report to you

### Report Format:
```
Good morning! Here's your ARYA daily report 🌅

📅 Today's Meetings: 3
  → Raj Kumar — 11AM
  → Priya Singh — 2PM
  → Amit Shah — 4PM

📋 Follow-ups Due Today: 5
  → Rohit Sharma (called 3 days ago)
  → Neha Gupta (no-show last week)
  → ...

⚠️ Stale Leads (no contact in 7+ days): 3
```

---

## n8n Setup Requirements

| Item | Details |
|---|---|
| n8n version | Latest (self-hosted) |
| Hosting | Railway (₹500/month) or Local |
| Credentials needed | Telegram API, Claude API, Google OAuth |
| Workflows to build | 5 (Brain + CRM + Email + Calendar + Report) |
| Estimated build time | 6-8 hours |

---

## Why We Chose Python Over n8n for ARYA

Even though n8n gives a visual workflow — we chose Python because:
1. More reliable — n8n workflows break randomly
2. Faster responses — Python responds in under 1 second
3. More flexible — no limits on what ARYA can do
4. Easier to maintain and improve over time
5. Claude Code can write, fix and upgrade Python code directly

n8n is great for simple automations — but for an intelligent agent like ARYA that needs to think and make decisions, Python + Claude API is the better foundation.
