import os
import base64
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
from arya.brain import generate_email_body

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]


def get_gmail_service():
    """Authenticate and return Gmail service"""
    creds = None
    if os.path.exists('token_gmail.pickle'):
        with open('token_gmail.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token_gmail.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)


def get_email_history(email: str) -> str:
    """Get last 3 email subjects with a contact"""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me',
            q=f"from:{email} OR to:{email}",
            maxResults=3
        ).execute()

        messages = results.get('messages', [])
        history = []

        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
                metadataHeaders=['Subject', 'Date']
            ).execute()

            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            history.append(f"- {date}: {subject}")

        return "\n".join(history) if history else "No previous emails found"
    except Exception as e:
        return "No email history available"


def send_followup_email(name: str, email: str) -> str:
    """Send a personalised follow-up email"""
    try:
        if not email or "@" not in email:
            return f"❌ No valid email address for {name}. Please provide their email."

        # Get history for context
        history = get_email_history(email)

        # Generate personalised email body using Claude
        email_body = generate_email_body(name, history)

        # Build and send email
        service = get_gmail_service()
        message = MIMEMultipart()
        message['To'] = email
        message['Subject'] = f"Following up — {name}"
        message.attach(MIMEText(email_body, 'plain'))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()

        return f"✅ Follow-up email sent to *{name}* ({email})"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"


def send_bulk_emails(leads: list, update_callback=None) -> str:
    """Send personalised follow-up emails to a list of leads"""
    total = len(leads)
    if total == 0:
        return "❌ No leads with email addresses found."

    sent = 0
    failed = 0
    failed_names = []

    for i, lead in enumerate(leads):
        name = lead[0] if len(lead) > 0 else ""
        email = lead[1] if len(lead) > 1 else ""

        if not name or not email or "@" not in email:
            failed += 1
            continue

        try:
            history = get_email_history(email)
            email_body = generate_email_body(name, history)

            service = get_gmail_service()
            message = MIMEMultipart()
            message['To'] = email
            message['Subject'] = f"Following up — {name}"
            message.attach(MIMEText(email_body, 'plain'))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            sent += 1

            # Send progress update every 10 emails
            if update_callback and sent % 10 == 0:
                update_callback(f"📤 Progress: {sent}/{total} emails sent...")

        except Exception as e:
            failed += 1
            failed_names.append(name)

    result = f"✅ *Bulk Email Done!*\n\n"
    result += f"📤 Sent: {sent}/{total}\n"
    if failed > 0:
        result += f"❌ Failed: {failed}\n"
        if failed_names:
            result += f"Failed leads: {', '.join(failed_names[:5])}"
    return result


def send_direct_email(to_email: str, subject: str = None, body: str = None) -> str:
    """Send email to any email address directly"""
    try:
        if not to_email or "@" not in to_email:
            return "❌ Please provide a valid email address."

        if not subject:
            subject = "Message from ARYA"
        if not body:
            body = "Hi,\n\nThis is a message sent via ARYA.\n\nBest regards"

        service = get_gmail_service()
        message = MIMEMultipart()
        message['To'] = to_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()

        return f"✅ Email sent to *{to_email}*\n📧 Subject: {subject}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"


def check_reply(name: str, email: str) -> str:
    """Check if a contact has replied"""
    try:
        if not email or "@" not in email:
            return f"❌ No valid email for {name} in CRM."

        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me',
            q=f"from:{email}",
            maxResults=1
        ).execute()

        messages = results.get('messages', [])
        if messages:
            msg = service.users().messages().get(
                userId='me', id=messages[0]['id'], format='metadata',
                metadataHeaders=['Subject', 'Date']
            ).execute()
            headers = msg['payload']['headers']
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
            return f"✅ Last message from *{name}*:\n📅 {date}\n📧 {subject}"
        else:
            return f"📭 No replies found from *{name}* ({email})"
    except Exception as e:
        return f"❌ Error checking replies: {str(e)}"
