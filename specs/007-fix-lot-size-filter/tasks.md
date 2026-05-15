# Tasks: Fix Covered Call Screener — 100-Share Lot Filter

**Input**: Design documents from `specs/007-fix-lot-size-filter/`
**Branch**: `007-fix-lot-size-filter`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: User Story 1 — Valid Lot Filter (the only story for this fix)

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

---

## Phase 3: Polish & Validation

- [x] T004 Run full regression suite `pytest tests/ -q` — confirm all existing tests still pass (no regressions)

---

## Dependencies & Execution Order

- T001 first (RED tests, no implementation)
- T002 and T003 can start after T001 confirms RED
  - T002 (models.py) and T003 (screener.py) touch different files → [P] in theory, but T003 depends on the `contracts` field from T002 — run T002 first, then T003
- T004 last (full regression)

---

## Implementation Strategy

### MVP (this entire fix is MVP)

1. T001: Write failing tests
2. T002: Add `contracts` field to model
3. T003: Add gate + set `contracts` in screener service
4. T004: Full regression — done

Total: 4 tasks, ~30 minutes, 3 files changed.
