import os
import json
import anthropic
from dotenv import load_dotenv

# Load .env from the project root using absolute path
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(dotenv_path=_env_path, override=True)

def get_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=key)

SYSTEM_PROMPT = """
You are ARYA — Agent Running Your Actions.
You are an intelligent CRM assistant that helps manage leads, send emails and book meetings.

You have access to:
- Google Sheets (CRM with all leads)
- Gmail (send and read emails)
- Google Calendar (book and manage meetings)

When the user sends a message, identify the intent and respond ONLY with a valid JSON object like this:

{
  "intent": "crm_add" | "crm_update" | "crm_read" | "email_send" | "email_bulk" | "email_read" | "calendar_book" | "calendar_read" | "report" | "unknown",
  "details": {
    "name": "lead name if mentioned",
    "email": "email address if mentioned",
    "phone": "phone number if mentioned",
    "action": "specific action to take",
    "value": "value to update if any",
    "date": "date in YYYY-MM-DD format if mentioned (calculate from today if relative like 'Friday', 'tomorrow')",
    "time": "time in HH:MM 24hr format if mentioned",
    "note": "note content if any"
  },
  "reply": "friendly confirmation message to send back to user"
}

Intent rules:
- email_bulk: user wants to send emails to multiple/all leads (e.g. "Send email to all leads", "Send follow-up to all New leads", "Email all 500 leads"). Set value to the status filter like "New", "Interested", or "all"
- crm_add: user wants to add a new lead (e.g. "Add lead Raj", "New lead: Priya 9876543210")
- crm_update: user wants to update status or add a note for existing lead
- crm_read: user wants to see lead details, follow-ups, or CRM summary
- email_send: user wants to send a follow-up email
- email_read: user wants to check if someone replied
- calendar_book: user wants to book a meeting or call
- calendar_read: user wants to see meetings/schedule
- report: user wants a daily summary report
- unknown: anything else

Today's date context: use it to calculate relative dates like "tomorrow", "Friday", "next week".

Always respond with ONLY the JSON object. No extra text before or after.
"""


def understand_intent(user_message: str) -> dict:
    """Send user message to Claude and get intent + action"""
    try:
        message = get_client().messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        response_text = message.content[0].text.strip()

        # Extract JSON from response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = response_text[start:end]
            return json.loads(json_str)
        else:
            return {
                "intent": "unknown",
                "details": {},
                "reply": "Sorry, I didn't understand that. Can you rephrase?"
            }

    except Exception as e:
        return {
            "intent": "error",
            "details": {"error": str(e)},
            "reply": f"Something went wrong: {str(e)}"
        }


def generate_email_body(name: str, history: str) -> str:
    """Generate a personalised follow-up email body using Claude"""
    try:
        message = get_client().messages.create(
            model="claude-opus-4-5",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": f"Write a short, professional follow-up email to {name}. Previous email history: {history}. Keep it under 100 words. Friendly tone. End with a clear call to action. Return only the email body, no subject line."
                }
            ]
        )
        return message.content[0].text.strip()
    except Exception as e:
        return f"Hi {name},\n\nJust following up on our previous conversation. Would love to connect and discuss further.\n\nBest regards"
