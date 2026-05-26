import sys
import os

# Fix Windows encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8')

from arya.bot import run_bot

if __name__ == "__main__":
    print("===================================")
    print("  ARYA - Agent Running Your")
    print("         Actions")
    print("  Starting up...")
    print("===================================")
    run_bot()
