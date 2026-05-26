"""
Run this ONCE before starting ARYA.
This authenticates Google Sheets, Gmail and Calendar all at once.
"""
import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# All scopes needed by ARYA
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
]

TOKEN_FILE = 'token_google.pickle'

def setup_auth():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    # Save same token for all services
    for fname in ['token_sheets.pickle', 'token_gmail.pickle', 'token_calendar.pickle']:
        with open(fname, 'wb') as f:
            pickle.dump(creds, f)

    print("")
    print("====================================")
    print("  Google Auth SUCCESS!")
    print("  Sheets + Gmail + Calendar ready")
    print("  Now run: python main.py")
    print("====================================")

if __name__ == "__main__":
    print("Opening browser for Google login...")
    setup_auth()
