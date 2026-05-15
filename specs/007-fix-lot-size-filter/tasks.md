# Tasks: Fix Covered Call Screener — 100-Share Lot Filter

**Input**: Design documents from `specs/007-fix-lot-size-filter/`
**Branch**: `007-fix-lot-size-filter`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: User Story 1 — Valid Lot Filter (P1)
- **[US2]**: User Story 2 — Screener Result Cache (P2)

---

## Phase 1: Foundational

**Purpose**: No project initialization needed — existing FastAPI project. The only
foundational step is writing the RED unit tests (Constitution Principle IV: Test-First).

**⚠️ CRITICAL**: Write tests first. Confirm they FAIL before touching implementation files.

- [x] T001 [US1] Write RED unit tests for lot-size filter in tests/unit/test_covered_call_screener.py — cover: 100-share eligible (1 contract), 200-share eligible (2 contracts), 50-share filtered out, 150-share filtered out, 300-share eligible (3 contracts), 0-share filtered out, and negative-share filtered out. Use `unittest.mock.AsyncMock` to mock `_fetch_stock_positions`, `_fetch_open_calls`, and `_fetch_call_chain` so tests run without a real Schwab client. Confirm all tests FAIL (NameError or AssertionError) before proceeding.

---

## Phase 2: User Story 1 — Valid Lot Filter (Priority: P1) 🎯

**Goal**: Filter the screener to only show positions where shares is a positive multiple
of 100; expose `contracts = shares // 100` on each result.

**Independent Test**: `pytest tests/unit/test_covered_call_screener.py -v` — all tests pass.

- [x] T002 [P] [US1] Add `contracts: int = 0` field to `ScreenerResultView` in src/data/models.py after the `shares` field
- [x] T003 [US1] Add lot-size gate and `contracts` assignment in `run_screener()` in src/services/covered_call_screener.py — at the top of the `for pos in stock_positions:` loop, add `if shares <= 0 or shares % 100 != 0: continue`; set `contracts=shares // 100` on every `ScreenerResultView(...)` construction inside the loop (there are three: call_written/suppressed, no_liquid_options/insufficient_data, and the main recommended path)

**Checkpoint**: `pytest tests/unit/test_covered_call_screener.py -v` must show all GREEN.

- [x] T004 [US1] Run full regression suite `pytest tests/ -q` — confirm all existing tests still pass (no regressions)

---

## Phase 3: User Story 2 — Screener Result Cache (Priority: P2)

**Goal**: Cache screener results in sessionStorage so that navigating back to the screener
page within the same tab renders immediately from cache (no Schwab API call). Cache is
invalidated on explicit Refresh, erase-all, and logout (all handled by `eraseAll()`).

**Independent Test**: Manual — see quickstart.md "Verify screener result caching" section.

- [x] T005 [P] [US2] Add fractional-shares-floor unit test to tests/unit/test_covered_call_screener.py — test name `test_fractional_shares_floor`: mock position with `longQuantity=100.5`, confirm screener returns 1 result with `contracts=1`; mock position with `longQuantity=150.9`, confirm screener returns empty list. Run `pytest tests/unit/test_covered_call_screener.py -v` — new test must FAIL first, then pass after confirming existing `int()` cast in `_fetch_stock_positions` already satisfies it.
- [x] T006 [P] [US2] Create frontend/static/js/screener_cache.js — implement three synchronous sessionStorage wrapper functions: `saveScreenerResults(results)` stores `JSON.stringify(results)` under key `screener_results`; `loadScreenerResults()` returns parsed array or `null` on absence/parse error; `clearScreenerResults()` removes the key. Export all three. No dependencies. (~35 LOC)
- [x] T007 [US2] Update frontend/static/js/screener_ui.js to use the cache — add `import { saveScreenerResults, loadScreenerResults } from './screener_cache.js';` at the top; in `init()`, call `loadScreenerResults()` before fetching: if non-null call `renderScreener(cached)` and return without fetching; in `refreshScreener()`, after `const results = await resp.json()` and before `renderScreener(results)`, call `saveScreenerResults(results)`. No other changes — Refresh button already calls `refreshScreener()` which overwrites the cache; `eraseAll()` already calls `sessionStorage.clear()`.

**Checkpoint**: Manual browser verification per quickstart.md — cold load fetches from Schwab, warm load skips network, Refresh re-fetches, logout clears cache.

---

## Phase 4: Polish & Validation

- [x] T008 Run full regression suite `pytest tests/ -q` — confirm all tests still pass after fractional-shares test addition

---

## Dependencies & Execution Order

- T001–T004 complete (done)
- T005 and T006 are independent (different files) → can run in parallel
- T007 depends on T006 (imports screener_cache.js)
- T008 last (full regression after T005)

## Parallel Execution Examples

**Round 1** (independent): T005 + T006

**Round 2** (depends on T006): T007

**Round 3**: T008

---

## Implementation Strategy

### Completed (US1 — Lot Filter)

1. ~~T001: Write failing tests~~
2. ~~T002: Add `contracts` field to model~~
3. ~~T003: Add gate + set `contracts` in screener service~~
4. ~~T004: Full regression — done~~

### Remaining (US2 — Screener Cache)

5. T005: Fractional-shares floor edge-case test
6. T006: Create `screener_cache.js` (~35 LOC)
7. T007: Wire cache into `screener_ui.js`
8. T008: Full regression

Total remaining: 4 tasks, ~45 minutes, 3 files changed.
