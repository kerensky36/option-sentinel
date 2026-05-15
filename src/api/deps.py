"""FastAPI dependency injectors for the stateless multi-user architecture."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time

import schwab
from fastapi import HTTPException, Request

_security_log = logging.getLogger("security")


def _hash_ip(ip: str) -> str:
    pepper = os.getenv("LOG_PEPPER", "sentinel-pepper")
    return hmac.new(pepper.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]


def get_current_token(request: Request) -> str:
    """Extract the raw Bearer access token from the Authorization header.

    Raises HTTPException(401) if the header is absent or malformed.
    """
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        ip = request.client.host if request.client else "unknown"
        _security_log.warning(
            "SECURITY 401_invalid_token path=%s ip=%s",
            request.url.path,
            _hash_ip(ip),
        )
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        ip = request.client.host if request.client else "unknown"
        _security_log.warning(
            "SECURITY 401_invalid_token path=%s ip=%s",
            request.url.path,
            _hash_ip(ip),
        )
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    return token


def build_schwab_client(access_token: str) -> schwab.client.AsyncClient:
    """Build an async Schwab client from a raw access token string.

    Omitting expires_at prevents schwab-py from attempting auto-refresh.
    A real 401 from Schwab propagates through FastAPI as-is.
    """
    token_outer = {
        "creation_timestamp": int(time.time()),
        "token": {
            "access_token": access_token,
            "token_type": "Bearer",
        },
    }
    token_store: dict = {"data": token_outer}

    def token_read() -> dict:
        return token_store["data"]

    def token_write(new_token: dict) -> None:
        token_store["data"] = new_token

    return schwab.auth.client_from_access_functions(
        api_key=os.getenv("SCHWAB_CLIENT_ID", ""),
        app_secret=os.getenv("SCHWAB_CLIENT_SECRET", ""),
        token_read_func=token_read,
        token_write_func=token_write,
        asyncio=True,
    )


async def get_schwab_client(request: Request) -> schwab.client.AsyncClient:
    """Dependency: extracts Bearer token from request and returns a configured Schwab client.

    Raises HTTPException(401) if the header is absent, malformed, or client construction fails.
    """
    token = get_current_token(request)
    try:
        return build_schwab_client(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Failed to build Schwab client: {exc}") from exc


async def require_auth(request: Request) -> None:
    """Lightweight auth guard: raises 401 if no Bearer header present.

    For routes that need auth but do not call the Schwab API directly.
    """
    get_current_token(request)
