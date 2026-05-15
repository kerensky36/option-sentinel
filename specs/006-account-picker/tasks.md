# Tasks: Account Picker Dropdown + Security Hardening (Constitution v3.1.0)

**Input**: Design documents from `specs/006-account-picker/`
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/http.md ✅

**Organization**: Tasks are grouped by user story. US1–US3 = account picker (complete). US4 = security hardening (Constitution v3.1.0 compliance, pending).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)

---

## Phase 2: Foundational (Failing Tests First)

**Purpose**: Write RED tests per Constitution Principle IV before any implementation begins.

**⚠️ CRITICAL**: Tests MUST be written and confirmed failing before Phase 3 begins.

- [x] T001 Write failing contract tests for `GET /api/accounts` in `tests/contract/test_accounts_api.py` — assert 200 with `[{accountNumber, hashValue}]`, 401 on missing token, 422 on invalid hash passed to screener/positions
- [x] T002 [P] Write failing unit tests for account_hash resolution logic in `tests/unit/test_account_hash.py` — assert first-account fallback when no hash provided, 422 when provided hash not in list, stale stored hash → fallback behaviour

**Checkpoint**: Run `pytest tests/contract/test_accounts_api.py tests/unit/test_account_hash.py` — ALL tests must FAIL before proceeding.

---

## Phase 3: User Story 1 — Select Active Account After Login (Priority: P1) 🎯 MVP

**Goal**: A user with multiple accounts sees the account picker in the top nav. Selecting an account causes subsequent API calls to use that account's hash.

**Independent Test**: Log in with a two-account token, see both accounts in the picker as `...NNNN`, select the second, click Refresh on the screener — confirm the screener data reflects the second account. Run `pytest tests/contract/test_accounts_api.py` — all pass.

### Implementation for User Story 1

- [x] T003 [US1] Implement `GET /api/accounts` endpoint in `src/api/routes/accounts.py` — call `list_accounts(client)`, mask each `accountNumber` to `"..." + last4`, handle disambiguation if last-4 are non-unique, return `[{accountNumber, hashValue}]`; return 502 on Schwab API failure; do NOT log hashValue values
- [x] T004 [US1] Register accounts router in `src/api/main.py` — import and `app.include_router(accounts.router)` alongside existing routers
- [x] T005 [P] [US1] Add optional `account_hash: str | None = None` query param to `GET /api/positions/refresh` in `src/api/routes/positions.py` — pass it through to `fetch_positions_and_greeks()`; return 422 with `"Account hash not found on this token"` if provided hash is absent from account list
- [x] T006 [P] [US1] Add optional `account_hash: str | None = None` query param to `GET /api/screener/refresh` in `src/api/routes/screener.py` — pass it through to `run_screener()`; return 422 with `"Account hash not found on this token"` if provided hash is absent from account list
- [x] T007 [US1] Update `_fetch_positions(client, account_hash=None)` in `src/services/schwab_client.py` — if `account_hash` is provided, use it directly as `account_hash`; if absent, use `accounts[0]["hashValue"]`; if provided hash not in account list, raise `ValueError` (callers map to 422)
- [x] T008 [US1] Update `run_screener(schwab_client, account_hash=None)` in `src/services/covered_call_screener.py` — accept `account_hash` and thread it through to any call that uses account-specific Schwab API calls; update `fetch_positions_and_greeks` signature to accept `account_hash` in `src/services/schwab_client.py`
- [x] T009 [US1] Create `frontend/static/js/account_picker.js` — export `getSelectedAccountHash(): string|null` and `withAccountHash(url: string): string`; on init, call `GET /api/accounts` via `fetchWithAuth`, populate `<select id="account-picker">` with `<option value="{hashValue}">{accountNumber}</option>`, wire `change` event to update a module-level variable
- [x] T010 [US1] Add `<select id="account-picker">` element to the top nav in `frontend/templates/base.html` — place between logo and action buttons; import `account_picker.js` as a module script at the bottom of the page (alongside the existing erase-all handler)
- [x] T011 [P] [US1] Update `screener_ui.js` to call `withAccountHash('/api/screener/refresh')` instead of the bare URL in the `refreshScreener` function in `frontend/static/js/screener_ui.js`
- [x] T012 [P] [US1] Update `positions_ui.js` to call `withAccountHash('/api/positions/refresh')` instead of the bare URL in the `refreshPositions` / fetch call in `frontend/static/js/positions_ui.js`

**Checkpoint**: Account picker visible in nav, lists all accounts, selecting one causes screener/positions API calls to use the correct account hash. `pytest tests/contract/test_accounts_api.py` — all pass.

---

## Phase 4: User Story 2 — Account Selection Persists During Session (Priority: P2)

**Goal**: The selected account survives page navigation and browser refresh within the same tab. "Erase All" clears the selection.

**Independent Test**: Select account `...5678` on the screener page, navigate to positions — picker still shows `...5678`. Refresh the page — `...5678` still selected. Click "Erase All" — `sessionStorage` is empty.

### Implementation for User Story 2

- [x] T013 [US2] Add `sessionStorage` persistence to `frontend/static/js/account_picker.js` — on `change` event, write selected `hashValue` to `sessionStorage` under key `schwab_selected_account`; on init after fetching account list, read `sessionStorage` and pre-select the stored hash in the `<select>` if it exists in the returned list
- [x] T014 [US2] Add stale-hash guard to `frontend/static/js/account_picker.js` — after fetching account list on init, if the stored `schwab_selected_account` hash is NOT in the returned list, discard it and select `accounts[0]` (write the corrected value back to `sessionStorage`)
- [x] T015 [US2] Confirm `eraseAll()` clears account selection by adding an assertion to `tests/unit/test_account_hash.py` (or a new test file) — verify that `sessionStorage.clear()` removes `schwab_selected_account`; note this is already covered by `auth.js` calling `sessionStorage.clear()` — document and confirm, do not add redundant code

**Checkpoint**: Page refresh restores picker selection. Navigate between screener and positions — selection preserved. Erase All → selection gone. `pytest tests/unit/test_account_hash.py` — all pass.

---

## Phase 5: User Story 3 — Single-Account Users See No Friction (Priority: P3)

**Goal**: A user with exactly one account requires zero extra interactions — data loads automatically.

**Independent Test**: Log in with a single-account token, navigate to screener — data loads without any account picker interaction. Picker is pre-selected and non-interactive (disabled or hidden).

### Implementation for User Story 3

- [x] T016 [US3] Implement auto-select in `frontend/static/js/account_picker.js` — after fetching accounts, if `accounts.length === 1`, set `getSelectedAccountHash()` to that account's hash and write to `sessionStorage` without requiring user interaction
- [x] T017 [US3] Render picker as non-interactive for single-account users in `frontend/static/js/account_picker.js` and `frontend/templates/base.html` — when only one account is present, add `disabled` attribute to `<select>` and apply a visual style (e.g., reduced opacity) so the user sees the account but cannot interact with it

**Checkpoint**: Single-account user loads screener — data fetches immediately, picker shows account as non-interactive. No regression for multi-account users.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, visual polish, mobile rendering, end-to-end validation.

- [x] T018 Implement error state in `frontend/static/js/account_picker.js` — if `GET /api/accounts` fails (network error, non-200, 401), set `<select>` to a single disabled option with text `"Error loading accounts"` and do NOT auto-trigger any data refresh; let existing 401 handling in `fetchWithAuth` redirect to login on 401
- [x] T019 [P] Style `<select id="account-picker">` in `frontend/templates/base.html` to match TOS dark theme — dark background (`#1c1c24`), gray text, no rounded corners, font-size 10–11px, consistent with other nav controls
- [ ] T020 Validate mobile viewport rendering per Constitution Principle VI — open the app on a mobile viewport (or DevTools responsive mode), confirm picker is visible and usable in the top nav; adjust layout if picker overflows or wraps unexpectedly
- [ ] T021 Run all quickstart.md test scenarios end-to-end — single-account flow, multi-account selection, page refresh persistence, Erase All, and network-error simulation; AND security header verification curl commands from the Security Controls section
- [x] T022 [P] Update `specs/006-account-picker/checklists/requirements.md` — mark all items complete and record any deviations from spec

---

## Phase 7: Security Hardening — RED Tests First (Constitution Principle IV)

**Purpose**: Write failing tests for all Constitution v3.1.0 security controls. ALL tests MUST be confirmed failing before Phase 8 implementation begins.

**⚠️ CRITICAL**: Constitution Principle IV — security controls MUST have failing tests before implementation.

- [x] T023 Write failing contract tests for security response headers in `tests/contract/test_security_headers.py` — use FastAPI `TestClient`; assert: (a) any HTML response has `Content-Security-Policy` header containing `nonce-`; (b) two requests produce different nonce values; (c) all responses have `X-Frame-Options: DENY`; (d) all responses have `X-Content-Type-Options: nosniff`; (e) all responses have `Referrer-Policy: strict-origin-when-cross-origin`; (f) `/api/*` responses have `Cache-Control: no-store`; (g) foreign-origin requests to `/api/*` get no `Access-Control-Allow-Origin` header; (h) 429 returned after rate limit exceeded
- [x] T024 [P] Write failing unit tests for security middleware in `tests/unit/test_security_middleware.py` — assert: (a) `CSPNonceMiddleware` sets a different nonce on each request; (b) nonce matches URL-safe base64 pattern `[A-Za-z0-9_-]{22}`; (c) `SecurityHeadersMiddleware` adds no HSTS header when `HTTPS_ONLY` env var is absent or `false`; (d) generic error handler returns `{"detail":"Internal server error"}` with status 500 and no stack trace when `DEBUG=false`; (e) generic error handler does NOT mask errors when `DEBUG=true`

**Checkpoint**: Run `pytest tests/contract/test_security_headers.py tests/unit/test_security_middleware.py` — ALL tests must FAIL before Phase 8 begins.

---

## Phase 8: User Story 4 — Security-First Controls (Constitution v3.1.0)

**Goal**: All mandatory security controls from Constitution Principle II are implemented and verified. The app is safe to deploy to production.

**Independent Test**: Start the dev server and run the curl security verification commands from `specs/006-account-picker/quickstart.md` — CSP nonce changes per request, X-Frame-Options: DENY, CORS rejects foreign origin, Cache-Control: no-store on API routes. `pytest tests/contract/test_security_headers.py tests/unit/test_security_middleware.py` — all pass.

### Implementation for User Story 4

- [x] T025 [US4] Pin all dependencies in `requirements.txt` to exact versions — change every `>=` range to `==` with the latest stable version currently installed; add `slowapi` and `limits` with exact pinned versions; run `pip install -r requirements.txt` to verify; run `pip freeze` to confirm versions match
- [x] T026 [P] [US4] Add `CORSMiddleware` in `create_app()` in `src/api/main.py` — `from fastapi.middleware.cors import CORSMiddleware`; `allow_origins=[os.getenv("ALLOWED_ORIGIN","http://localhost:8000")]`; `allow_methods=["GET","POST","OPTIONS"]`; `allow_headers=["Authorization","Content-Type"]`; `allow_credentials=False`; wildcard `*` is FORBIDDEN
- [x] T027 [P] [US4] Implement `CSPNonceMiddleware(BaseHTTPMiddleware)` class in `src/api/main.py` — on each request: generate `secrets.token_urlsafe(16)` nonce, assign to `request.state.csp_nonce`; after `call_next`, set `Content-Security-Policy` response header: `default-src 'self'; script-src 'self' https://cdn.tailwindcss.com 'nonce-{nonce}'; style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`; import `secrets` at top of file
- [x] T028 [P] [US4] Implement `SecurityHeadersMiddleware(BaseHTTPMiddleware)` class in `src/api/main.py` — on each response: always set `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`; if `os.getenv("HTTPS_ONLY","false").lower()=="true"`, add `Strict-Transport-Security: max-age=31536000; includeSubDomains`; if `request.url.path.startswith("/api/")`, add `Cache-Control: no-store`
- [x] T029 [US4] Register all new middleware in `create_app()` in `src/api/main.py` — add `app.add_middleware(CORSMiddleware, ...)`, `app.add_middleware(CSPNonceMiddleware)`, `app.add_middleware(SecurityHeadersMiddleware)` after existing `NoCacheJSMiddleware`; add slowapi `Limiter(key_func=get_remote_address)` assigned to `app.state.limiter`; add `SlowAPIMiddleware`; add `@app.exception_handler(RateLimitExceeded)` returning `JSONResponse({"detail":"Rate limit exceeded"}, status_code=429)` with `Retry-After` header
- [x] T030 [US4] Apply rate limiting decorators to route handlers — in `src/api/routes/accounts.py`, `src/api/routes/positions.py`, `src/api/routes/screener.py`: add `@limiter.limit("60/minute")` to each endpoint (import `limiter` from `src.api.main`); in `src/auth/router.py`: add `@limiter.limit("10/minute")` to the `/auth/start` and `/auth/callback` handlers; add `request: Request` param to any handler that doesn't already have it (slowapi requires it)
- [x] T031 [US4] Add security event audit logging in `src/api/main.py` and `src/auth/router.py` — add at top of `src/api/main.py`: `import logging, hmac, hashlib; _security_log = logging.getLogger("security"); _log_pepper = os.getenv("LOG_PEPPER","sentinel-pepper")`; add helper `def _hash_ip(ip: str) -> str: return hmac.new(_log_pepper.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]`; log 401 events with format `SECURITY 401 invalid_token path={path} ip={hashed_ip}`; log 422 events `SECURITY 422 invalid_account_hash path={path} ip={hashed_ip}`; in `src/auth/router.py` log OAuth state mismatch as `SECURITY oauth_state_mismatch` and state expiry as `SECURITY oauth_state_expired`; NEVER include token values, hashValue, or raw IP in any log line
- [x] T032 [US4] Add generic production error handler in `src/api/main.py` — define `async def _generic_error_handler(request, exc): return JSONResponse({"detail":"Internal server error"}, status_code=500)`; after all routers are registered in `create_app()`, add: `if os.getenv("DEBUG","true").lower() != "true": app.add_exception_handler(Exception, _generic_error_handler)` — dev mode keeps FastAPI's default error output
- [x] T033 [US4] Pass CSP nonce into all Jinja2 `TemplateResponse` calls — search `src/api/routes/dashboard.py`, `src/api/routes/partials.py`, `src/auth/router.py` for every `TemplateResponse(...)` call; add `"csp_nonce": getattr(request.state, "csp_nonce", "")` to the context dict of each; the `request` parameter must already be present (it is in all existing handlers)
- [x] T034 [US4] Apply nonce attribute to inline scripts in `frontend/templates/base.html` — find every `<script>` block that does NOT have `src=` (inline scripts); add `nonce="{{ csp_nonce }}"` attribute to each opening `<script>` tag; two inline blocks are expected: (1) Tailwind CDN config, (2) Erase All event listener; verify no other inline scripts exist in the template or in `frontend/templates/login.html`
- [x] T035 [P] [US4] Create `scripts/audit.sh` — write the file with content: `#!/bin/bash\nset -e\npip-audit --require-hashes -r requirements.txt`; make it executable: `chmod +x scripts/audit.sh`

**Checkpoint**: `pytest tests/contract/test_security_headers.py tests/unit/test_security_middleware.py` — all pass. Curl security verification from quickstart.md succeeds. `bash scripts/audit.sh` exits 0.

---

## Phase 9: Security Validation & Full Suite

**Purpose**: End-to-end security verification and full regression check.

- [x] T036 Run `bash scripts/audit.sh` — if known CVEs are found, update affected packages to patched exact versions in `requirements.txt` and re-run; document any accepted exceptions with justification in `specs/006-account-picker/plan.md` Complexity Tracking table
- [x] T037 [P] Run full test suite `pytest tests/ -v` — confirm all account picker tests (T001–T022 scope) still pass; confirm all security header tests pass; fix any regressions before marking done
- [x] T038 Run security header curl verification per `specs/006-account-picker/quickstart.md` Security Controls section — verify: CSP nonce present and changes between requests, X-Frame-Options: DENY, CORS rejects `https://evil.example.com`, Cache-Control: no-store on `/api/screener/refresh`; document results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: Complete ✅
- **US1 (Phase 3)**: Complete ✅
- **US2 (Phase 4)**: Complete ✅
- **US3 (Phase 5)**: Complete ✅
- **Polish (Phase 6)**: T018, T019, T022 complete ✅; T020, T021 pending (can run after Phase 8)
- **Security RED tests (Phase 7)**: Start immediately — write failing tests first (T023, T024)
- **US4 (Phase 8)**: Depends on Phase 7 RED tests confirmed failing; T025 (deps) must complete before T029 (registers rate limiter); T026–T028 parallel; T029 after T026–T028; T030 after T029; T031–T032 parallel after T029; T033 → T034 sequential (context before templates)
- **Security Validation (Phase 9)**: Depends on Phase 8 completion

### Within Phase 8

```
T025 (pin deps) must complete before T029 (rate limiter registration needs slowapi installed)
T026 ‖ T027 ‖ T028  (independent middleware classes)
T026 + T027 + T028 → T029  (register all middleware)
T029 → T030  (limiter on app.state before decorators)
T029 → T031 ‖ T032  (app must exist)
T033 → T034  (pass nonce in context before applying to templates)
T035  (independent — scripts/)
```

### Parallel Opportunities

```
Phase 7:    T023 ‖ T024
Phase 8:    T026 ‖ T027 ‖ T028  (middleware classes)
            T031 ‖ T032          (after T029)
            T035                 (independent)
Phase 9:    T036 ‖ T037 ‖ T038  (independent verification tasks)
```

---

## Implementation Strategy

### Security Hardening MVP (Phase 7 + Phase 8)

1. Phase 7: Write RED tests (T023, T024) — confirm failing
2. Phase 8: Implement controls (T025–T035) — sequential where required, parallel where possible
3. **Validate**: Security header tests pass; curl checks succeed; audit clean
4. Phase 9: Full suite regression (T036–T038)
5. Finish Polish (T020, T021)

### Incremental Delivery

1. Account picker (US1–US3) — COMPLETE ✅
2. Security hardening (US4) — Phase 7 RED → Phase 8 GREEN → Phase 9 validation
3. Polish — T020 (mobile) + T021 (end-to-end)

---

## Notes

- [P] tasks = different files, no incomplete dependencies between them
- Tests MUST be written RED before implementation (Constitution Principle IV — non-negotiable)
- `hashValue` and Bearer token values MUST NOT appear in any server log output
- The `<select>` element ID `account-picker` is the stable DOM contract between `base.html` and `account_picker.js`
- `eraseAll()` in `auth.js` calls `sessionStorage.clear()` — no additional code needed to clear account selection
- slowapi requires `request: Request` as a parameter on any endpoint that uses `@limiter.limit` — check all decorated handlers
- Middleware registration order matters: SecurityHeaders → CSPNonce → CORS (outermost evaluated last in Starlette)
- `DEBUG=true` is the default to preserve developer experience; production Cloud Run sets `DEBUG=false`
