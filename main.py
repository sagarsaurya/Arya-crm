import sys
import os
import base64
import pickle
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Fix Windows encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8')


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ARYA is running")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress request logs


def start_web_server():
    port = int(os.getenv("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"[HEALTH] Server running on port {port}", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[HEALTH] Server crashed: {e}", flush=True)


# Start web server as NON-daemon so it keeps process alive even if bot crashes
t = threading.Thread(target=start_web_server, daemon=False)
t.start()
time.sleep(1)  # give server a moment to bind before bot starts


def load_google_tokens():
    """Load Google tokens from env var (for Render) or use existing pickle files."""
    token_b64 = os.getenv("GOOGLE_TOKEN_B64")
    creds_b64 = os.getenv("GOOGLE_CREDENTIALS_B64")

    if token_b64:
        token_data = base64.b64decode(token_b64)
        for fname in ["token_google.pickle", "token_sheets.pickle", "token_gmail.pickle", "token_calendar.pickle"]:
            with open(fname, "wb") as f:
                f.write(token_data)
        print("Google tokens loaded from env var.", flush=True)

    if creds_b64:
        with open("credentials.json", "wb") as f:
            f.write(base64.b64decode(creds_b64))
        print("credentials.json loaded from env var.", flush=True)


from arya.bot import run_bot

if __name__ == "__main__":
    print("===================================", flush=True)
    print("  ARYA - Agent Running Your", flush=True)
    print("         Actions", flush=True)
    print("  Starting up...", flush=True)
    print("===================================", flush=True)

    load_google_tokens()

    while True:
        try:
            run_bot()
        except Exception as e:
            print(f"[BOT] Crashed: {e} — restarting in 10s...", flush=True)
            time.sleep(10)
