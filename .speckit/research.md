# Research: Option Sentinel

**Date**: 2026-04-29 | **Branch**: `001-option-sentinel-monitor`

## Decision 1: Schwab API Python Client

**Decision**: Use `schwab-py` for OAuth2 and positions; use raw `httpx` calls for
Greeks via the Schwab `/marketdata/v1/chains` endpoint.

**Rationale**: There is no official Schwab Python SDK. `schwab-py` (alexgolec/schwab-py,
v1.5.0, June 2025) is the most-maintained community wrapper. It handles the OAuth2
3-legged flow, transparent access token refresh (30-min TTL), and has a clean
positions API. However, it does not expose Greeks — they must be extracted from the
raw `/chains` JSON response. Using `httpx` through schwab-py's underlying session
avoids re-implementing OAuth header injection.

**Key facts**:
- Schwab `/marketdata/v1/chains` response includes: delta, gamma, theta, vega, IV
- Rate limit: 120 calls/min — 5-minute refresh cycle is well within limits (<1% usage)
- Access token: 30-min TTL (auto-refreshed by schwab-py)
- Refresh token: 7-day TTL (triggers re-auth prompt per FR-005)

**Alternatives considered**:
- `schwab-trader` (Alpha status, not production-ready) — rejected: too immature
- Custom HTTP client from scratch — rejected: schwab-py's OAuth handling is reliable and tested

---

## Decision 2: Frontend Stack

**Decision**: HTMX + Tailwind CSS (CDN) with FastAPI + Jinja2 server-rendered templates.
SSE (Server-Sent Events) for 5-minute live updates.

**Rationale**: All business logic (Greeks computation, scoring, alert state) stays in
Python. Server renders color-coded HTML directly. HTMX swaps updated table rows in-place
without a page reload. Tailwind provides responsive layout with zero build pipeline —
loaded from CDN. No npm, no node_modules, no Vite. `uvicorn src.api.main:app --reload`
is the entire development workflow.

**Alternatives considered**:
- React/Vue SPA — rejected: introduces build tooling, JS state management, and
  requires serialising Python business logic into JSON for client-side re-computation.
  Adds 150KB+ bundle with no benefit for a single-user dashboard.
- Alpine.js + Tailwind — rejected: cleaner than React but polling-only (no native SSE);
  Greek and scoring updates would require manual DOM manipulation in JavaScript.

---

## Decision 3: Black-Scholes Greeks Fallback

**Decision**: Custom ~100-line implementation using `scipy.stats.norm` and
`scipy.optimize.brentq`. No third-party Black-Scholes library.

**Rationale**: `scipy` and `numpy` are already in the stack. The closed-form Black-Scholes
formulas for delta, gamma, theta, and vega are 2–3 lines each. Implied volatility
uses Brent's method (`brentq`) — acceptable performance for a fallback that only runs
when the Schwab API is missing a Greek. This avoids a dependency on `py_vollib`
(dormant since Feb 2024, open pip issues as of March 2025) or `mibian` (unclear
maintenance status).

**Risk**: IV calculation can fail to converge for deep ITM/OTM options. Mitigation:
catch `ValueError` from `brentq` and return `source = 'unavailable'` for that Greek.

**Alternatives considered**:
- `py_vollib` — best accuracy (LetsBeRational) but maintenance risk; rejected
- `mibian` — simpler API but slower IV; maintenance unclear; rejected
- `QuantLib` — industry-standard but C++ wrapper overhead; overkill for a fallback; rejected

---

## Decision 4: Background Scheduler

**Decision**: `APScheduler` (AsyncIOScheduler) for the 5-minute poll job and
once-daily expiry warning check.

**Rationale**: Lightest-weight option that integrates cleanly with FastAPI's asyncio
event loop. Two jobs: (1) positions + Greeks poll every 5 minutes during market hours,
(2) expiry warning check at 09:30 ET each trading day. No Redis, no worker process,
no Celery — constitution Principle V (Simplicity Boundary) requires justification for
any added abstraction, and APScheduler is the simplest fit.

**Alternatives considered**:
- Celery + Redis — rejected: distributed task queue for a single-user local app is
  over-engineered per Principle V
- `asyncio.sleep` loop — rejected: fragile (exception kills the loop), no cron-style
  scheduling for the daily expiry check

---

## Decision 5: Database ORM + Migrations

**Decision**: SQLAlchemy 2.x (async engine) + Alembic for schema migrations.

**Rationale**: SQLAlchemy is the standard Python ORM. Alembic migrations ensure the
constitution requirement that switching to Postgres requires only a config change and
schema migration with no logic changes. Using async SQLAlchemy aligns with FastAPI's
async model.

**Risk-free rate for Black-Scholes**: US 3-month Treasury rate, configurable via
`RISK_FREE_RATE` environment variable in `.env`. Default: 0.045 (4.5%).
