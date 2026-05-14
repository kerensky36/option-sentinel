"""Refresh schwab_token.json using schwab-py's manual flow.

Run from the project root:
    .venv/bin/python scripts/refresh_token.py

Steps:
1. Opens the Schwab auth URL (or prints it for you to open)
2. You log in and get redirected to the callback URL
3. The browser will show an error (nothing is listening) — that's expected
4. Copy the full URL from the address bar and paste it here
5. A new schwab_token.json is written in the current format
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

APP_KEY = os.getenv("SCHWAB_APP_KEY", "")
APP_SECRET = os.getenv("SCHWAB_APP_SECRET", "")
CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL", "https://127.0.0.1/auth/callback")
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "schwab_token.json")

if not APP_KEY or not APP_SECRET:
    print("ERROR: SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set in .env")
    sys.exit(1)

import schwab

print(f"Callback URL: {CALLBACK_URL}")
print(f"Token will be saved to: {os.path.abspath(TOKEN_PATH)}")
print()

schwab.auth.client_from_manual_flow(
    api_key=APP_KEY,
    app_secret=APP_SECRET,
    callback_url=CALLBACK_URL,
    token_path=TOKEN_PATH,
)

print()
print("Done — schwab_token.json updated. You can now use Dev Login.")
