# Tasks: Seamless, Stateful Demo ↔ Live Mode Switch

**Tests**: Required (Constitution IV); run and see them fail before implementing.

## Phase 1: US1 + US2 (P1)

### Tests (write first, confirm failing)

- [ ] T001 [US2] `tests/unit/mode_switch_harness.mjs` + `tests/unit/test_mode_switch.py`: `scopedKey` prefixes only in demo; caches written in demo are not read in live and vice versa (FR-406, SC-403); live key names unchanged (US2-3).
- [ ] T002 [US1] Same files: `switchMode('demo')` keeps the token and reloads; `switchMode('live')` with token clears the flag and reloads; without token assigns `/auth/start` (FR-402–404).
- [ ] T003 [US1] `tests/unit/test_demo_mode_login.py`: callback/dev-login clear `demo_mode`; demo-login does not remove the token (FR-405). Base template has the switch (FR-401).

### Implementation

- [ ] T004 [US1] `auth.js`: `scopedKey`, `hasLiveToken`, `switchMode`.
- [ ] T005 [US2] Scope keys in `account_picker.js`, `position_cache.js`, `screener_cache.js`, `quorum_cache.js`.
- [ ] T006 [US1] `src/auth/router.py`: clear demo flag on token store.
- [ ] T007 [US1] `base.html`: DEMO | LIVE switch; fix Disconnect button markup.
- [ ] T008 `data_use.html`: demo state row (FR-409).

## Phase 2: Polish

- [ ] T009 Full `pytest -q`, `node --check` on changed JS, headless Chromium walk-through of live → demo → live.
