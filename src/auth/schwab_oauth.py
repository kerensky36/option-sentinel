"""Stateless Schwab OAuth helpers.

Token flow:
1. build_auth_url() → generate Schwab authorize URL + PKCE state.
   The caller stores the state in a short-lived signed cookie.
2. exchange_code_for_token(received_url, state) → call Schwab token endpoint,
   return the raw token dict. Caller delivers token to browser.
3. Per-request: caller passes token dict via Authorization header.
   get_schwab_client_from_token(token_dict) rebuilds the client in-memory.
"""
from __future__ import annotations

import os
import time
from urllib.parse import urlencode, urlparse, parse_qs

import httpx
import schwab
from schwab import auth as schwab_auth

APP_KEY = os.getenv("SCHWAB_APP_KEY", "")
APP_SECRET = os.getenv("SCHWAB_APP_SECRET", "")
CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL", "https://127.0.0.1")

# Schwab's token endpoint
_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


def build_auth_url() -> tuple[str, str]:
    """Generate the Schwab OAuth authorise URL and the PKCE state string.

    Returns:
        (authorize_url, state) — state must be stored in a short-lived signed
        cookie by the caller and validated in the callback.
    """
    ctx = schwab_auth.get_auth_context(APP_KEY, CALLBACK_URL)
    return ctx.authorization_url, ctx.state


async def exchange_code_for_token(received_url: str, state: str) -> dict:
    """Exchange the OAuth callback URL (containing code + state) for a token dict.

    Uses the Schwab token endpoint directly via httpx to avoid schwab-py's
    file-based token persistence side effect.

    Args:
        received_url: The full callback URL with code and state query params.
        state: The expected PKCE state string (for CSRF validation).

    Returns:
        Token dict with access_token, refresh_token, expiry fields.

    Raises:
        ValueError: If state mismatch or token exchange fails.
    """
    parsed = urlparse(received_url)
    params = parse_qs(parsed.query)

    returned_state = params.get("state", [None])[0]
    if returned_state != state:
        raise ValueError(f"OAuth state mismatch: expected {state!r}, got {returned_state!r}")

    error = params.get("error", [None])[0]
    if error:
        desc = params.get("error_description", [error])[0]
        raise ValueError(f"Schwab OAuth error: {desc}")

    code = params.get("code", [None])[0]
    if not code:
        raise ValueError("No 'code' parameter in callback URL")

    # Exchange code for token directly via httpx
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": CALLBACK_URL,
            },
            auth=(APP_KEY, APP_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise ValueError(f"Token exchange failed: HTTP {resp.status_code} — {resp.text}")

    raw = resp.json()

    # Add expires_at so authlib can detect expiry and auto-refresh.
    now = int(time.time())
    raw.setdefault("expires_at", now + raw.get("expires_in", 1800))

    # Wrap in the full format client_from_access_functions (TokenMetadata) expects.
    return {
        "creation_timestamp": now,
        "token": raw,
    }


def get_schwab_client_from_token(token_dict: dict) -> schwab.client.AsyncClient:
    """Rebuild an async Schwab client from a token dict (no file I/O).

    Used by the per-request dependency in deps.py.
    """
    token_store: dict = {"token": token_dict}

    def token_read() -> dict:
        return token_store["token"]

    def token_write(new_token: dict) -> None:
        token_store["token"] = new_token

    return schwab_auth.client_from_access_functions(
        api_key=APP_KEY,
        app_secret=APP_SECRET,
        token_read_func=token_read,
        token_write_func=token_write,
        asyncio=True,
    )
