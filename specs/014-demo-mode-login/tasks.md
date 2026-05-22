# Tasks: Demo Mode Login (014)

**Input**: Design documents from `specs/014-demo-mode-login/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks grouped by user story — each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to
- All task descriptions include exact file paths

---

## Phase 1: Setup

**Purpose**: Confirm test infrastructure before writing failing tests.

- [x] T001 Confirm `tests/unit/` and `tests/contract/` directories exist; if absent, create `tests/unit/__init__.py` and `tests/contract/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Failing tests written first (Principle IV), then the `isDemoMode()` guard and
`/auth/demo-login` endpoint that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Write failing test: `GET /auth/demo-login` returns 200 HTML containing `sessionStorage.setItem('demo_mode'` and `window.location.replace('/')`, with a CSP nonce attribute on the `<script>` tag, in `tests/unit/test_demo_mode_login.py`
- [x] T003 [P] Write failing test: validate `DEMO_POSITIONS_SPREADS` entries each match `PositionView` schema (required fields, correct types, no null Greeks); validate `DEMO_SCREENER_RESULTS` entries match `ScreenerResultView` schema, in `tests/contract/test_demo_mode_contract.py`
- [x] T004 Add `DEMO_MODE_KEY = 'demo_mode'` constant and export `isDemoMode()` function to `frontend/static/js/auth.js` (reads `sessionStorage.getItem(DEMO_MODE_KEY) === 'true'`)
- [x] T005 Add rate-limited (30/minute) `GET /auth/demo-login` endpoint to `src/auth/router.py` — inline script sets `demo_mode=true` in sessionStorage using CSP nonce, then `window.location.replace('/')`, with `<noscript>` fallback; run T002 test and confirm it passes

**Checkpoint**: `isDemoMode()` exported, `/auth/demo-login` endpoint live, T002 passing. All user stories can now be worked on.

---

## Phase 3: User Story 1 — Demo Entry via Yellow Button (Priority: P1) 🎯 MVP

**Goal**: User clicks yellow "Try Demo" on login page, lands on dashboard in demo mode with no OAuth redirect.

**Independent Test**: Click "Try Demo" → dashboard loads in <3 s → `sessionStorage['demo_mode'] === 'true'` → zero requests to Schwab domain (quickstart Scenarios 1 and 2).

### Implementation for User Story 1

- [x] T006 [US1] Add yellow "Try Demo" anchor button (href `/auth/demo-login`, amber/yellow background `#c8a820`, dark text `#0c0c10`) below the "Connect Schwab Account" button in `frontend/templates/login.html`
- [x] T007 [US1] Create `frontend/static/js/demo_data.js`: export `DEMO_SPREADS_HASH = 'demo-spreads-0001'`, `DEMO_EQUITY_HASH = 'demo-equity-0002'`, `DEMO_ACCOUNTS` array (2 entries matching `/api/accounts` shape), and a stub `demoResponse(url)` that returns `DEMO_ACCOUNTS` for `/api/accounts` and an empty array `[]` for all other paths
- [x] T008 [US1] Modify `fetchWithAuth()` in `frontend/static/js/auth.js`: add `if (isDemoMode()) { const { demoResponse } = await import('./demo_data.js'); return demoResponse(url); }` as the first check, before the token retrieval block
- [x] T009 [US1] Verify quickstart Scenarios 1 and 2: login page shows yellow button; clicking it lands on dashboard without Schwab redirect; DevTools confirms `demo_mode=true` in sessionStorage; no requests to external domains

**Checkpoint**: User Story 1 fully functional — demo entry works end-to-end. Deploy/demo if ready.

---

## Phase 4: User Story 4 — Complete Isolation & DEMO Banner (Priority: P1)

**Goal**: DEMO MODE banner visible on all pages in demo mode; session cleared on logout; real Schwab login unaffected after demo session.

**Independent Test**: Banner present on dashboard; logout clears all demo sessionStorage keys; subsequent Schwab login works normally (quickstart Scenarios 3, 9, 10).

### Implementation for User Story 4

- [x] T010 [US4] In `frontend/templates/base.html`, insert immediately after `<body>`: a hidden `<div id="demo-banner">` with amber background (`#c8a820`), dark text, and the label `DEMO MODE — data is simulated and does not reflect real account balances`; followed by a `<script nonce="{{ csp_nonce }}">` block that sets `document.getElementById('demo-banner').style.display = 'block'` when `sessionStorage.getItem('demo_mode') === 'true'`
- [x] T011 [US4] Verify quickstart Scenarios 3, 9, and 10: banner visible on dashboard and screener in demo mode; logout clears `demo_mode` and `schwab_selected_account` from sessionStorage; fresh Schwab OAuth login (or dev-login) succeeds with no demo artefacts

**Checkpoint**: Both P1 stories complete — demo entry + isolation both verified.

---

## Phase 5: User Story 2 — Option Spreads Demo Account (Priority: P2)

**Goal**: Positions table shows 6 realistic option spread legs (AAPL put spread, SPY iron condor, TSLA call spread) when the spreads demo account is selected.

**Independent Test**: Select "DEMO — Options Spreads" → positions table renders 6 rows with symbol, strike, expiry, P&L, and non-null Greeks (quickstart Scenarios 4 and 5).

### Implementation for User Story 2

- [x] T012 [US2] Replace the stub `demoResponse()` in `frontend/static/js/demo_data.js` with the full implementation: export `DEMO_POSITIONS_SPREADS` array (6 PositionView-shaped objects per `research.md` D-007: AAPL 195P short, AAPL 185P long, SPY 520P short, SPY 560C short, TSLA 280C short, TSLA 295C long); update `demoResponse(url)` to return `DEMO_POSITIONS_SPREADS` when `pathname === '/api/positions/refresh'` and account hash is not `DEMO_EQUITY_HASH`
- [x] T013 [US2] Confirm T003 contract test passes for spreads data; verify quickstart Scenarios 4 and 5: account picker shows 2 demo accounts; spreads account renders 6 position rows with populated Greek columns

**Checkpoint**: User Story 2 complete — spreads positions visible and correct.

---

## Phase 6: User Story 3 — Equities & ETFs Demo Account (Priority: P2)

**Goal**: Equity account shows 2 covered call positions in the positions tab and 4 screener candidates (AAPL recommended, VOO recommended, QQQ suppressed, MSFT suppressed) in the screener tab.

**Independent Test**: Select "DEMO — Equities & ETFs" → 2 CCs in positions table → screener shows 4 rows with correct recommendation_status (quickstart Scenarios 6 and 7).

### Implementation for User Story 3

- [x] T014 [US3] Extend `frontend/static/js/demo_data.js`: add `DEMO_POSITIONS_EQUITY` array (2 covered-call PositionView objects: AAPL 220C short, VOO 510C short) and `DEMO_SCREENER_RESULTS` array (4 ScreenerResultView objects: AAPL recommended, VOO recommended, QQQ suppressed low-IV, MSFT suppressed near-earnings) per `research.md` D-007; update `demoResponse()` to serve correct arrays when `account_hash === DEMO_EQUITY_HASH` for both `/api/positions/refresh` and `/api/screener/refresh`
- [x] T015 [US3] Confirm T003 contract test passes for all data sets; verify quickstart Scenarios 6, 7, and 8: equity account shows 2 CC positions; screener shows 4 rows with correct statuses; DevTools confirms zero requests to external domains throughout the full demo session

**Checkpoint**: All four user stories complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and any cross-cutting cleanup.

- [ ] T016 Run all 10 quickstart.md scenarios sequentially in a browser and confirm every scenario passes; record any failures and fix before marking complete
- [x] T017 [P] Review `tests/unit/test_demo_mode_login.py` and `tests/contract/test_demo_mode_contract.py` for completeness: ensure edge cases covered (rate limit hit returns 429; `/auth/demo-login` called with missing CSP nonce still sets `demo_mode`; demo hash prefix `demo-` cannot match any real Schwab hash format)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user story work**
- **US1 (Phase 3)**: Depends on Foundational (needs `isDemoMode()` and endpoint)
- **US4 (Phase 4)**: Depends on Foundational (needs `isDemoMode()` for banner script)
- **US2 (Phase 5)**: Depends on US1 (needs `fetchWithAuth()` wiring from T008)
- **US3 (Phase 6)**: Depends on US2 (extends `demo_data.js` created in T012)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

```
Foundational
    ├── US1 (Phase 3) ──> US2 (Phase 5) ──> US3 (Phase 6)
    └── US4 (Phase 4)  [independent of US2/US3]
```

US4 can be worked in parallel with US2/US3 once US1 is complete (banner needs
`isDemoMode()` from Foundational, but not the positions data from US2/US3).

### Within Each Phase

- T002 and T003 MUST exist and FAIL before T005 (Principle IV: test-first)
- T007 (demo_data.js stub) must precede T008 (fetchWithAuth wiring) — import would fail otherwise
- T012 (full demo_data.js) must precede T014 (equity extension)

---

## Parallel Execution Examples

### Parallel within Foundational (Phase 2)

```
T002 — write test_demo_mode_login.py
T003 — write test_demo_mode_contract.py      [parallel with T002 — different file]
```

### Parallel within US1 (Phase 3)

```
T007 — create demo_data.js stub
T006 — add yellow button to login.html       [parallel with T007 — different file]
```

### Parallel within Polish (Phase 7)

```
T016 — run all quickstart scenarios
T017 — extend test coverage                  [parallel with T016 — different files]
```

---

## Implementation Strategy

### MVP First (US1 + US4 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (tests written failing; endpoint + isDemoMode added)
3. Complete Phase 3: User Story 1 (yellow button + demo entry working)
4. Complete Phase 4: User Story 4 (banner + isolation verified)
5. **STOP and VALIDATE**: Quickstart Scenarios 1–3, 9–10 all pass
6. Deploy/demo — users can enter demo mode and see the banner

### Full Delivery (all stories)

1. MVP above
2. Phase 5: US2 (spreads positions)
3. Phase 6: US3 (equity positions + screener)
4. Phase 7: Full quickstart validation
5. Final deploy

---

## Notes

- [P] tasks = different files, no unresolved dependencies — safe to run concurrently
- Tests T002 and T003 MUST fail before implementation (Principle IV)
- `demo_data.js` is loaded lazily via dynamic `import()` inside `fetchWithAuth` — the stub in T007 MUST be created before T008 modifies `fetchWithAuth`
- Demo hashes use `demo-` prefix (cannot collide with real Schwab hashes — see data-model.md)
- No changes to any existing API route; all demo interception is client-side
- `eraseAll()` in `auth.js` already calls `sessionStorage.clear()` — no change required to clear `demo_mode`
