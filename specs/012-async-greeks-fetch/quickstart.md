# Quickstart: Parallel Greeks Fetch — Verification Protocol

**Feature**: 012-async-greeks-fetch  
**Date**: 2026-05-17

## Purpose

Confirms the parallel Greeks fetch is correct and measurably faster than the sequential baseline. Run these scenarios after implementation, before merging.

## Prerequisites

- Dev server running (`uvicorn src.api.main:app --reload`)
- Valid Schwab Bearer token in hand
- Portfolio with at least 2 distinct underlying symbols

---

## Scenario 1 — Correctness: response is unchanged

**Goal**: Verify no Greeks values changed.

1. With the **current branch** (before implementation), call the positions endpoint and save the response:
   ```
   curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/positions/refresh | jq . > /tmp/before.json
   ```
2. After implementation, call again with the same token:
   ```
   curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/positions/refresh | jq . > /tmp/after.json
   ```
3. Diff the two:
   ```
   diff /tmp/before.json /tmp/after.json
   ```

**Expected**: No diff (or only floating-point noise in the last decimal place of IV).

---

## Scenario 2 — Performance: parallel is faster for N ≥ 2 underlyings

**Goal**: Confirm wall-clock time is ≈ 1× single call, not N×.

1. Time the positions endpoint with a multi-underlying portfolio:
   ```
   time curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/positions/refresh > /dev/null
   ```
2. Note the real time. Compare to the sequential baseline (run the same command on `main`).

**Expected**: With 4 underlyings, the parallel version completes in roughly the same time as 1 underlying on the sequential version.

---

## Scenario 3 — Single underlying: no regression

**Goal**: Confirm behaviour with exactly 1 underlying is unchanged.

1. If you have a portfolio with only one underlying, run Scenario 1 and Scenario 2 against it.

**Expected**: Response identical, timing unchanged (gather with 1 coroutine = direct await).

---

## Scenario 4 — Unit test: concurrency confirmed

**Goal**: The unit test proves all calls were issued before any resolved.

```
pytest tests/unit/test_schwab_client.py -v -k "parallel"
```

**Expected**: All parallel-fetch tests pass (green).

---

## Scenario 5 — Unit test: failure isolation

**Goal**: One failing underlying does not blank out others.

```
pytest tests/unit/test_schwab_client.py -v -k "isolation"
```

**Expected**: Test confirms partial results returned when one underlying raises.

---

## Scenario 6 — Empty portfolio

**Goal**: Empty symbol list returns `{}` immediately with no gather call.

```
pytest tests/unit/test_schwab_client.py -v -k "empty"
```

**Expected**: Passes; `get_option_chain` is never called.

---

## Scenario 7 — Full test suite

```
pytest tests/ -v
```

**Expected**: All pre-existing tests pass without modification.

---

## Scenario 8 — Contract test

```
pytest tests/contract/test_positions_api.py -v
```

**Expected**: All contract tests pass; response schema is unchanged.
