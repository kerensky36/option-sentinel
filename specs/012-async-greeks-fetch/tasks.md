# Tasks: Parallel Greeks Fetch

**Input**: Design documents from `specs/012-async-greeks-fetch/`  
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ quickstart.md ✅

**Scope**: One function changed (`_fetch_greeks` in `src/services/schwab_client.py`), one new test file (`tests/unit/test_schwab_client.py`). No models, routes, frontend, or contract changes.

**Tests**: Required — Principle IV (Test-First) is NON-NEGOTIABLE per the project constitution.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no in-flight dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm the single affected file is understood before writing tests.

- [x] T001 Read `src/services/schwab_client.py` in full and confirm the current `_fetch_greeks` loop structure matches the plan description

**Checkpoint**: File structure confirmed — test writing can begin.

---

## Phase 2: Foundational — Failing Tests (BLOCKS all implementation)

**Purpose**: Write all unit tests and confirm they are RED before any implementation begins. This is required by Principle IV.

**⚠️ CRITICAL**: Every test below MUST fail before proceeding to Phase 3.

- [x] T002 Create `tests/unit/test_schwab_client.py` with async test infrastructure (pytest-asyncio or `asyncio.run`), mock Schwab client fixture that records `get_option_chain` call counts and can simulate responses or exceptions
- [x] T003 [US1] Write `test_fetch_greeks_issues_calls_concurrently`: mock `get_option_chain` on a client with 3 underlyings; assert all 3 calls were issued (call count == 3) and that the function returns a merged dict with all symbols present — this test is currently RED because the serial loop does not change call count but the concurrency assertion can be approximated by confirming all three results arrive
- [x] T004 [US2] Write `test_fetch_greeks_returns_correct_values`: build a mock returning known delta/gamma/theta/vega/IV for two underlyings; assert the returned dict contains all symbols with the exact expected values
- [x] T005 [US3] Write `test_fetch_greeks_one_failure_does_not_block_others`: mock one underlying to raise `Exception("network error")` and others to return valid data; assert the healthy underlyings' Greeks are present in the result and the failed one is absent (no data, no propagated exception)
- [x] T006 Write `test_fetch_greeks_empty_symbols_returns_empty_dict`: call `_fetch_greeks([], client)` and assert `{}` is returned with `get_option_chain` never called
- [x] T007 Run `pytest tests/unit/test_schwab_client.py -v` and confirm all new tests FAIL (or ERROR on import if the test infrastructure is not yet wired up); document the failure output as confirmation of RED state

**Checkpoint**: All tests confirmed RED — implementation may begin.

---

## Phase 3: User Story 1 & 2 — Parallel Greeks Implementation (Priority: P1) 🎯 MVP

**Goal**: `_fetch_greeks` fires all `get_option_chain` calls concurrently so N underlyings take ≈ 1 round-trip. Output is identical to the sequential version.

**Independent Test**: `pytest tests/unit/test_schwab_client.py -v` — T003 and T004 must turn GREEN.

- [x] T008 Add `import asyncio` at the top of `src/services/schwab_client.py` (module-level, below existing imports)
- [x] T009 Inside `_fetch_greeks`, extract the existing `try/except` loop body into a named inner coroutine `async def _fetch_one(underlying: str, sym_list: list[str]) -> dict[str, dict]` that returns a partial symbol→Greeks dict on success or `{}` on exception — keep the `except Exception: pass` pattern intact
- [x] T010 Replace the serial `for` loop with `results = await asyncio.gather(*[_fetch_one(u, s) for u, s in underlying_to_symbols.items()], return_exceptions=True)` in `src/services/schwab_client.py`
- [x] T011 Add result merge loop after the gather: `greeks_by_symbol: dict[str, dict] = {}` then `for r in results: if not isinstance(r, Exception): greeks_by_symbol.update(r)` in `src/services/schwab_client.py`
- [x] T012 Run `pytest tests/unit/test_schwab_client.py::test_fetch_greeks_issues_calls_concurrently tests/unit/test_schwab_client.py::test_fetch_greeks_returns_correct_values -v` and confirm GREEN

**Checkpoint**: US1 and US2 tests green — parallel fetch correct and complete.

---

## Phase 4: User Story 3 — Failure Isolation Confirmed (Priority: P2)

**Goal**: Confirm that a failed concurrent task does not blank out Greeks for healthy underlyings. The `return_exceptions=True` flag and the `isinstance(r, Exception)` filter implemented in Phase 3 should already satisfy this.

**Independent Test**: `pytest tests/unit/test_schwab_client.py::test_fetch_greeks_one_failure_does_not_block_others -v` — must turn GREEN.

- [x] T013 [US3] Run `pytest tests/unit/test_schwab_client.py::test_fetch_greeks_one_failure_does_not_block_others -v`; if RED, inspect the merge loop in `_fetch_greeks` and confirm `return_exceptions=True` is set and the `isinstance` filter correctly skips exceptions
- [x] T014 [US3] Run `pytest tests/unit/test_schwab_client.py::test_fetch_greeks_empty_symbols_returns_empty_dict -v` and confirm GREEN (early return for empty symbols is unchanged)

**Checkpoint**: All four new unit tests GREEN — all user stories satisfied.

---

## Phase 5: Polish & Full Validation

**Purpose**: Confirm no regressions across the full test suite and validate via quickstart protocol.

- [x] T015 Run `pytest tests/ -v` and confirm all pre-existing tests pass without modification
- [x] T016 [P] Run `pytest tests/contract/test_positions_api.py -v` and confirm contract tests pass (response schema unchanged)
- [ ] T017 [P] Perform quickstart Scenario 1 (correctness diff) from `specs/012-async-greeks-fetch/quickstart.md` — call the positions endpoint before and after, diff the JSON output, confirm no change
- [ ] T018 Perform quickstart Scenario 2 (timing) from `specs/012-async-greeks-fetch/quickstart.md` — time the positions endpoint with a multi-underlying portfolio and confirm measurable improvement over the sequential baseline

**Checkpoint**: All tests green, correctness confirmed, performance improvement measured — ready to merge.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Tests)**: Depends on Phase 1 — BLOCKS Phases 3, 4, 5
- **Phase 3 (Implementation)**: Depends on Phase 2 RED confirmation
- **Phase 4 (Isolation)**: Depends on Phase 3 completion (the fix is already in place)
- **Phase 5 (Validation)**: Depends on Phases 3 and 4 green

### Within Phase 2

- T002 (test file creation) must complete before T003–T006
- T003–T006 can be written in parallel (all in the same file, different functions — write sequentially to avoid conflict)
- T007 (confirm RED) is the gate to Phase 3

### Within Phase 3

- T008 → T009 → T010 → T011 → T012 (sequential, all editing the same function)

### Parallel Opportunities

- T015, T016, T017 in Phase 5 can run in parallel

---

## Parallel Example: Phase 5 Validation

```
Task: pytest tests/ -v                                    (T015)
Task: pytest tests/contract/test_positions_api.py -v     (T016, parallel with T015)
Task: quickstart Scenario 1 — correctness diff            (T017, parallel with T015/T016)
```

---

## Implementation Strategy

### MVP (minimum to ship)

1. Phase 1: Read the file
2. Phase 2: Write + confirm RED tests
3. Phase 3: Implement gather
4. Phase 4: Confirm isolation test green
5. Phase 5: Full suite + quickstart
6. Done — single-file change, no migrations, no deploys needed

### Incremental Check

After T012: run the full suite immediately. If any pre-existing test breaks, the issue is in T008–T011 before touching anything else.

---

## Notes

- All tasks in `src/services/schwab_client.py` are sequential (same function)
- `tests/unit/test_schwab_client.py` is a new file — no merge conflicts
- No database, no migrations, no frontend — validation is purely test-driven
- Quickstart Scenario 2 (timing) requires a live Schwab token; all other scenarios can run against mocks
