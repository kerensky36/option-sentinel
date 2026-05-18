# Research: Parallel Greeks Fetch

**Feature**: 012-async-greeks-fetch  
**Date**: 2026-05-17

## Decision 1: asyncio.gather vs asyncio.TaskGroup

**Decision**: Use `asyncio.gather(*coros, return_exceptions=True)`

**Rationale**: `gather` with `return_exceptions=True` maps directly to the existing per-underlying `try/except` isolation pattern — a failed coroutine returns an exception object rather than propagating, so the caller can filter and still merge results from healthy underlyings. `TaskGroup` (Python 3.11+) cancels all sibling tasks on the first failure, which would break the isolation guarantee in FR-003.

**Alternatives considered**:
- `asyncio.TaskGroup`: Rejected — task group cancels siblings on first error; we need all-complete semantics with per-task failure isolation.
- Manual `asyncio.create_task` + `await`: More verbose, no benefit over `gather` for this use case.

## Decision 2: Inner helper function vs lambda

**Decision**: Extract per-underlying logic into a named inner `async def _fetch_one(underlying, sym_list)` inside `_fetch_greeks`.

**Rationale**: A named inner function keeps the `try/except` block intact and readable. It also makes the unit test mockable — the test can patch `_fetch_one` or the underlying `client.get_option_chain` directly. Lambdas cannot be `async`.

**Alternatives considered**:
- Inline coroutine expression via `asyncio.gather(*(async_work() for ...))` pattern: Not valid Python syntax for multi-statement coroutines.

## Decision 3: httpx AsyncClient concurrency safety

**Decision**: The schwab-py `AsyncClient` wraps `httpx.AsyncClient` (confirmed in `schwab/client/asynchronous.py` — `self.session.aclose()` is httpx's method; base.py docs reference httpx timeout API). httpx `AsyncClient` is explicitly designed for concurrent requests on a single instance and is safe to use with `asyncio.gather`.

**Rationale**: No connection-level conflict will occur when multiple `await session.get(...)` calls are issued concurrently on the same client. This is a documented design property of httpx.

**Alternatives considered**:
- Creating a separate client per underlying: Unnecessary overhead; one client handles concurrent requests correctly.

## Decision 4: Result merging strategy

**Decision**: Each `_fetch_one` returns a `dict[str, dict]` (symbol → Greeks). After `gather`, iterate results and call `merged.update(r)` for each non-exception result.

**Rationale**: Simple and correct. No symbol can appear in two underlyings' chains, so there is no key collision risk. Exception instances returned by `gather(return_exceptions=True)` are skipped via `isinstance(r, Exception)` check.

**Alternatives considered**:
- Returning `(underlying, dict)` tuples: Unnecessary — symbol keys are globally unique across underlyings.

## Decision 5: Import placement

**Decision**: Add `import asyncio` at the top of `src/services/schwab_client.py` (module level, not inside the function).

**Rationale**: `asyncio` is stdlib. Module-level import is the standard convention and avoids repeated import overhead per call.
