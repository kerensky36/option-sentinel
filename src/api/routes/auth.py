"""Auth routes: login, OAuth connect/callback, logout."""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.api.main import templates
from src.auth.schwab_oauth import build_auth_url, exchange_code_for_token

router = APIRouter(prefix="/auth")

# CSRF state cookie config
_STATE_COOKIE = "oauth_state"
_STATE_MAX_AGE = 300  # 5 minutes — enough to complete the OAuth flow

# Secret for signing the state cookie (itsdangerous)
_OAUTH_STATE_SECRET = os.getenv("OAUTH_STATE_SECRET", "dev-state-secret-change-in-prod")


def _sign_state(state: str) -> str:
    """Sign the state value with itsdangerous to prevent tampering."""
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(_OAUTH_STATE_SECRET)
    return s.dumps(state)


def _verify_state(signed: str, max_age: int = _STATE_MAX_AGE) -> str:
    """Verify and extract the state value. Raises BadSignature/SignatureExpired on failure."""
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(_OAUTH_STATE_SECRET)
    return s.loads(signed, max_age=max_age)


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Render the login page."""
    return templates.TemplateResponse(request, "login.html", {})


@router.get("/connect")
async def connect(request: Request):
    """Initiate the Schwab OAuth flow.

    Stores the PKCE state in a short-lived signed cookie and redirects to Schwab.
    """
    authorize_url, state = build_auth_url()
    signed_state = _sign_state(state)

    response = RedirectResponse(url=authorize_url, status_code=302)
    response.set_cookie(
        key=_STATE_COOKIE,
        value=signed_state,
        max_age=_STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@router.get("/callback", response_class=HTMLResponse)
async def callback(request: Request):
    """Receive the OAuth callback from Schwab.

    Validates the state cookie, exchanges the code for a token dict, then
    renders a minimal HTML page with an inline <script> that stores the token
    in sessionStorage and redirects to the dashboard.
    """
    from itsdangerous import BadSignature, SignatureExpired

    # Validate state cookie
    signed_state = request.cookies.get(_STATE_COOKIE, "")
    if not signed_state:
        return RedirectResponse(url="/auth/login?error=missing_state", status_code=302)

    try:
        expected_state = _verify_state(signed_state)
    except SignatureExpired:
        return RedirectResponse(url="/auth/login?error=state_expired", status_code=302)
    except BadSignature:
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)

    # Exchange code for token
    received_url = str(request.url)
    try:
        token_dict = await exchange_code_for_token(received_url, expected_state)
    except ValueError as exc:
        return RedirectResponse(
            url=f"/auth/login?error=auth_failed",
            status_code=302,
        )

    token_json = json.dumps(token_dict)

    # Render inline script — token goes to sessionStorage, page redirects
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Connecting…</title></head>
<body>
<script>
  try {{
    sessionStorage.setItem('schwab_token', JSON.stringify({token_json}));
  }} catch (e) {{
    console.error('Failed to store token in sessionStorage:', e);
  }}
  window.location.replace('/');
</script>
<noscript>
  <p>JavaScript is required. <a href="/">Continue</a></p>
</noscript>
</body>
</html>"""

    response = HTMLResponse(content=html, status_code=200)
    # Clear the state cookie — it's single-use
    response.delete_cookie(key=_STATE_COOKIE)
    return response


@router.post("/logout", response_class=HTMLResponse)
async def logout(request: Request):
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
