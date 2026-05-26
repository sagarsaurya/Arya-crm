import os
import pickle
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

SCOPES = ['https://www.googleapis.com/auth/calendar']
TIMEZONE = 'Asia/Kolkata'


def get_calendar_service():
    """Authenticate and return Google Calendar service"""
    creds = None
    if os.path.exists('token_calendar.pickle'):
        with open('token_calendar.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token_calendar.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


def get_todays_meetings() -> str:
    """Get all meetings for today"""
    try:
        service = get_calendar_service()
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return "📅 No meetings today"

        meeting_list = ["📅 *Today's Meetings:*"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = dt.strftime('%I:%M %p')
            except:
                time_str = start
            meeting_list.append(f"• {time_str} — {event.get('summary', 'Untitled')}")

        return "\n".join(meeting_list)
    except Exception as e:
        return f"❌ Error fetching meetings: {str(e)}"


def book_meeting(name: str, date_str: str, time_str: str) -> str:
    """Book a 1-hour meeting with a lead"""
    try:
        if not date_str or not time_str:
            return f"❌ Please provide date and time. Example: 'Book call with {name} on 2026-04-28 at 15:00'"

        service = get_calendar_service()

        # Parse datetime
        meeting_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_datetime = meeting_datetime + timedelta(hours=1)

        event = {
            'summary': f"Call with {name}",
            'description': f"Follow-up call with {name} — booked by ARYA",
            'start': {
                'dateTime': meeting_datetime.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': TIMEZONE,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }

        created = service.events().insert(calendarId='primary', body=event).execute()
        display_time = meeting_datetime.strftime('%d %b %Y at %I:%M %p')
        return f"✅ Meeting booked!\n👤 {name}\n📅 {display_time}\n🔔 Reminder set for 30 mins before"
    except ValueError:
        return f"❌ Invalid date/time format. Use YYYY-MM-DD for date and HH:MM for time."
    except Exception as e:
        return f"❌ Error booking meeting: {str(e)}"


def get_upcoming_meetings(days: int = 7) -> str:
    """Get meetings for next N days"""
    try:
        service = get_calendar_service()
        now = datetime.utcnow().isoformat() + 'Z'
        future = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=future,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return f"📅 No meetings in next {days} days"

        meeting_list = [f"📅 *Upcoming Meetings (next {days} days):*"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                formatted = dt.strftime('%d %b, %I:%M %p')
            except:
                formatted = start
            meeting_list.append(f"• {formatted} — {event.get('summary', 'Untitled')}")

        return "\n".join(meeting_list)
    except Exception as e:
        return f"❌ Error: {str(e)}"
