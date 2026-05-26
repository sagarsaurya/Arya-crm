import os
import base64
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

BANNER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'banner.png')


def get_gmail_service():
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


def build_campaign_html(name: str) -> str:
    """Build the exact email HTML matching the AIOS campaign"""
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #222; font-size: 15px; line-height: 1.6; }}
  .container {{ max-width: 600px; margin: auto; padding: 20px; }}
  .banner {{ width: 100%; max-width: 500px; display: block; margin: 20px 0; }}
  .register-btn {{
    display: inline-block;
    background-color: #f5a623;
    color: white;
    padding: 12px 28px;
    text-decoration: none;
    border-radius: 5px;
    font-weight: bold;
    font-size: 16px;
    margin: 10px 0;
  }}
  .footer {{ margin-top: 30px; font-size: 13px; color: #555; }}
  ul {{ padding-left: 20px; }}
  li {{ margin-bottom: 6px; }}
</style>
</head>
<body>
<div class="container">

  <p>Dear {name},</p>

  <p>Let me ask you something: <strong>How many hours did you lose last week to tasks AI could have handled in minutes?</strong></p>

  <p>If you don't have a clear answer, that's exactly why this is for you.</p>

  <p>🚀 <strong>INTRODUCING: AI FOUNDATION WORKSHOP</strong></p>

  <img src="cid:banner_image" class="banner" alt="AI Foundation Workshop Banner"/>

  <p>This is a focused, 2-day hands-on program designed specifically for business owners who want to start using AI, the right way, from Day 1.</p>

  <p><strong>Here's what you'll walk away with:</strong></p>
  <ul>
    <li>✅ The 3 things that make AI actually work for your business</li>
    <li>✅ How to set up and use Claude, the most powerful AI tool for business operations</li>
    <li>✅ Your very own first AI Employee, built by YOU, during the session</li>
    <li>✅ A personalized 30-Day AI Action Plan to implement immediately</li>
  </ul>

  <p>No jargon. No fluff. Just practical AI you can use the very next day.</p>

  <p>
    📅 <strong>Date:</strong> 12th &amp; 13th May<br>
    🕐 <strong>Time:</strong> 9:30 AM – 12:30 PM<br>
    📍 <strong>Venue:</strong> My Cube, Park Street, Kolkata<br>
    🔴 <strong>Seats are LIMITED, this fills fast.</strong>
  </p>

  <p>👉 <strong>Ready to claim your spot?</strong></p>

  <a href="https://forms.gle/eTJo2t6mf4AkFtVH7" class="register-btn">Register Now</a>

  <p style="font-size:14px;">Or click here: <a href="https://forms.gle/eTJo2t6mf4AkFtVH7">https://forms.gle/eTJo2t6mf4AkFtVH7</a></p>

  <p>Or just hit Reply to this email.<br>
  Either way, you are welcome to join the room.</p>

  <div class="footer">
    Warm regards,<br>
    <strong>Rama Barik</strong><br>
    Gen AI Consultant<br>
    📞 +91 96747 57903<br>
    ✉️ ajay@aikigai.in &nbsp;|&nbsp; 🌐 aikigai.ai
  </div>

</div>
</body>
</html>
"""


def send_campaign_email(name: str, email: str) -> bool:
    """Send campaign email with banner to one lead"""
    try:
        service = get_gmail_service()

        msg = MIMEMultipart('related')
        msg['To'] = email
        msg['Subject'] = "Learn AI for Your Business in 2 Days! Kolkata, May 12th & 13th"

        # HTML body
        html_content = build_campaign_html(name)
        msg_alt = MIMEMultipart('alternative')
        msg.attach(msg_alt)
        msg_alt.attach(MIMEText(html_content, 'html'))

        # Attach banner image inline
        if os.path.exists(BANNER_PATH):
            with open(BANNER_PATH, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', '<banner_image>')
                img.add_header('Content-Disposition', 'inline', filename='banner.png')
                msg.attach(img)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return True

    except Exception as e:
        print(f"Failed to send to {email}: {str(e)}")
        return False


def send_campaign_to_all(leads: list) -> str:
    """Send campaign email to all leads — fast, no Claude API calls"""
    total = len(leads)
    if total == 0:
        return "❌ No leads with email addresses found."

    # Pre-load Gmail service once (not per email)
    try:
        service = get_gmail_service()
    except Exception as e:
        return f"❌ Gmail connection failed: {str(e)}"

    # Pre-load banner once
    banner_data = None
    if os.path.exists(BANNER_PATH):
        with open(BANNER_PATH, 'rb') as f:
            banner_data = f.read()

    sent = 0
    failed = 0

    for lead in leads:
        name = lead[0] if len(lead) > 0 else "there"
        email = lead[1] if len(lead) > 1 else ""

        if not email or "@" not in email:
            failed += 1
            continue

        try:
            msg = MIMEMultipart('related')
            msg['To'] = email
            msg['Subject'] = "Learn AI for Your Business in 2 Days! Kolkata, May 12th & 13th"

            msg_alt = MIMEMultipart('alternative')
            msg.attach(msg_alt)
            msg_alt.attach(MIMEText(build_campaign_html(name), 'html'))

            if banner_data:
                img = MIMEImage(banner_data)
                img.add_header('Content-ID', '<banner_image>')
                img.add_header('Content-Disposition', 'inline', filename='banner.png')
                msg.attach(img)

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId='me', body={'raw': raw}).execute()
            sent += 1

        except Exception as e:
            failed += 1

    result = f"✅ *Campaign Email Done!*\n\n"
    result += f"📤 Sent: {sent}/{total}\n"
    if failed > 0:
        result += f"❌ Failed: {failed}"
    return result
