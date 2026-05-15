# Tasks: Account Picker Dropdown

**Input**: Design documents from `specs/006-account-picker/`
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/http.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 2: Foundational (Failing Tests First)

**Purpose**: Write RED tests per Constitution Principle III before any implementation begins.

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
- [ ] T020 Validate mobile viewport rendering per Constitution Principle V — open the app on a mobile viewport (or DevTools responsive mode), confirm picker is visible and usable in the top nav; adjust layout if picker overflows or wraps unexpectedly
- [ ] T021 Run all quickstart.md test scenarios end-to-end — single-account flow, multi-account selection, page refresh persistence, Erase All, and network-error simulation
- [x] T022 [P] Update `specs/006-account-picker/checklists/requirements.md` — mark all items complete and record any deviations from spec

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: Start immediately — write failing tests first
- **US1 (Phase 3)**: Depends on Phase 2 RED tests being written — all Phase 3 tasks can start once T001/T002 exist
- **US2 (Phase 4)**: Depends on Phase 3 completion (needs picker to exist)
- **US3 (Phase 5)**: Depends on Phase 3 completion (needs picker to exist); can run in parallel with Phase 4
- **Polish (Phase 6)**: Depends on Phases 3–5

### Within Phase 3

- T003 (accounts route) → T004 (register router) → confirms T001 tests pass
- T005, T006 are parallel (different route files)
- T007 (schwab_client) → T008 (covered_call_screener) — service layer must be updated before routes can use it
- T009 (account_picker.js) → T010 (base.html) — JS module before template wires it up
- T011, T012 are parallel (different JS files) — both depend on T009 exporting `withAccountHash`

### Parallel Opportunities

```
Phase 2:    T001 ‖ T002
Phase 3:    T005 ‖ T006  (route files)
            T007 → T008  (sequential — service layer)
            T009 → T010  (sequential — module then template)
            T011 ‖ T012  (after T009)
Phase 5:    T016 → T017  (sequential)
Phase 6:    T019 ‖ T022  (parallel polish tasks)
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Phase 2: Write RED tests (T001, T002)
2. Phase 3: Implement backend + frontend (T003–T012)
3. **Validate**: Picker visible, multi-account works, contract tests pass
4. Ship MVP — account picker functional

### Incremental Delivery

1. MVP (US1) → account picker works, data goes to correct account
2. US2 → selection survives navigation and refresh
3. US3 → single-account users unaffected
4. Polish → error states, mobile, end-to-end validation

---

## Notes

- [P] tasks = different files, no incomplete dependencies between them
- Tests MUST be written RED before implementation (Constitution Principle III — non-negotiable)
- `eraseAll()` in `auth.js` calls `sessionStorage.clear()` — no code change needed for US2's "Erase All" requirement; the test in T015 confirms this by documentation
- `hashValue` values MUST NOT appear in any server log output
- The `<select>` element ID `account-picker` is the stable DOM contract between `base.html` and `account_picker.js`
