import sys
import os
import base64
import pickle
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Fix Windows encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8')


def load_google_tokens():
    """Load Google tokens from env var (for Render) or use existing pickle files."""
    token_b64 = os.getenv("GOOGLE_TOKEN_B64")
    creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")

    if token_b64:
        token_data = base64.b64decode(token_b64)
        for fname in ["token_google.pickle", "token_sheets.pickle", "token_gmail.pickle", "token_calendar.pickle"]:
            with open(fname, "wb") as f:
                f.write(token_data)
        print("Google tokens loaded from env var.")

    if creds_b64:
        with open("credentials.json", "wb") as f:
            f.write(base64.b64decode(creds_b64))
        print("credentials.json loaded from env var.")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ARYA is running")

    def log_message(self, format, *args):
        pass  # suppress request logs


def start_web_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


from arya.bot import run_bot

if __name__ == "__main__":
    print("===================================")
    print("  ARYA - Agent Running Your")
    print("         Actions")
    print("  Starting up...")
    print("===================================")

    load_google_tokens()

    # Start health check web server in background (required for Render free tier)
    t = threading.Thread(target=start_web_server, daemon=True)
    t.start()

    run_bot()
