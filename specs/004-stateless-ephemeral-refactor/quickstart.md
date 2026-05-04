# Quickstart: Stateless Ephemeral Refactor

**Feature**: 004-stateless-ephemeral-refactor
**Date**: 2026-05-03

---

## Prerequisites

- Python 3.11+
- A Schwab developer account with an app registered at developer.schwab.com
- The Schwab app's callback URL set to `http://127.0.0.1:8000/auth/callback` (local) or your Cloud Run URL + `/auth/callback` (production)

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
```

No `alembic upgrade head` step — there is no database.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SCHWAB_APP_KEY` | Yes | Schwab developer app key |
| `SCHWAB_APP_SECRET` | Yes | Schwab developer app secret |
| `SCHWAB_CALLBACK_URL` | Yes | OAuth callback URL (must match Schwab app config) |
| `SCHWAB_ACCOUNT_ID` | Yes | Schwab account number for options positions |
| `SCHWAB_SCREENER_ACCOUNT_ID` | Yes | Schwab account number for covered call screener (long stock) |
| `SECRET_KEY` | Yes | Random 32-byte hex string for session cookie signing |

Generate a `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Cloud Run Deployment

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
  --set-env-vars SCHWAB_APP_KEY=...,SCHWAB_APP_SECRET=...,SCHWAB_CALLBACK_URL=https://YOUR_CLOUD_RUN_URL/auth/callback \
  --set-secrets SECRET_KEY=option-sentinel-secret-key:latest,SCHWAB_ACCOUNT_ID=schwab-account-id:latest,SCHWAB_SCREENER_ACCOUNT_ID=schwab-screener-account-id:latest
```

After deploy, update the Schwab developer app's callback URL to the Cloud Run URL + `/auth/callback`.

---

## Running Tests

```bash
pytest tests/
```

No database fixtures or migrations required — all tests use in-memory data.
