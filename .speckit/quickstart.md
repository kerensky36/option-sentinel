# Quickstart: Option Sentinel

**Prerequisites**: Python 3.11+, a Charles Schwab brokerage account with API access

---

## 1. Register a Schwab Developer App

1. Go to https://developer.schwab.com and sign in
2. Create a new app — set the callback URL to `https://127.0.0.1` (required by Schwab)
3. Note your **App Key** (client ID) and **App Secret**

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
# Schwab API credentials
SCHWAB_APP_KEY=your_app_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_CALLBACK_URL=https://127.0.0.1
SCHWAB_ACCOUNT_ID=your_account_number

# Database (default: local SQLite)
DATABASE_URL=sqlite+aiosqlite:///./option_sentinel.db
# To use Postgres: DATABASE_URL=postgresql+asyncpg://user:pass@localhost/option_sentinel

# Email alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_RECIPIENT=your@gmail.com

# Black-Scholes risk-free rate (US 3-month Treasury; update annually)
RISK_FREE_RATE=0.045
```

---

## 4. Initialise the Database

```bash
alembic upgrade head
```

---

## 5. Authenticate with Schwab

Run the one-time OAuth2 flow:

```bash
python -m src.auth.schwab_oauth
```

This opens a browser for Schwab login. After authorising, paste the redirect URL
back into the terminal. Tokens are stored in the local database.

---

## 6. Start the App

```bash
uvicorn src.api.main:app --reload
```

Open http://localhost:8000 in your browser.

---

## 7. Re-authenticate (every 7 days)

The dashboard will display a re-authentication prompt at least 24 hours before the
Schwab refresh token expires. When prompted, run:

```bash
python -m src.auth.schwab_oauth
```

---

## Development Notes

- **Hot reload**: `--reload` flag restarts the server on code changes
- **Tests**: `pytest` (runs all tests; no external services required)
- **Migrations**: `alembic revision --autogenerate -m "description"` → `alembic upgrade head`
- **Logs**: Written to stdout; redirect to file with `uvicorn ... >> app.log 2>&1`
