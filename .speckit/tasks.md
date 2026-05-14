---
description: "Task list for Option Sentinel implementation"
---

# Tasks: Option Sentinel

**Input**: `.speckit/plan.md`, `.speckit/spec.md`, `.speckit/data-model.md`, `.speckit/contracts/http.md`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

**Tests**: Included — constitution Principle III (Test-First) is NON-NEGOTIABLE.
Tests MUST be written and confirmed failing before implementation.

**Organization**: Tasks grouped by user story for independent implementation and delivery.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths included in all descriptions

---

## Phase 1: Setup

**Purpose**: Project skeleton and configuration

- [X] T001 Create directory structure: `src/api/routes/`, `src/auth/`, `src/data/migrations/`, `src/notifications/templates/`, `src/rules/`, `src/services/`, `frontend/templates/partials/`, `frontend/static/`, `tests/unit/`, `tests/integration/`, `tests/contract/`
- [X] T002 Populate `requirements.txt` with pinned versions: fastapi, uvicorn[standard], jinja2, sqlalchemy[asyncio], aiosqlite, alembic, apscheduler, aiosmtplib, schwab-py, httpx, scipy, numpy, pytest, pytest-asyncio
- [X] T003 [P] Configure `pytest.ini` (asyncio_mode=auto) and `tests/conftest.py` with async SQLite test DB fixture
- [X] T004 [P] Populate `.env.example` per `.speckit/quickstart.md` with all required variables
- [ ] T005 Initialise Alembic: `alembic init src/data/migrations`, configure `src/data/migrations/env.py` to read `DATABASE_URL` from env

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work begins until this phase is complete

- [ ] T006 Create SQLAlchemy async engine + session factory in `src/data/database.py`; expose `get_db` dependency
- [ ] T007 [P] Create all ORM models in `src/data/models.py`: Position, Greeks, ExitGoal, Thesis, Spread, Alert, AuthToken (singleton), BinaryEventFlag (singleton) — per `.speckit/data-model.md`
- [ ] T008 Generate initial Alembic migration for all entities: `alembic revision --autogenerate -m "initial schema"`; verify migration applies cleanly
- [ ] T009 [P] Implement schwab-py OAuth2 client init + token lifecycle management in `src/auth/schwab_oauth.py`; expose `get_schwab_client()` coroutine
- [ ] T010 Implement AuthToken DB read/write + re-auth detection (re_auth_required = True when refresh_expiry < now + 24h) in `src/auth/token_store.py`
- [ ] T011 [P] Create FastAPI app factory in `src/api/main.py`: register all routers, configure Jinja2 templates, wire APScheduler lifespan startup/shutdown
- [ ] T012 [P] Create FastAPI dependency injection helpers in `src/api/deps.py`: `get_db`, `get_schwab_client`
- [ ] T013 [P] Create Jinja2 base layout in `frontend/templates/base.html`: HTMX CDN, Tailwind CDN, SSE extension, nav bar, binary event banner slot, main content block
- [ ] T014 [P] Implement Black-Scholes calculator in `src/services/bs_calculator.py`: `bs_greeks(S, K, T, r, sigma, option_type)` and `implied_volatility(S, K, T, r, option_price, option_type)` using `scipy.stats.norm` and `scipy.optimize.brentq`; handle IV convergence failure by returning `None`

**Checkpoint**: Foundation ready — all user story phases can now begin

---

## Phase 3: User Story 1 — Live Position Dashboard (Priority: P1) 🎯 MVP

**Goal**: Trader opens dashboard and sees all open positions with mark price, P&L, Greeks (with source indicator), and thesis group assignment. Data refreshes automatically every 5 minutes.

**Independent Test**: Connect to a Schwab account with ≥1 open options position; open `http://localhost:8000`; confirm position row shows symbol, strike, expiry, quantity, mark, P&L, DTE, and at least delta with a source badge.

### Tests for User Story 1 ⚠️ Write FIRST — confirm FAILING before T018

- [ ] T015 [P] [US1] Write unit tests for `bs_calculator` Greeks accuracy (call + put delta, gamma, vega, theta; IV round-trip) in `tests/unit/test_bs_calculator.py`
- [ ] T016 [P] [US1] Write contract tests for `GET /` (returns 200 HTML) and `GET /partials/positions` (returns 200 HTML fragment) in `tests/contract/test_api_contracts.py`
- [ ] T017 [P] [US1] Write integration test for one full poll cycle: mock Schwab response → positions + Greeks written to DB → dashboard query returns updated data in `tests/integration/test_polling_cycle.py`

### Implementation for User Story 1

- [ ] T018 [US1] Implement Schwab positions fetcher in `src/services/schwab_client.py`: use schwab-py for `GET /accounts/{id}/positions`; use raw `httpx` call for `GET /marketdata/v1/chains` to extract Greeks per option symbol
- [ ] T019 [US1] Implement Greeks parser + fallback in `src/services/greeks_service.py`: extract delta/gamma/theta/vega/IV from Schwab chain response; fall back to `bs_calculator` for any `None` field; set `_source` enum per field
- [ ] T020 [US1] Implement APScheduler async poll job in `src/services/poll_scheduler.py`: runs every 5 minutes during market hours (09:30–16:00 ET, Mon–Fri, US holidays skipped); calls `schwab_client` → updates Position + Greeks rows; emits SSE `refresh` event
- [ ] T021 [US1] Implement `GET /` dashboard route in `src/api/routes/dashboard.py`: query all open positions with Greeks + thesis assignment; render `dashboard.html`
- [ ] T022 [US1] Implement `GET /partials/positions` HTMX fragment route in `src/api/routes/partials.py`: same query as T021; render `partials/positions_table.html`
- [ ] T023 [US1] Implement `GET /sse` SSE stream in `src/api/routes/sse.py`: yield `event: refresh` after each poll; yield `event: re_auth_required` when `AuthToken.re_auth_required` is True
- [ ] T024 [P] [US1] Create `frontend/templates/dashboard.html` extending `base.html`: positions table section wired with `hx-get="/partials/positions"` and `sse-swap="refresh"`; polling status bar
- [ ] T025 [P] [US1] Create `frontend/templates/partials/positions_table.html`: responsive Tailwind table with columns: symbol, type, strike, expiry, qty, mark, P&L (colour-coded green/red), DTE, delta, gamma, theta, vega, IV — each Greek shows value + source badge (`api`=blue, `calculated`=amber, `unavailable`=grey)
- [ ] T026 [US1] Register all US1 routes in `src/api/main.py`; wire scheduler startup into FastAPI lifespan; confirm `pytest tests/contract/test_api_contracts.py` and `pytest tests/unit/test_bs_calculator.py` pass

**Checkpoint**: User Story 1 independently functional and tested — MVP deliverable

---

## Phase 4: User Story 2 — Credit Spread Profit Target Alert (Priority: P2)

**Goal**: When a credit spread reaches 50% of its maximum profit, the trader receives an email alert. Alert does not re-fire until position resets below threshold and re-crosses.

**Independent Test**: Seed a Spread with net_credit=1.00; set Position current_mark=0.50 (50% captured); run poll cycle; confirm Alert row created with `delivery_status='delivered'` and email received.

### Tests for User Story 2 ⚠️ Write FIRST — confirm FAILING before T029

- [ ] T027 [P] [US2] Write unit tests for profit target rule: fires at 50%, does not re-fire within same event, re-arms after reset in `tests/unit/test_profit_target.py`
- [ ] T028 [P] [US2] Write integration test for full alert pipeline: trigger → Alert created → email sent → retry on failure in `tests/integration/test_alert_pipeline.py`

### Implementation for User Story 2

- [ ] T029 [US2] Implement async email client with 3-attempt retry logic in `src/notifications/email_client.py`: uses `aiosmtplib`; logs each attempt to Alert row; sets `delivery_status` to `delivered` | `failed` | `max_retries`
- [ ] T030 [P] [US2] Create plain-text email template for profit target alert in `src/notifications/templates/profit_target.txt`: includes position symbol, current P&L %, suggested action
- [ ] T031 [US2] Implement profit target rule engine in `src/rules/profit_target.py`: calculate `(net_credit - current_mark) / net_credit * 100`; fire if ≥50% and no un-reset Alert exists for this position+type; create Alert row; call email client
- [ ] T032 [US2] Wire profit target rule into poll job in `src/services/poll_scheduler.py`; confirm `pytest tests/unit/test_profit_target.py` and `pytest tests/integration/test_alert_pipeline.py` pass

**Checkpoint**: User Story 2 independently functional and tested

---

## Phase 5: User Story 3 — Expiry Warning Escalation (Priority: P2)

**Goal**: Trader receives escalating email warnings at 14, 7, and 3 DTE. Each tier fires once per position per threshold crossing.

**Independent Test**: Seed Position with expiry_date = today + 14 days; run daily expiry check; confirm 14-day Alert created and email sent; advance date to +7 and +3 and confirm respective alerts fire independently.

### Tests for User Story 3 ⚠️ Write FIRST — confirm FAILING before T034

- [ ] T033 [P] [US3] Write unit tests for expiry warning tiers: 14d/7d/3d fire at correct DTE, do not repeat for same tier, all three tiers fire independently in `tests/unit/test_expiry_warning.py`

### Implementation for User Story 3

- [ ] T034 [P] [US3] Create plain-text email templates for `expiry_14d.txt`, `expiry_7d.txt`, `expiry_3d.txt` in `src/notifications/templates/`
- [ ] T035 [US3] Implement expiry warning rule with 3-tier escalation in `src/rules/expiry_warning.py`: for each open position, check DTE against 14/7/3 thresholds; fire only if no Alert exists for that position+tier in current crossing
- [ ] T036 [US3] Add daily expiry check job to APScheduler in `src/services/poll_scheduler.py`: runs at 09:30 ET on trading days; confirm `pytest tests/unit/test_expiry_warning.py` passes

**Checkpoint**: User Story 3 independently functional and tested

---

## Phase 6: User Story 4 — Binary Event Exit Protocol (Priority: P2)

**Goal**: Trader raises a binary event flag from the dashboard; system immediately sends a consolidated exit-all email listing every open position. Flag stays active with visible banner until explicitly cleared.

**Independent Test**: Seed 2 open positions; POST `/binary-event/raise`; confirm single Alert created with `alert_type='binary_event_exit'`, email delivered within 60s, and banner visible on dashboard.

### Tests for User Story 4 ⚠️ Write FIRST — confirm FAILING before T039

- [ ] T037 [P] [US4] Write integration test for binary event: raise flag → consolidated alert fires immediately → clearing flag resets state in `tests/integration/test_alert_pipeline.py`
- [ ] T038 [P] [US4] Write contract tests for `POST /binary-event/raise` and `POST /binary-event/clear` in `tests/contract/test_api_contracts.py`

### Implementation for User Story 4

- [ ] T039 [P] [US4] Create plain-text email template listing all open positions in `src/notifications/templates/binary_event_exit.txt`
- [ ] T040 [US4] Implement binary event rule engine in `src/rules/binary_event.py`: on flag raise, query all open positions, create single consolidated Alert, call email client immediately (not on poll cycle); idempotent per flag-raise event
- [ ] T041 [US4] Implement `POST /binary-event/raise` and `POST /binary-event/clear` routes in `src/api/routes/binary.py`: update BinaryEventFlag singleton; call binary event rule on raise; return updated `binary_banner.html` fragment
- [ ] T042 [P] [US4] Create `frontend/templates/partials/binary_banner.html`: prominent red Tailwind banner when active; hidden when inactive; HTMX OOB swap target
- [ ] T043 [US4] Wire binary banner into `frontend/templates/dashboard.html`; register binary routes in `src/api/main.py`; confirm `pytest tests/integration/test_alert_pipeline.py` and `pytest tests/contract/test_api_contracts.py` pass

**Checkpoint**: User Story 4 independently functional and tested

---

## Phase 7: User Story 5 — Thesis Groups & Position Scoring (Priority: P3)

**Goal**: Trader creates named thesis groups (template-based), assigns positions to them, sets exit goals per position, and sees two scoring signals: automatic exit proximity score and inherited thesis alignment rating.

**Independent Test**: Create thesis group "IV crush play"; assign 2 positions; set exit goal (profit_target_pct=50) on one position; run poll cycle; confirm exit_proximity_score > 0 on that position and both positions show thesis alignment rating on dashboard.

### Tests for User Story 5 ⚠️ Write FIRST — confirm FAILING before T047

- [ ] T044 [P] [US5] Write unit tests for exit proximity scoring: P&L %, DTE, and price target dimensions; composite max logic; no-goal case returns 0 in `tests/unit/test_exit_scoring.py`
- [ ] T045 [P] [US5] Write integration tests for thesis assignment + scoring: create thesis → assign positions → set exit goals → verify scores update on poll in `tests/integration/test_thesis_assignment.py`
- [ ] T046 [P] [US5] Write contract tests for `POST /thesis`, `PUT /thesis/{id}/alignment`, `DELETE /thesis/{id}`, `POST /positions/{id}/assign`, `POST /positions/{id}/exit-goals` in `tests/contract/test_api_contracts.py`

### Implementation for User Story 5

- [ ] T047 [US5] Implement exit proximity score computation in `src/rules/exit_scoring.py`: for each active ExitGoal, compute pnl_score, dte_score, price_score; return `max(scores)` as 0–100 int; 0 if no goals defined
- [ ] T048 [US5] Wire exit scoring into poll cycle in `src/services/poll_scheduler.py`: after position update, compute and persist ExitGoal.exit_proximity_score for all positions with defined goals
- [ ] T049 [US5] Implement thesis CRUD routes in `src/api/routes/thesis.py`: `POST /thesis` (create), `PUT /thesis/{id}/alignment` (update rating), `DELETE /thesis/{id}` (nullify member positions' thesis_id); return updated `thesis_panel.html` fragments
- [ ] T050 [US5] Implement position management routes in `src/api/routes/positions.py`: `POST /positions/{id}/assign` (set thesis_id), `POST /positions/{id}/exit-goals` (upsert ExitGoal); return updated `position_row.html` OOB fragment
- [ ] T051 [P] [US5] Create `frontend/templates/partials/thesis_panel.html`: sidebar listing thesis groups with template badge, alignment rating pill (colour-coded), and position count; HTMX form for create/delete
- [ ] T052 [P] [US5] Create `frontend/templates/partials/position_row.html`: single position row with exit proximity score bar (0–100 visual progress bar, Tailwind), thesis alignment rating badge, exit goal inline form trigger
- [ ] T053 [US5] Wire thesis panel and updated position rows into `frontend/templates/dashboard.html`; register all US5 routes in `src/api/main.py`; confirm all US5 tests pass

**Checkpoint**: User Story 5 independently functional and tested

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, mobile responsiveness, and end-to-end validation

- [ ] T054 [P] Add `GET /health` endpoint in `src/api/routes/dashboard.py`: return JSON with last_poll timestamp, DB status, and schwab_auth status
- [ ] T055 [P] Add `re_auth_required` SSE event emission in `src/api/routes/sse.py`: check AuthToken on each poll; emit event when re_auth_required=True
- [ ] T056 Run `quickstart.md` validation end-to-end: fresh install → Schwab OAuth → `alembic upgrade head` → `uvicorn` → open dashboard → confirm positions visible
- [ ] T057 [P] Tailwind mobile-responsive layout pass on `frontend/templates/`: collapse Greeks columns behind a toggle on small viewports; ensure position table scrolls horizontally on mobile; test at 375px width
- [ ] T058 [P] Add edge case unit tests: Greeks all-unavailable (Black-Scholes fails), thesis deletion moves positions to Unassigned, exit goal with no fields set in `tests/unit/`
- [ ] T059 Encrypt AuthToken access_token and refresh_token at rest using Fernet symmetric encryption keyed from `SECRET_KEY` env var in `src/auth/token_store.py`

---

---

## Phase 9: User Story 6 — Left Navigation Shell (Priority: P1)

**Goal**: Persistent left sidebar with "Thesis Monitor" and "Covered Call Screener" nav items. Active item highlighted. Mobile-responsive collapse. No new backend routes beyond a stub for `/screener`.

**Independent Test**: Open `http://localhost:8000`; confirm sidebar renders with both items; click each item; confirm correct view loads and active state updates. No brokerage connection required.

### Tests for User Story 6 ⚠️ Write FIRST — confirm FAILING before T062

- [ ] T060 [P] [US6] Write contract tests in `tests/contract/test_api_contracts.py`: `GET /` response HTML contains nav items "Thesis Monitor" and "Covered Call Screener"; `GET /screener` returns 200; active item receives highlight class based on current route

### Implementation for User Story 6

- [ ] T061 [US6] Restructure `frontend/templates/base.html`: change outer layout to `flex` row — `<aside>` left sidebar (fixed ~160px, `bg-gray-900 border-r border-gray-800`) containing nav items linking to `/` and `/screener`, active state driven by `current_page` context variable; keep existing top nav bar for logo and system controls; `<main>` content area fills remaining width
- [ ] T062 [US6] Update `src/api/routes/dashboard.py` `GET /` to pass `current_page="thesis_monitor"` in template context; create `src/api/routes/screener.py` with stub `GET /screener` route passing `current_page="covered_call_screener"`; register `screener` router in `src/api/main.py`
- [ ] T063 [P] [US6] Mobile responsive sidebar in `base.html`: sidebar collapses to a compact horizontal icon strip on viewports narrower than Tailwind `md` (768px); main content stacks below; confirm at 375px width

**Checkpoint**: User Story 6 independently functional and tested — nav shell ready for US7 and US8

---

## Phase 10: User Story 7 — Thesis Monitor View (Priority: P2)

**Goal**: Thesis-first health summary cards at `GET /`. Each card shows alignment rating, position count, aggregate exit proximity score, and combined P&L. Misaligned cards have red accent. Score ≥ 80 is highlighted. Cards expand inline to show individual position rows. SSE-driven updates.

**Independent Test**: Create 2 thesis groups with different alignment ratings; assign ≥ 1 position to each; open Thesis Monitor; confirm one card per group with correct counts, scores, and P&L; confirm misaligned card has red accent; confirm card expands to show position rows.

### Tests for User Story 7 ⚠️ Write FIRST — confirm FAILING before T067

- [ ] T064 [P] [US7] Write contract test in `tests/contract/test_api_contracts.py`: `GET /` HTML contains thesis card elements (name, alignment badge, position count, score, P&L)
- [ ] T065 [P] [US7] Write integration test in `tests/integration/test_thesis_assignment.py`: create 2 thesis groups + 2 positions each; call aggregation helper; assert correct avg score, combined P&L, and position count per group

### Implementation for User Story 7

- [ ] T066 [US7] Extend `src/api/_group_helpers.py` with `load_thesis_cards(session)`: for each thesis group query avg exit proximity score (across member positions with goals defined), sum of unrealised P&L, and position count; return list of thesis card dicts alongside existing helpers
- [ ] T067 [P] [US7] Create `frontend/templates/partials/thesis_cards.html`: grid of thesis health cards using ThinkorSwim palette; each card shows name + template badge + alignment rating pill (green=aligned, amber=partial, red=misaligned, grey=unrated); position count; avg exit proximity score with `≥80` highlight; combined P&L (green/red); "Unassigned" card last if unassigned positions exist; card body (hidden by default) shows inline position rows via HTMX `hx-get="/partials/positions?thesis_id={id}"` on expand
- [ ] T068 [US7] Update `frontend/templates/dashboard.html` to render `thesis_cards.html` partial as the primary content; wire `hx-get="/partials/thesis-cards"` SSE refresh; add `GET /partials/thesis-cards` route to `src/api/routes/partials.py` returning updated cards fragment
- [ ] T069 [US7] Update `src/api/routes/dashboard.py` `GET /` to call `load_thesis_cards` and pass results to template; confirm `pytest tests/contract/` and `pytest tests/integration/test_thesis_assignment.py` pass

**Checkpoint**: User Story 7 independently functional and tested

---

## Phase 11: User Story 8 — Covered Call Screener (Priority: P3)

**Goal**: Rank stock positions from second Schwab account by covered call income potential. IV Rank (primary), annualised yield, assignment safety (delta 0.20–0.30), earnings suppression. On-demand refresh only. Setup prompt when `SCHWAB_CC_ACCOUNT_ID` not configured.

**Independent Test**: Set `SCHWAB_CC_ACCOUNT_ID` to second account; open `/screener`; click Refresh; confirm ranked table with IV Rank, yield, delta, earnings proximity for each stock position. Test setup prompt by unsetting env var and reloading.

### Tests for User Story 8 ⚠️ Write FIRST — confirm FAILING before T072

- [ ] T070 [P] [US8] Write unit tests in `tests/unit/test_covered_call_screener.py`: composite score ranks high-IV position above low-IV; earnings suppression sets status to `earnings_risk`; liquidity exclusion sets status to `no_liquid_options`; call-already-written sets status to `call_written`; missing env var returns setup prompt flag
- [ ] T071 [P] [US8] Write contract tests in `tests/contract/test_api_contracts.py`: `GET /screener` returns 200 HTML; when env var missing, response contains setup prompt text; `POST /screener/refresh` returns 200 HTML fragment

### Implementation for User Story 8

- [ ] T072 [US8] Implement `src/services/covered_call_screener.py`: `screen(schwab_client, account_id) -> list[CoveredCallCandidate]`; fetch stock positions from `account_id` via schwab-py; for each position call Schwab `/marketdata/v1/chains` for 30–45 DTE window; find best call strike where delta is closest to 0.25 with bid ≥ 0.05 and OI ≥ 100; compute IV Rank (current IV vs 52-week IV range from chain data), annualised yield `((bid / stock_price) * (365 / dte))`, composite score `(iv_rank * 0.50) + (yield_score * 0.30) + (delta_safety * 0.20)`; apply suppression rules (earnings within 7d → `earnings_risk`, no liquid options → `no_liquid_options`, existing short call detected → `call_written`); return sorted descending by composite score
- [ ] T073 [US8] Implement `src/api/routes/screener.py`: `GET /screener` renders `screener.html` — if `SCHWAB_CC_ACCOUNT_ID` not set, pass `setup_required=True`; `POST /screener/refresh` calls screener service and returns `screener_table.html` fragment via HTMX swap; register routes in `src/api/main.py`
- [ ] T074 [P] [US8] Create `frontend/templates/screener.html` extending `base.html`: setup prompt block (shown when `setup_required=True`) with env var name and instructions; screener table section with `hx-post="/screener/refresh"` Refresh button; create `frontend/templates/partials/screener_table.html`: ranked table with columns ticker / shares / price / IV Rank (highlighted >50 in green) / rec. strike / rec. expiry / bid / yield % / delta / DTE to earnings / score / status badge; status badges: `RANKED` (default), `AVOID — EARNINGS RISK` (amber), `CALL WRITTEN` (grey), `NO LIQUID OPTIONS` (dark grey)
- [ ] T075 [US8] Confirm all US8 unit and contract tests pass; note that end-to-end validation with live second account is deferred until `SCHWAB_CC_ACCOUNT_ID` is configured

**Checkpoint**: User Story 8 independently functional and tested (unit + contract); live validation deferred

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Foundational — first user story (MVP)
- **US2, US3, US4 (Phases 4–6)**: All depend on Foundational + US1 email infrastructure (T029)
- **US5 (Phase 7)**: Depends on Foundational; independent of US2–US4
- **US6 (Phase 9)**: Depends on US1 (base.html already exists); blocks US7 and US8 visually but not functionally
- **US7 (Phase 10)**: Depends on US5 (thesis groups must exist); requires US6 nav shell
- **US8 (Phase 11)**: Depends on US6 nav shell; independent of US2–US7 backend logic
- **Polish (Phase 8)**: Depends on all user stories complete

### Critical Path

Setup → Foundational → US1 → US2 (email client T029 needed by US3, US4) → US3 + US4 (parallel) → US5 → US6 → US7 + US8 (parallel) → Polish

### Parallel Opportunities Within US1

```bash
# After Foundational completes, launch together:
T015: tests/unit/test_bs_calculator.py
T016: tests/contract/test_api_contracts.py
T017: tests/integration/test_polling_cycle.py
T024: frontend/templates/dashboard.html
T025: frontend/templates/partials/positions_table.html

# Then sequentially:
T018 → T019 → T020 → T021 → T022 → T023 → T026
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and validate**: open dashboard, confirm positions with Greeks visible
5. Demo to yourself — this is the foundation everything else builds on

### Incremental Delivery

1. Setup + Foundational → skeleton runs
2. US1 → dashboard live with Greeks (MVP)
3. US2 → profit target alerts (core money rule)
4. US3 + US4 → expiry + binary event alerts (parallel if desired)
5. US5 → thesis groups + scoring (decision support layer)
6. Polish → hardening + mobile

---

## Summary

| Phase | Tasks | Story |
|---|---|---|
| Setup | T001–T005 | — |
| Foundational | T006–T014 | — |
| US1 — Dashboard | T015–T026 | P1 |
| US2 — Profit Alert | T027–T032 | P2 |
| US3 — Expiry Warnings | T033–T036 | P2 |
| US4 — Binary Event | T037–T043 | P2 |
| US5 — Thesis & Scoring | T044–T053 | P3 |
| Polish | T054–T059 | — |
| US6 — Left Nav Shell | T060–T063 | P1 |
| US7 — Thesis Monitor | T064–T069 | P2 |
| US8 — Covered Call Screener | T070–T075 | P3 |
| **Total** | **75 tasks** | |
