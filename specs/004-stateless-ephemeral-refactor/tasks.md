# Tasks: Stateless Ephemeral Refactor

**Input**: Design documents from `specs/004-stateless-ephemeral-refactor/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/http.md ✅ quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to
- Exact file paths are required in every task description

---

## Phase 1: Teardown (Delete Dead Code)

**Purpose**: Remove all infrastructure that no longer has a role. These deletions unblock every subsequent phase by eliminating import conflicts.

- [x] T001 Strip removed packages from `requirements.txt`: delete `sqlalchemy[asyncio]`, `aiosqlite`, `alembic`, `apscheduler`, `aiosmtplib`, `cryptography`, `holidays`, `sse-starlette`; remove `itsdangerous` (no longer needed — no server-side sessions)
- [x] T002 [P] Delete `src/data/migrations/` directory (all versions and env.py) and `alembic.ini` if present
- [x] T003 [P] Delete `src/auth/token_store.py`
- [x] T004 [P] Delete `src/notifications/` directory (email_client.py and __init__.py)
- [x] T005 [P] Delete `src/rules/` directory (profit_target.py, expiry_warning.py, exit_scoring.py, binary_event.py, __init__.py)
- [x] T006 [P] Delete `src/services/poll_scheduler.py`, `src/services/thesis_health.py`, `src/services/position_groups.py`
- [x] T007 [P] Delete `src/api/routes/sse.py`, `src/api/routes/admin.py`, `src/api/routes/thesis.py`, `src/api/routes/binary.py`
- [x] T008 [P] Delete `src/api/_group_helpers.py`

**Checkpoint**: All deleted modules removed. `git status` shows only deletions + requirements.txt change. No `src/` files should import from deleted modules yet — Phase 2 fixes remaining imports.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core stateless infrastructure. Every user story depends on these tasks completing first.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T009 Replace `src/data/models.py` with Pydantic in-memory models: `PositionView` and `ScreenerResultView` per `specs/004-stateless-ephemeral-refactor/data-model.md` — no SQLAlchemy imports
- [x] T010 Refactor `src/api/deps.py`: remove `get_session` and all SQLAlchemy imports; add `get_schwab_client(request: Request)` dependency that reads the Bearer token from the `Authorization` header (`request.headers.get("Authorization")`), strips the `Bearer ` prefix, and returns a configured schwab async client using `client_from_access_functions`; raise `HTTPException(401)` if header is absent or malformed
- [x] T011 Refactor `src/auth/schwab_oauth.py`: replace file-based token logic with `build_auth_url() -> tuple[str, str]` (returns Schwab authorize URL and PKCE state string — no server session involved) and `exchange_code_for_token(received_url: str, state: str) -> dict` (exchanges code for token dict and returns it — caller is responsible for delivering it to the browser); use `schwab.auth.client_from_access_functions` to rebuild clients from a token dict passed in per-request
- [x] T012 Refactor `src/api/main.py`: remove `start_scheduler`/`stop_scheduler` lifespan; remove lifespan context manager entirely; do NOT add `SessionMiddleware` (no server-side sessions); remove deleted route imports (`sse`, `admin`, `thesis`, `binary`); add auth router import; keep `dashboard`, `partials`, `positions`, `screener` routers; configure uvicorn access log format to exclude `Authorization` header values

**Checkpoint**: App starts cleanly (`uvicorn src.api.main:app`). No import errors. No SessionMiddleware. No DB connection attempted on startup.

---

## Phase 3: User Story 1 — Schwab OAuth Login (Priority: P1) 🎯 MVP

**Goal**: Users log in via Schwab OAuth. The token is delivered to the browser via an inline script in the callback page and stored in `sessionStorage`. The server never holds the token after the callback response is sent.

**Independent Test**: Start the app, open `/`, get redirected to `/auth/login`. Click "Connect Schwab Account". Complete Schwab OAuth flow. Open DevTools → Application → sessionStorage — token present. Open DevTools → Network — no `Set-Cookie` header on the callback response containing a token. Open Cloud Run logs — no token value visible. Click "Disconnect" — sessionStorage empty, redirected to login.

### Implementation

- [x] T013 [US1] Create `src/api/routes/auth.py`: `GET /auth/login` (render login.html), `GET /auth/connect` (call `build_auth_url()`, store PKCE state in a short-lived server-side state cookie for CSRF validation only, redirect to Schwab), `GET /auth/callback` (validate state cookie, call `exchange_code_for_token(received_url, state)`, render a minimal HTML page with an inline `<script>` that calls `sessionStorage.setItem('schwab_token', JSON.stringify({...}))` then `window.location.replace('/')` — token delivered to browser and immediately moved to sessionStorage), `POST /auth/logout` (render a page that calls `sessionStorage.clear()`, `localStorage.clear()`, then `indexedDB.deleteDatabase('option-sentinel')` before redirecting to `/auth/login`)
- [x] T014 [US1] Create `frontend/templates/login.html`: ThinkorSwim-styled page with "Option Sentinel" heading, brief one-paragraph description of the privacy model (token stays in your browser, server never stores it), and a single "Connect Schwab Account" button linking to `/auth/connect`; extend `base.html`; no nav sidebar when unauthenticated
- [x] T015 [US1] Create `frontend/static/js/auth.js`: exports `getToken()` (reads `sessionStorage.getItem('schwab_token')` and parses JSON), `isAuthenticated()` (returns true if token exists and not expired), and `eraseAll()` (clears sessionStorage, localStorage, deletes IndexedDB `option-sentinel` database, redirects to `/auth/login`); used by all other JS modules
- [x] T016 [US1] Add server-side auth guard in `src/api/deps.py`: `require_auth(request)` dependency checks for `Authorization: Bearer` header; if absent returns 401 JSON `{"error": "unauthenticated"}` (client JS intercepts 401s and redirects to login); apply to all non-auth, non-health route handlers
- [x] T017 [US1] Write unit tests in `tests/unit/test_schwab_oauth.py`: test `build_auth_url()` returns a valid URL string and state, test `exchange_code_for_token()` returns a token dict given a mocked Schwab response, test `require_auth` returns 401 when Authorization header absent

**Checkpoint**: OAuth flow completes. Token in sessionStorage confirmed via DevTools. No token in cookies or server logs. Logout clears all browser storage.

---

## Phase 4: User Story 2 — Live Positions Dashboard (Priority: P1)

**Goal**: Authenticated user sees a Refresh button that fetches live positions + Greeks from Schwab and renders them in the positions table. No automatic polling.

**Independent Test**: Log in. Dashboard loads (empty table, Refresh button visible). Click Refresh. Table populates with live position data including Greeks. Click Refresh again — data updates. No SSE connection in browser network tab.

### Implementation

- [x] T018 [US2] Refactor `src/services/schwab_client.py`: delete `sync_positions_and_greeks` (DB-writing version); add `fetch_positions_and_greeks(schwab_client) -> list[PositionView]` that calls the existing `_fetch_positions` and `_fetch_greeks` helpers, builds `PositionView` objects using `build_greeks` from `src/services/greeks_service.py`, computes `unrealised_pnl` and `days_to_expiry` in-memory, and returns a plain list — no session, no DB
- [x] T019 [US2] Refactor `src/services/greeks_service.py`: update `build_greeks` signature to accept raw position dict and Greeks dict instead of SQLAlchemy `Position` model; return a plain dict keyed by the `PositionView` Greek field names; keep Black-Scholes fallback logic intact
- [x] T020 [US2] Create `GET /api/positions/refresh` in `src/api/routes/positions.py`: extract Bearer token from `Authorization` header via `get_schwab_client` dep; call `fetch_positions_and_greeks`; return raw JSON array of `PositionView` objects (not an HTML partial — client JS renders and caches); do NOT log the Authorization header value
- [x] T021 [US2] Create `frontend/static/js/position_cache.js`: exports `savePositions(positions)` (writes positions JSON array to IndexedDB `option-sentinel` store `positions` with key `latest`), `loadPositions()` (reads latest cached positions from IndexedDB, returns null if empty), `clearPositions()` (deletes all records from the positions store)
- [x] T022 [US2] Create `frontend/static/js/positions_ui.js`: on Refresh button click, reads token from `auth.getToken()`, sends `fetch('/api/positions/refresh', {headers: {Authorization: 'Bearer ...'}})`, on success calls `position_cache.savePositions()` then renders the positions table from JSON (applying thesis assignments from `thesis_store.getAssignments()`); on page load, calls `position_cache.loadPositions()` and renders cached data immediately with a "last refreshed at X" timestamp badge
- [x] T023 [US2] Refactor `src/api/routes/dashboard.py`: remove all DB session dependencies, `poll_scheduler` import, `BinaryEventFlag` query, `_group_helpers` import; `GET /` renders `dashboard.html` shell (no position data server-side); update `/health` to return `{"status": "ok"}` with no DB check
- [x] T024 [US2] Refactor `frontend/templates/dashboard.html`: remove SSE JavaScript and EventSource setup; add Refresh button wired to `positions_ui.js`; add `<div id="positions-table">` placeholder; import `auth.js`, `position_cache.js`, `positions_ui.js` as ES modules; keep ThinkorSwim styling
- [x] T025 [US2] Refactor `frontend/templates/base.html`: remove SSE connection setup, EventSource JS, `sse-starlette` client scripts; remove references to deleted routes in nav; add "Erase All Data" button in nav wired to `auth.eraseAll()` with a confirmation dialog
- [x] T026 [US2] Write contract test in `tests/contract/test_positions_api.py`: mock `fetch_positions_and_greeks` to return two `PositionView` fixtures; assert `GET /api/positions/refresh` with valid `Authorization` header returns 200 JSON array; assert request without `Authorization` header returns 401; assert response does not set any cookies

**Checkpoint**: Full positions refresh cycle works. Dashboard loads in < 1s. Clicking Refresh fetches and renders positions. Greeks show source indicators. No SSE connection established.

---

## Phase 5: User Story 4 — Erase All Data (Priority: P2)

**Goal**: A single button wipes every trace of trader data from the browser — token, position cache, thesis groups, everything. Implemented as a client-side-only operation; the server has nothing to delete.

**Independent Test**: Log in, refresh positions, create thesis group. Click "Erase All Data", confirm prompt. Open DevTools → Application: sessionStorage empty, IndexedDB empty, localStorage empty. Page shows login screen.

### Implementation

- [x] T027 [US4] Verify `auth.eraseAll()` in `frontend/static/js/auth.js` (from T015) correctly sequences: `sessionStorage.clear()` → `localStorage.clear()` → `indexedDB.deleteDatabase('option-sentinel')` (awaited) → `window.location.replace('/auth/login')`; write a unit test in `tests/unit/test_erase_all.js` using a mock browser environment that confirms each storage layer is cleared before redirect
- [x] T028 [US4] Confirm the "Erase All Data" button in `base.html` (added in T025) shows a `window.confirm()` prompt before calling `auth.eraseAll()`; button must be visible in the nav on all authenticated pages

**Checkpoint**: Erase All clears all three storage mechanisms. DevTools confirms empty state. Redirect to login occurs. Server receives no request during the erase operation.

---

## Phase 6: User Story 3 — Browser-Persisted Thesis Groups (Priority: P2)

**Goal**: Thesis groups and position-to-thesis assignments are stored in browser localStorage. The server is never involved. The dashboard applies assignments client-side after the positions table is populated.

**Independent Test**: Create a thesis group via the dashboard UI. Assign a position to it. Reload the page. Click Refresh. The thesis label appears in the position row — no server request for thesis data in browser network tab.

### Implementation

- [x] T029 [US3] Create `frontend/static/js/thesis_store.js`: plain JS module with functions `getThesisGroups()`, `saveThesisGroup(group)`, `deleteThesisGroup(id)`, `getAssignments()`, `setAssignment(symbol, thesisGroupId)` — all read/write from `localStorage` keys `thesis_groups` and `thesis_assignments`; export as ES module
- [x] T030 [US3] Create `frontend/static/js/thesis_ui.js`: wires up thesis create/assign form inputs to `thesis_store.js` save functions; called by `positions_ui.js` after table render to apply thesis labels to position rows
- [x] T031 [US3] Update `frontend/templates/dashboard.html` to include thesis group create/assign UI as a client-side-only panel (no form `action` to any server route); import `thesis_store.js` and `thesis_ui.js` as ES modules; remove any `<form>` that POSTs to `/thesis/*` routes

**Checkpoint**: Thesis groups persist across page reloads (localStorage). Assignments render in position rows after Refresh. No `/thesis/*` network requests made.

---

## Phase 7: User Story 5 — Covered Call Screener (Priority: P2)

**Goal**: Authenticated user clicks Refresh on the screener page and gets live covered-call recommendations computed from the second Schwab account — no DB read or write.

**Independent Test**: Log in. Navigate to `/screener`. Click Refresh. Table of ranked covered-call recommendations appears. Positions within 7 days of earnings show "Suppressed" status. Clicking Refresh again fetches fresh data.

### Implementation

- [x] T032 [US5] Refactor `src/services/covered_call_screener.py`: remove all SQLAlchemy session parameters and `ScreenerResult` DB model writes; add `run_screener(schwab_client) -> list[ScreenerResultView]` that fetches long stock positions from `SCHWAB_SCREENER_ACCOUNT_ID`, computes rankings, and returns a plain `list[ScreenerResultView]` — no persistence
- [x] T033 [US5] Refactor `src/api/routes/screener.py`: add `GET /api/screener/refresh` endpoint that reads Bearer token via `get_schwab_client` dep, calls `run_screener`, returns JSON array of `ScreenerResultView`; remove DB-writing logic; keep `GET /screener` as shell page render only; do NOT log Authorization header
- [x] T034 [US5] Create `frontend/static/js/screener_ui.js`: on Refresh button click, reads token from `auth.getToken()`, sends `fetch('/api/screener/refresh', {headers: {Authorization: 'Bearer ...'}})`, renders screener table from JSON response; show "Suppressed" badge for suppressed rows
- [x] T035 [US5] Update `frontend/templates/screener.html`: add Refresh button wired to `screener_ui.js`; add `<div id="screener-table">` placeholder; import `auth.js` and `screener_ui.js` as ES modules; keep ThinkorSwim styling
- [x] T036 [US5] Write contract test in `tests/contract/test_screener_api.py`: mock `run_screener` to return two `ScreenerResultView` fixtures; assert `GET /api/screener/refresh` with valid `Authorization` header returns 200 JSON array; assert request without header returns 401

**Checkpoint**: Screener page loads instantly (empty). Refresh populates table with live results. Suppressed positions are visually distinct. No DB activity in server logs.

---

## Phase 8: User Story 6 — Cloud Run Deployment (Priority: P3)

**Goal**: App is containerised, deployable to Cloud Run with scale-to-zero, and cold-starts in under 3 seconds.

**Independent Test**: Build Docker image locally. Run container with env vars set. `curl http://localhost:8080/health` returns `{"status":"ok"}` within 3 seconds of container start. Cold-start time logged in container output.

### Implementation

- [x] T037 [US6] Create `Dockerfile`: `python:3.11-slim` base; copy `requirements.txt`, `pip install --no-cache-dir -r requirements.txt`; copy `src/`, `frontend/`; expose port 8080; `CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]` — access logging disabled to prevent any chance of token values appearing in logs; use Cloud Run structured logging instead
- [x] T038 [US6] Update `.env.example`: remove `DATABASE_URL`, `SCHWAB_TOKEN_PATH`, `SECRET_KEY` (old DB encryption var); add `SCHWAB_SCREENER_ACCOUNT_ID`; add `OAUTH_STATE_SECRET` (for signing the short-lived CSRF state cookie only — separate from any token); add comments for Cloud Run Secret Manager usage
- [x] T039 [US6] Verify `/health` endpoint returns `{"status": "ok"}` with no auth required and no DB check; add smoke test in `tests/unit/test_health.py`
- [x] T040 [US6] Add `.dockerignore` excluding `__pycache__`, `*.pyc`, `.env`, `*.sqlite`, `schwab_token.json`, `specs/`, `tests/` to minimise image size

**Checkpoint**: `docker build` succeeds. `docker run` with env vars starts and serves `/health` in < 3 s. Image size < 500 MB.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [x] T041 [P] Remove remaining dead test files: `tests/integration/test_thesis_assignment.py`, `tests/unit/test_covered_call_screener.py`, `tests/contract/test_api_contracts.py` (replaced by new contract tests from T026, T036)
- [x] T042 [P] Update `tests/` conftest.py: remove DB fixture setup (`AsyncSessionLocal`, migration calls); add an `auth_headers` fixture that returns `{"Authorization": "Bearer <mock_token>"}` for route tests
- [x] T043 Run `pytest tests/` and confirm all new tests pass; fix any import errors from Phase 1 deletions
- [x] T044 Validate `specs/004-stateless-ephemeral-refactor/quickstart.md` against actual local run: follow each step, confirm app starts, OAuth flow completes, positions refresh, screener refresh, Erase All all work
- [x] T045 Write `README.md` "Privacy & Data Handling" section (new, detailed): explain the full login flow step by step, where each piece of data lives (sessionStorage/IndexedDB/localStorage), that Cloud Run only forwards the token and never stores it, and how to use the Erase All button; remove DB setup steps from existing README; add Cloud Run deployment section

---

## Phase 10: Multi-User OAuth (from `specs/multi-user-oauth.md`, 2026-05-13)

**Purpose**: Replace session-cookie auth and hardcoded account env vars with stateless PKCE OAuth,
raw Bearer token delivery to sessionStorage, dynamic account resolution, and simplified 401→login
error handling (no silent refresh).

**⚠️ SPEC CHANGE**: `schwab_refresh_token` is NOT stored. Any 401 → `eraseAll()` → login.

- [x] T046 Remove `itsdangerous` from `requirements.txt`; verify no remaining imports of `itsdangerous` in codebase
- [x] T047 Create `src/auth/router.py`: `GET /auth/login` (render login.html), `GET /auth/start` (PKCE: generate verifier+challenge+state, store in `_pkce_store` dict, redirect to `SCHWAB_AUTH_URL`), `GET /auth/callback` (lookup+delete state from dict, httpx POST to `SCHWAB_TOKEN_URL`, HTML inline script stores only `schwab_access_token` in sessionStorage), `GET /auth/dev-login` (extract `access_token` from `schwab_token.json`, store as `schwab_access_token`), `POST /auth/logout` (HTML that calls `eraseAll()` JS sequence). NO `/auth/refresh` route.
- [x] T048 Update `src/api/main.py`: in `create_app()`, add startup validation — check `SCHWAB_CLIENT_ID`, `SCHWAB_CLIENT_SECRET`, `SCHWAB_REDIRECT_URI`, `SCHWAB_AUTH_URL`, `SCHWAB_TOKEN_URL` are all set, raise `RuntimeError` with missing names if any absent; replace `from src.api.routes import auth` import with `from src.auth import router as auth_module` and `app.include_router(auth_module.router)`
- [x] T049 Delete `src/api/routes/auth.py` (all functionality moved to `src/auth/router.py`)
- [x] T050 Update `src/api/deps.py`: replace `get_schwab_client` implementation — `get_current_token(request) -> str` extracts raw Bearer string (raises 401 if absent/malformed); `build_schwab_client(access_token: str)` wraps token as `{"creation_timestamp": now, "token": {"access_token": ..., "token_type": "Bearer"}}` and calls `client_from_access_functions` with `SCHWAB_CLIENT_ID`/`SCHWAB_CLIENT_SECRET`; `get_schwab_client` combines both as a FastAPI dependency
- [x] T051 [P] Update `src/services/covered_call_screener.py`: remove `SCHWAB_CC_ACCOUNT_ID` env var guard and early return; replace `resolve_account_hash(client, account_id)` call with `list_accounts(client)` → use `accounts[0]["hashValue"]`; log warning and return `[]` if no accounts found
- [x] T052 [P] Update `src/services/schwab_client.py`: remove `ACCOUNT_ID = os.getenv(...)` global; in `_fetch_positions`, replace `resolve_account_hash(client, ACCOUNT_ID)` with `list_accounts(client)` → `accounts[0]["hashValue"]`
- [x] T053 Rewrite `frontend/static/js/auth.js`: export `getAccessToken()` (reads `sessionStorage.getItem('schwab_access_token')`); export `isAuthenticated()` (returns `!!getAccessToken()`); export `fetchWithAuth(url, options={})` (attaches `Authorization: Bearer <token>`, on 401 calls `eraseAll()`); export `eraseAll()` (unchanged: clears sessionStorage+localStorage+IndexedDB, redirects to `/auth/login`); remove `getToken()`, `getAuthHeader()`, all base64 encoding
- [x] T054 [P] Update `frontend/static/js/positions_ui.js`: import `fetchWithAuth, isAuthenticated` instead of `getAuthHeader`; in `refreshPositions()`, replace `isAuthenticated()` guard + manual `fetch` with `const resp = await fetchWithAuth('/api/positions/refresh')` followed by `if (!resp) return;` guard; remove explicit `Authorization` header construction
- [x] T055 [P] Update `frontend/static/js/screener_ui.js`: same pattern as T054 — import `fetchWithAuth, isAuthenticated`; replace manual fetch+auth with `fetchWithAuth`
- [x] T056 [P] Update `frontend/templates/login.html`: change `href="/auth/connect"` to `href="/auth/start"`
- [x] T057 [P] Update `.env`: add `SCHWAB_CLIENT_ID` (= current `SCHWAB_APP_KEY` value), `SCHWAB_CLIENT_SECRET` (= `SCHWAB_APP_SECRET`), `SCHWAB_REDIRECT_URI` (= `SCHWAB_CALLBACK_URL`), `SCHWAB_AUTH_URL=https://api.schwabapi.com/v1/oauth/authorize`, `SCHWAB_TOKEN_URL=https://api.schwabapi.com/v1/oauth/token`; old vars can remain for reference but are no longer read by the app
- [x] T058 [P] Update `.env.example`: replace old var names with new ones; remove `DATABASE_URL`, `OAUTH_STATE_SECRET`, `SECRET_KEY`; add `SCHWAB_AUTH_URL` and `SCHWAB_TOKEN_URL` with correct Schwab URLs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Teardown)**: No dependencies — start immediately; T002–T008 all parallel
- **Phase 2 (Foundational)**: Must follow Phase 1 — T009 → T010 → T011 → T012 sequential
- **Phase 3 (US1 OAuth)**: Must follow Phase 2; T015 (`auth.js`) is prerequisite for all other JS modules
- **Phase 4 (US2 Positions)**: Must follow Phase 3 (needs `auth.js`); T021 and T022 are prerequisite for Phase 6
- **Phase 5 (US4 Erase All)**: Must follow Phase 3; can run parallel with Phase 4
- **Phase 6 (US3 Thesis)**: Must follow Phase 4 (needs `position_cache.js` and `positions_ui.js`)
- **Phase 7 (US5 Screener)**: Must follow Phase 3; parallel with Phases 4–6
- **Phase 8 (US6 Docker)**: Must follow Phase 4 (needs working app to containerise)
- **Phase 9 (Polish)**: Follows all user story phases

### Parallel Opportunities

```text
Phase 1: T002–T008 all in parallel
Phase 2: sequential (T009 → T010 → T011 → T012)
After Phase 3: Phase 4 (positions), Phase 5 (erase all), Phase 7 (screener) in parallel
Phase 9: T041, T042 in parallel
```

---

## Implementation Strategy

### MVP (US1 + US2 = working dashboard)

1. Complete Phase 1 (Teardown)
2. Complete Phase 2 (Foundational)
3. Complete Phase 3 (US1 — OAuth login)
4. Complete Phase 4 (US2 — Positions refresh)
5. **STOP and VALIDATE**: Login → Refresh → positions visible → Logout
6. App is deployable and useful at this point

### Incremental Delivery

- Phase 5 (US3 — Thesis localStorage): adds grouping without server changes
- Phase 6 (US4 — Screener): adds screener in parallel or after US3
- Phase 7 (US5 — Dockerfile): wraps everything for Cloud Run
- Phase 8: clean up tests and docs

### Total Tasks

| Phase | Tasks | Parallel? |
|---|---|---|
| Phase 1 (Teardown) | 8 | 7 in parallel |
| Phase 2 (Foundational) | 4 | Sequential |
| Phase 3 (US1 OAuth + token) | 5 | Mostly sequential |
| Phase 4 (US2 Positions + cache) | 9 | Some parallel |
| Phase 5 (US4 Erase All) | 2 | Sequential |
| Phase 6 (US3 Thesis) | 3 | Sequential |
| Phase 7 (US5 Screener) | 5 | Some parallel |
| Phase 8 (US6 Docker) | 4 | Some parallel |
| Phase 9 (Polish + README) | 5 | 2 in parallel |
| **Total** | **45** | |
