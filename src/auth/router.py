"""Auth router: PKCE OAuth flow, login page, dev utilities."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.api.main import templates

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


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse(
        request, "login.html", {"dev_login_available": os.path.exists(_TOKEN_FILE)}
    )


@router.get("/start")
async def auth_start():
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
async def auth_callback(request: Request):
    """Receive Schwab OAuth callback, exchange code for access token."""
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")

    if not code or not state:
        return RedirectResponse(url="/auth/login?error=missing_params", status_code=302)

    entry = _pkce_store.pop(state, None)
    if not entry:
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)

    if time.time() - entry["created_at"] > _PKCE_TTL:
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
        return RedirectResponse(url="/auth/login?error=token_exchange_failed", status_code=302)

    data = resp.json()
    access_token = json.dumps(data.get("access_token", ""))

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Connecting…</title></head>
<body>
<script>
  try {{
    sessionStorage.setItem('schwab_access_token', {access_token});
  }} catch (e) {{
    console.error('Failed to store token:', e);
  }}
  window.location.replace('/');
</script>
<noscript><p>JavaScript is required. <a href="/">Continue</a></p></noscript>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@router.get("/dev-login", response_class=HTMLResponse)
async def dev_login():
    """DEV ONLY: inject access token from schwab_token.json into sessionStorage."""
    if not os.path.exists(_TOKEN_FILE):
        return HTMLResponse(content="<p>schwab_token.json not found.</p>", status_code=404)

    with open(_TOKEN_FILE) as f:
        data = json.load(f)

    inner = data.get("token", data)
    access_token = json.dumps(inner.get("access_token", ""))

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Dev Login…</title></head>
<body>
<script>
  try {{
    sessionStorage.setItem('schwab_access_token', {access_token});
  }} catch (e) {{
    console.error('Failed to store token:', e);
  }}
  window.location.replace('/');
</script>
<noscript><p>JavaScript is required. <a href="/">Continue</a></p></noscript>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@router.post("/logout", response_class=HTMLResponse)
async def logout():
    """Render a page that clears all browser storage and redirects to login."""
    html = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Signing out…</title></head>
<body>
<script>
  (async function() {
    sessionStorage.clear();
    localStorage.clear();
    try {
      await new Promise((resolve, reject) => {
        const req = indexedDB.deleteDatabase('option-sentinel');
        req.onsuccess = resolve;
        req.onerror = reject;
        req.onblocked = resolve;
      });
    } catch (e) {
      console.warn('IndexedDB clear failed:', e);
    }
    window.location.replace('/auth/login');
  })();
</script>
<noscript><p>Signed out. <a href="/auth/login">Return to login</a></p></noscript>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)
