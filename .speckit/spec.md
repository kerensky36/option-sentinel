# Option Sentinel — Product Specification

**Version:** 0.1  
**Date:** 2026-04-28  
**Status:** Draft

---

## 1. Overview

Option Sentinel is a personal options position monitor for a single user. It connects to the Charles Schwab public API, polls open positions during market hours, evaluates each position against a set of pre-defined trading rules, and delivers alerts when those rules fire. A live React dashboard provides at-a-glance status of all positions, rule states, and alert history.

---

## 2. Goals

- Automatically track open options positions without manual data entry.
- Surface actionable alerts (close, expiry, exit, thesis) so no opportunity or risk is missed.
- Keep all position data local; never transmit it to external services.
- Provide a foundation that can be extended to more complex rule sets and larger storage backends.

## 3. Non-Goals

- **No automated trade execution** — alerts are informational only.
- **No multi-user support** — single-user deployment only.
- **No mobile app** — desktop/browser dashboard only.

---

## 4. Core Features

### 4.1 Schwab API Integration

| Aspect | Detail |
|---|---|
| API surface | Schwab public API only; no internal or undocumented endpoints |
| Auth flow | OAuth 2.0; user completes initial browser-based consent once |
| Access token TTL | 30 minutes — refreshed automatically by the backend |
| Refresh token TTL | 7 days — expiry must surface a clear re-authentication prompt to the user |
| Token storage | Stored locally in the SQLite database; never logged or transmitted |

**Token lifecycle rules:**

1. Before every API call, the backend checks whether the access token expires within 60 seconds; if so, it refreshes automatically using the stored refresh token.
2. If the refresh token has expired (or is within 1 hour of expiry), the backend sets a `reauth_required` flag in the database and emits a high-priority in-dashboard banner and email notification instructing the user to re-authenticate.
3. All token operations are atomic — a failed refresh must not leave a partially-updated token record.

### 4.2 Position Polling

- Polling runs every **5 minutes during market hours** (Mon–Fri 09:30–16:00 US Eastern, excluding market holidays).
- Each poll fetches all open options positions from the Schwab account.
- Positions are upserted into the local database by a composite key of `(symbol, expiration_date, strike, option_type, open_date)`.
- Polling is suspended outside market hours and on holidays (holiday calendar embedded in the app, updated annually).
- A "last polled" timestamp and poll status (success / error) are stored and shown in the dashboard.

### 4.3 Trading Rules Engine

Each rule is evaluated after every successful poll. Rules produce zero or more **alerts**.

#### Rule 1 — Credit Spread Close Trigger

**Condition:** The current mark value of a credit spread position has declined to ≤ 50% of the maximum profit (i.e., the net credit received at open).

**Calculation:**

```
max_profit        = net_credit_received          (stored at position open)
current_value     = current_mark_of_spread       (fetched each poll)
profit_captured   = max_profit - current_value
trigger           = profit_captured >= 0.50 * max_profit
```

**Alert payload:**

- Position identifier (symbol, expiry, strikes)
- Current value, max profit, % captured
- Suggested action: "Consider closing — 50% max profit reached"

**Deduplication:** Alert fires once per position. If the position re-enters the trigger range after a manual reset, it fires again.

#### Rule 2 — Expiry Escalating Warnings

**Condition:** Days to expiration (DTE) crosses a threshold.

| Threshold | Severity |
|---|---|
| DTE ≤ 14 | `INFO` |
| DTE ≤ 7 | `WARNING` |
| DTE ≤ 3 | `CRITICAL` |

- Each threshold fires exactly once per position (not every poll once crossed).
- DTE is calculated as calendar days from today's date to the expiration date.
- Alert payload includes position identifier, DTE, and severity level.

#### Rule 3 — Binary Event Exit

**Trigger:** User manually sets a `binary_event_active` flag (via dashboard toggle or API endpoint).

**Effect:** Immediately fires a `CRITICAL` alert for **every open position** instructing full exit.

- The flag persists until manually cleared by the user.
- While the flag is active, re-polling does not generate duplicate binary-event alerts for the same position (deduped by position + flag activation timestamp).
- Alert payload: "Binary event active — consider full exit" with list of all open positions.

#### Rule 4 — Thesis Alignment

**Model:** Each position carries a `thesis_alignment` field set manually by the user: `aligned | misaligned | unset`.

- `misaligned` positions render with a visual warning badge on the dashboard.
- No automated alert fires for misalignment alone — it is a visual cue only.
- The user sets/changes alignment via the dashboard or REST API.
- Thesis alignment state is stored in the local database and survives position re-polls (keyed to the position, not overwritten by poll updates).

### 4.4 Alert System

**Delivery — Phase 1 (required):**
- Email via SMTP (configurable provider; credentials stored in local `.env`).
- In-dashboard alert feed (persisted in SQLite, shown in reverse-chronological order).

**Delivery — Phase 2 (stretch):**
- SMS via Twilio (opt-in; Twilio credentials in `.env`).

**Alert record schema:**

```
id, position_id, rule_name, severity, message, fired_at, acknowledged_at, delivery_status
```

- Users can acknowledge alerts from the dashboard (sets `acknowledged_at`).
- Unacknowledged `CRITICAL` alerts are visually prominent until dismissed.

### 4.5 Dashboard

Single-page React application served by the FastAPI backend.

**Panels:**

| Panel | Content |
|---|---|
| Positions table | All open positions with columns: symbol, type, strikes, expiry, DTE, max profit, current value, % captured, thesis alignment badge, active alerts |
| Alert feed | Recent alerts with severity, message, timestamp, acknowledge button |
| System status | Last poll time, poll result, token expiry countdown, reauth banner (when needed) |
| Binary event toggle | On/Off toggle with confirmation dialog; current state shown prominently |

**Refresh:** Dashboard polls the backend `/api/status` endpoint every 30 seconds for live updates (no WebSocket required in v1).

---

## 5. Technical Architecture

### 5.1 Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI |
| Frontend | React 18+, served as static build from FastAPI |
| Database | SQLite (production), abstracted via SQLAlchemy ORM for Postgres migration |
| Task scheduler | APScheduler (in-process) for polling and token refresh |
| HTTP client | `httpx` (async) for Schwab API calls |
| Email | Python `smtplib` / `aiosmtplib` |
| SMS (stretch) | Twilio Python SDK |

### 5.2 Database Schema (key tables)

```
tokens          (id, access_token, refresh_token, access_expires_at, refresh_expires_at, updated_at)
positions       (id, symbol, expiration_date, strike_low, strike_high, option_type, open_date,
                 net_credit, current_mark, thesis_alignment, is_open, last_updated_at)
alerts          (id, position_id, rule_name, severity, message, fired_at, acknowledged_at, delivery_status)
settings        (key, value)   -- binary_event_active, last_poll_at, last_poll_status, etc.
```

### 5.3 Postgres Migration Path

- All database access goes through SQLAlchemy; no raw SQL with SQLite-specific syntax.
- Migration scripts managed with Alembic.
- Switching to Postgres requires only changing the `DATABASE_URL` env var and running `alembic upgrade head`.

### 5.4 Configuration

All secrets and environment-specific values in `.env` (never committed):

```
SCHWAB_CLIENT_ID
SCHWAB_CLIENT_SECRET
SCHWAB_REDIRECT_URI
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
ALERT_EMAIL_TO
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM, TWILIO_TO  # stretch
DATABASE_URL   # defaults to sqlite:///./option_sentinel.db
```

---

## 6. API Endpoints (Backend)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/positions` | List all open positions with current rule states |
| `PATCH` | `/api/positions/{id}/thesis` | Set thesis alignment for a position |
| `GET` | `/api/alerts` | List alerts (filter: unacknowledged, severity, date range) |
| `POST` | `/api/alerts/{id}/acknowledge` | Acknowledge an alert |
| `GET` | `/api/status` | System status: last poll, token expiry, binary event flag |
| `POST` | `/api/binary-event` | Set binary event flag `{ "active": true/false }` |
| `POST` | `/api/auth/start` | Begin Schwab OAuth flow (returns redirect URL) |
| `GET` | `/api/auth/callback` | Schwab OAuth callback; exchanges code for tokens |
| `POST` | `/api/poll` | Manually trigger an immediate position poll |

---

## 7. Data Privacy

- All position data is written only to the local SQLite file.
- No position, token, or alert data is transmitted to any external service other than:
  - Schwab API (to fetch positions and refresh tokens)
  - SMTP relay (alert email body; contains position details — user is responsible for choosing a trusted relay)
  - Twilio (stretch; SMS body contains minimal alert text)
- The application does not include analytics, telemetry, or crash-reporting that would transmit data externally.

---

## 8. Out-of-Scope / Future Considerations

- Automated trade execution (explicitly excluded)
- Multi-account or multi-user support
- Mobile or native app
- Real-time streaming (WebSocket feed from Schwab)
- Strategy-level P&L aggregation across multiple legs
- Greeks monitoring (delta, theta, vega alerts)
- Backtesting or paper-trading modes
