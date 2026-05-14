# Quickstart: Stateless Ephemeral Refactor

**Feature**: 004-stateless-ephemeral-refactor  
**Date**: 2026-05-03 (updated 2026-05-13 for multi-user-oauth.md extension)

---

## Prerequisites

- Python 3.11+
- A Schwab developer account with an app registered at developer.schwab.com
- The Schwab app's callback URL set to `https://127.0.0.1/auth/callback` (local) or your Cloud Run URL + `/auth/callback` (production)

---

## Local Setup

```bash
# 1. Clone and install (no DB setup required)
pip install -r requirements.txt

# 2. Copy and fill environment variables
cp .env.example .env
# Edit .env — see Environment Variables below

# 3. Run
uvicorn src.api.main:app --reload --port 8000

# 4. Open http://127.0.0.1:8000 and click "Connect Schwab Account"
#    — or use the "Dev Login" button if schwab_token.json is present
```

No `alembic upgrade head` step — there is no database.

---

## Environment Variables

### Required (app fails fast at startup if missing)

| Variable | Description | Example |
|----------|-------------|---------|
| `SCHWAB_CLIENT_ID` | Schwab developer app key | `2wtAiqo9NW3h...` |
| `SCHWAB_CLIENT_SECRET` | Schwab developer app secret | `pDdxXHbCJPCX...` |
| `SCHWAB_REDIRECT_URI` | OAuth callback URL — must match Schwab app config | `https://127.0.0.1/auth/callback` |
| `SCHWAB_AUTH_URL` | Schwab OAuth authorise endpoint | `https://api.schwabapi.com/v1/oauth/authorize` |
| `SCHWAB_TOKEN_URL` | Schwab token endpoint | `https://api.schwabapi.com/v1/oauth/token` |

> **Migration note**: If your `.env` uses the old names (`SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`,
> `SCHWAB_CALLBACK_URL`), rename them. The values are identical; only the key names changed.

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `RISK_FREE_RATE` | `0.045` | Black-Scholes risk-free rate (US 3-month Treasury) |

### Removed (no longer used)

| Variable | Reason |
|----------|--------|
| `SCHWAB_ACCOUNT_ID` | Replaced by dynamic `client.get_account_numbers()` |
| `SCHWAB_CC_ACCOUNT_ID` | Same |
| `DATABASE_URL` | No database |
| `SECRET_KEY` | No session cookie |
| `OAUTH_STATE_SECRET` | PKCE state in-memory dict (no signed cookie) |

---

## Dev Login (local only)

If `schwab_token.json` exists in the project root (from a previous `scripts/refresh_token.py` run),
the login page shows a "Dev Login" button. This bypasses the full OAuth flow by injecting the
stored token into `sessionStorage` — useful for local development without SSL/port-forwarding.

```bash
# Refresh the local token file if expired (access token valid 30 min; refresh token valid 7 days)
python scripts/refresh_token.py
```

---

## Cloud Run Deployment

> **Important**: `max-instances=1` is required. The in-memory PKCE state dict does not
> survive across instances — use a single instance for the OAuth flow to work correctly.

```bash
# Build and push container
docker build -t gcr.io/YOUR_PROJECT/option-sentinel .
docker push gcr.io/YOUR_PROJECT/option-sentinel

# Deploy
gcloud run deploy option-sentinel \
  --image gcr.io/YOUR_PROJECT/option-sentinel \
  --platform managed \
  --region us-central1 \
  --min-instances 0 \
  --max-instances 1 \
  --set-env-vars \
    SCHWAB_CLIENT_ID=YOUR_APP_KEY,\
    SCHWAB_CLIENT_SECRET=YOUR_APP_SECRET,\
    SCHWAB_REDIRECT_URI=https://YOUR_CLOUD_RUN_URL/auth/callback,\
    SCHWAB_AUTH_URL=https://api.schwabapi.com/v1/oauth/authorize,\
    SCHWAB_TOKEN_URL=https://api.schwabapi.com/v1/oauth/token,\
    RISK_FREE_RATE=0.045
```

After deploy, update the Schwab developer app's callback URL to the Cloud Run URL + `/auth/callback`.

---

## Running Tests

```bash
pytest tests/
```

No database fixtures or migrations required — all tests use in-memory data.

---

## Browser Token Lifecycle

| Event | Access Token |
|-------|-------------|
| OAuth login completes | Written to `sessionStorage.schwab_access_token` |
| API call returns 401 (token expired) | `eraseAll()` called → cleared → redirect to login |
| Tab closed | Cleared (sessionStorage is tab-scoped) |
| "Disconnect" / logout | Cleared + IndexedDB + localStorage wiped → login |
| "Erase All Data" | Cleared + IndexedDB + localStorage wiped → login |

No silent refresh. Token expiry (Schwab access tokens live ~30 min) requires a fresh login.
