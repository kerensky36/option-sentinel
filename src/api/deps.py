"""FastAPI dependency injectors for the stateless architecture."""
from __future__ import annotations

import base64
import json
import os

import schwab
from fastapi import HTTPException, Request

APP_KEY = os.getenv("SCHWAB_APP_KEY", "")
APP_SECRET = os.getenv("SCHWAB_APP_SECRET", "")
CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL", "https://127.0.0.1")


def _parse_token_from_header(authorization: str) -> dict:
    """Extract and decode the Schwab token dict from an Authorization: Bearer header.

    Accepts either:
    - Base64-encoded JSON token dict: Bearer <base64(json_string)>
    - Raw JSON string: Bearer <json_string>
    """
    bearer = authorization.removeprefix("Bearer ").strip()
    if not bearer:
        raise ValueError("Empty bearer token")

    # Try base64-decode first, then fall back to raw JSON
    try:
        decoded = base64.b64decode(bearer + "==").decode("utf-8")
        return json.loads(decoded)
    except Exception:
        pass

    try:
        return json.loads(bearer)
    except Exception:
        raise ValueError("Bearer token is not valid base64-JSON or raw JSON")


async def get_schwab_client(request: Request) -> schwab.client.AsyncClient:
    """Dependency: reads the Schwab token from the Authorization header and returns
    a configured async schwab client.

    Raises HTTPException(401) if the header is absent or malformed.
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    try:
        token_dict = _parse_token_from_header(authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"Malformed Authorization token: {exc}") from exc

    # Build the client using in-memory token functions (no file I/O)
    token_store: dict = {"token": token_dict}

    def token_read() -> dict:
        return token_store["token"]

    def token_write(new_token: dict) -> None:
        token_store["token"] = new_token

    try:
        client = schwab.auth.client_from_access_functions(
            api_key=APP_KEY,
            app_secret=APP_SECRET,
            token_read_func=token_read,
            token_write_func=token_write,
            asyncio=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Failed to build Schwab client: {exc}") from exc

    return client


async def require_auth(request: Request) -> None:
    """Dependency: raises HTTP 401 if no Authorization: Bearer header is present.

    For use on routes that require authentication but do not directly call the Schwab API
    (e.g. HTML shell renders). Separate from get_schwab_client to allow lightweight checks.
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated"},
        )
