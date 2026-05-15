# Implementation Plan: Option Sentinel

**Branch**: `001-option-sentinel-monitor` | **Date**: 2026-04-29 | **Spec**: `.speckit/spec.md`
**Input**: Feature specification from `.speckit/spec.md`

## Summary

Option Sentinel is a local web application for a single trader to monitor open
options positions sourced from the Charles Schwab API. It displays a visual,
mobile-responsive dashboard with live position data, option Greeks, thesis
groupings, and exit proximity scoring. It fires email alerts when profit targets,
expiry thresholds, or binary event flags are triggered. All data is stored locally;
nothing is transmitted externally except to the Schwab API.

The stack is: **Python 3.11 + FastAPI + HTMX + Tailwind CSS + SQLite + APScheduler**.
Greeks are sourced from Schwab's `/marketdata/v1/chains` endpoint; a custom
Black-Scholes calculator using `scipy` provides fallback values when the API
does not return them.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `schwab-py` — Schwab OAuth2 + positions (community SDK, actively maintained)
- `httpx` — direct Schwab `/chains` calls for Greeks (schwab-py doesn't expose them)
- `fastapi` + `uvicorn` — web server
- `jinja2` — server-rendered HTML templates
- `htmx` (CDN) — HTMX for DOM swaps + SSE live updates
- `tailwindcss` (CDN) — responsive utility-first styling
- `sqlalchemy` 2.x + `alembic` — ORM + migrations
- `apscheduler` — 5-minute polling scheduler
- `aiosmtplib` — async email delivery
- `scipy` + `numpy` — Black-Scholes Greeks fallback
- `pytest` + `pytest-asyncio` — testing

**Storage**: SQLite (local); switchable to Postgres via env var — no logic changes required
**Testing**: pytest + pytest-asyncio; integration tests against real SQLite DB (no mocks)
**Target Platform**: Local web service at `http://localhost:8000`
**Project Type**: Web application — Python backend + server-rendered HTMX frontend
**Performance Goals**: 5-min position + Greeks refresh; <60s binary event alert delivery; <200ms dashboard load
**Constraints**: Local-only; no cloud sync; mobile-responsive; no npm/build pipeline

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Local-First Privacy | ✅ Pass | Only Schwab API receives outbound data; SQLite on disk |
| II. Spec-Before-Code | ✅ Pass | This plan follows a ratified spec |
| III. Test-First | ✅ Pass | Tasks will enforce test-before-implement ordering |
| IV. Alert Reliability | ✅ Pass | Alert engine must be idempotent; retry logic required (FR-032) |
| V. Simplicity Boundary | ✅ Pass | Single user, no unnecessary abstractions; APScheduler not Celery |
| VI. Visual & Responsive UI | ✅ Pass | HTMX + Tailwind; SSE push; mobile-responsive layout |

**No violations. Complexity Tracking table not required.**

## Project Structure

### Documentation (this feature)

```text
.speckit/
├── plan.md          # This file
├── research.md      # Phase 0 output
├── data-model.md    # Phase 1 output
├── quickstart.md    # Phase 1 output
├── contracts/
│   └── http.md      # REST + SSE endpoint contracts
└── tasks.md         # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── main.py           # FastAPI app factory + route registration
│   ├── routes/
│   │   ├── dashboard.py  # GET / — full dashboard HTML
│   │   ├── partials.py   # GET /partials/* — HTMX fragment endpoints
│   │   ├── sse.py        # GET /sse — Server-Sent Events stream
│   │   ├── thesis.py     # Thesis CRUD endpoints
│   │   ├── positions.py  # Position assignment + exit goal endpoints
│   │   └── binary.py     # Binary event flag endpoints
│   └── deps.py           # FastAPI dependency injection (DB session, etc.)
├── auth/
│   ├── schwab_oauth.py   # schwab-py client init + token lifecycle
│   └── token_store.py    # AuthToken DB read/write + re-auth detection
├── data/
│   ├── database.py       # SQLAlchemy engine + session factory
│   ├── models.py         # ORM models (all entities)
│   └── migrations/       # Alembic migration scripts
├── notifications/
│   ├── email_client.py   # aiosmtplib wrapper + retry logic
│   └── templates/        # Plain-text email templates per alert type
├── rules/
│   ├── profit_target.py  # 50% max-profit close trigger
│   ├── expiry_warning.py # 14/7/3-day escalation
│   ├── binary_event.py   # Binary event exit alert
│   └── exit_scoring.py   # Exit proximity score computation (0–100)
└── services/
    ├── schwab_client.py          # Position + quote fetcher (schwab-py + raw httpx for Greeks)
    ├── greeks_service.py         # Schwab Greeks parser + Black-Scholes fallback
    ├── bs_calculator.py          # ~100-line scipy Black-Scholes implementation
    ├── poll_scheduler.py         # APScheduler 5-min job wiring
    └── covered_call_screener.py  # CC screener: fetch stock positions → rank by composite score

frontend/
├── templates/
│   ├── base.html         # Layout shell: top nav + left sidebar + main content block
│   ├── dashboard.html    # Thesis Monitor view (extends base) — thesis cards + positions
│   ├── screener.html     # Covered Call Screener view (extends base)
│   └── partials/
│       ├── positions_table.html  # HTMX-swappable positions grid
│       ├── position_row.html     # Single position row (HTMX OOB swap target)
│       ├── thesis_panel.html     # Thesis group sidebar (create/delete)
│       ├── thesis_cards.html     # Thesis Monitor health cards (HTMX-swappable)
│       ├── binary_banner.html    # Binary event flag banner
│       └── screener_table.html   # Covered Call Screener ranked results table
└── static/
    └── sentinel.svg      # Minimal static assets; CSS/JS from CDN

tests/
├── unit/
│   ├── test_bs_calculator.py          # Black-Scholes Greeks accuracy
│   ├── test_exit_scoring.py           # Score computation correctness
│   ├── test_profit_target.py          # Alert rule logic
│   ├── test_expiry_warning.py         # Alert tier logic
│   └── test_covered_call_screener.py  # CC composite score + suppression rules
├── integration/
│   ├── test_alert_pipeline.py    # Alert fire → log → retry pipeline
│   ├── test_polling_cycle.py     # Poll → update → score cycle
│   └── test_thesis_assignment.py # Thesis CRUD + position assignment
└── contract/
    └── test_api_contracts.py     # FastAPI endpoint contract tests (all routes)
```

**Structure Decision**: Web application layout. Backend in `src/`, server-rendered
templates in `frontend/templates/`, tests in `tests/`. No `backend/` prefix — the
project has a single Python package root at `src/`.

## New Routes (US6–US8)

| Route | Handler | Purpose |
|---|---|---|
| `GET /` | `dashboard.py` | Thesis Monitor view (existing, refocused to thesis cards) |
| `GET /screener` | `screener.py` | Covered Call Screener view |
| `POST /screener/refresh` | `screener.py` | Re-fetch option chains and re-rank on demand |

`current_page` context variable injected by every page route so `base.html` can highlight the active sidebar item.

## Complexity Tracking

*No constitution violations — table not required.*
