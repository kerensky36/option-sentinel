"""Auth router: PKCE OAuth flow, login page, dev utilities."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import secrets
import time
import urllib.parse

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.api.main import limiter, log_security_event, templates

router = APIRouter(prefix="/auth")

_pkce_store: dict[str, dict] = {}
_PKCE_TTL = 600  # 10 minutes

_TOKEN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "schwab_token.json")
)


def _evict_expired() -> None:
    now = time.time()
    for k in [k for k, v in _pkce_store.items() if now - v["created_at"] > _PKCE_TTL]:
        del _pkce_store[k]


def _env(name: str) -> str:
    return os.environ.get(name, "")


def _handoff_page(title: str, handoff: str, noscript: str, token: str | None = None) -> HTMLResponse:
    """A page that runs /static/js/auth_handoff.js and moves on (specs/023: no inline scripts).

    Firebase sends its own nonce-free CSP on the /auth/** pages it proxies, so these
    pages cannot use an inline script even with Cloud Run's nonce.
    """
    token_attr = f' data-token="{html.escape(token)}"' if token is not None else ""
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{title}</title></head>
<body data-handoff="{handoff}"{token_attr}>
<noscript><p>{noscript}</p></noscript>
<script src="/static/js/auth_handoff.js"></script>
</body>
</html>""", status_code=200)


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "dev_login_available": os.path.exists(_TOKEN_FILE),
            "csp_nonce": getattr(request.state, "csp_nonce", ""),
        },
    )


@router.get("/start")
@limiter.limit("10/minute")
async def auth_start(request: Request):
    """Initiate Schwab OAuth flow with PKCE. Redirects browser to Schwab."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    state = secrets.token_urlsafe(32)

    _evict_expired()
    _pkce_store[state] = {"code_verifier": code_verifier, "created_at": time.time()}

    params = urllib.parse.urlencode({
        "client_id": _env("SCHWAB_CLIENT_ID"),
        "redirect_uri": _env("SCHWAB_REDIRECT_URI"),
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return RedirectResponse(url=f"{_env('SCHWAB_AUTH_URL')}?{params}", status_code=302)


@router.get("/callback", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def auth_callback(request: Request):
    """Receive Schwab OAuth callback, exchange code for access token."""
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")

    if not code or not state:
        return RedirectResponse(url="/auth/login?error=missing_params", status_code=302)

    entry = _pkce_store.pop(state, None)
    if not entry:
        log_security_event("oauth_state_mismatch", request)
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)

    if time.time() - entry["created_at"] > _PKCE_TTL:
        log_security_event("oauth_state_expired", request)
        return RedirectResponse(url="/auth/login?error=state_expired", status_code=302)

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            _env("SCHWAB_TOKEN_URL"),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _env("SCHWAB_REDIRECT_URI"),
                "code_verifier": entry["code_verifier"],
            },
            auth=(_env("SCHWAB_CLIENT_ID"), _env("SCHWAB_CLIENT_SECRET")),
        )

    if not resp.is_success:
        log_security_event("schwab_token_exchange_failed", request)
        return RedirectResponse(url="/auth/login?error=token_exchange_failed", status_code=302)

    data = resp.json()
    return _handoff_page("Connecting…", "live", 'JavaScript is required. <a href="/">Continue</a>',
                         token=data.get("access_token", ""))


@router.get("/demo-login", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def demo_login(request: Request):
    """Enter demo mode: sets demo_mode flag in sessionStorage, no Schwab OAuth required."""
    return _handoff_page("Demo Mode…", "demo", 'JavaScript is required. <a href="/">Continue</a>')


@router.get("/dev-login", response_class=HTMLResponse)
async def dev_login(request: Request):
    """DEV ONLY: inject access token from schwab_token.json into sessionStorage."""
    if not os.path.exists(_TOKEN_FILE):
        return HTMLResponse(content="<p>schwab_token.json not found.</p>", status_code=404)

    with open(_TOKEN_FILE) as f:
        data = json.load(f)

    inner = data.get("token", data)
    return _handoff_page("Dev Login…", "live", 'JavaScript is required. <a href="/">Continue</a>',
                         token=inner.get("access_token", ""))


@router.post("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """Render a page that clears all browser storage and redirects to login."""
    return _handoff_page("Signing out…", "logout", 'Signed out. <a href="/auth/login">Return to login</a>')
