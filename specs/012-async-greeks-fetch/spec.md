# Feature Specification: Parallel Greeks Fetch

**Feature Branch**: `012-async-greeks-fetch`  
**Created**: 2026-05-17  
**Status**: Draft  
**Input**: User description: "Parallelize the get_option_chain API calls in _fetch_greeks using asyncio.gather. Currently each unique underlying triggers a sequential await, so N underlyings = N serial round-trips to Schwab. After the change all option chain fetches fire concurrently and results are merged. No other changes — no caching, no new endpoints, no UI changes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Faster Position Load with Multiple Underlyings (Priority: P1)

A trader holding positions across several underlyings (e.g. QQQ, SPY, TSLA, NVDA) refreshes the positions dashboard. Today all Greeks data is fetched serially — each underlying blocks the next. After this change, all fetches fire at the same time and the page loads faster.

**Why this priority**: This is the sole purpose of the feature. Every other story is a correctness or resilience guarantee that supports it.

**Independent Test**: Load positions with 3+ unique underlyings and measure wall-clock time before and after. The refresh must complete faster with no change to the data returned.

**Acceptance Scenarios**:

1. **Given** a portfolio with N ≥ 2 unique underlyings, **When** the positions endpoint is called, **Then** the Greeks fetch completes in approximately the time of a single Schwab option chain request (not N × that time).
2. **Given** a portfolio with 1 unique underlying, **When** the positions endpoint is called, **Then** behaviour and response time are unchanged from the current implementation.

---

### User Story 2 - Correctness: Greeks Data Is Identical (Priority: P1)

A trader expects the same delta, gamma, theta, vega, and IV values after the change as before. Parallelising the fetch must not alter which options are matched or which values are returned.

**Why this priority**: A performance gain that silently changes Greeks values is a regression. Correctness is non-negotiable.

**Independent Test**: Compare the full JSON response for the same portfolio before and after the change. All numeric fields must match within floating-point precision.

**Acceptance Scenarios**:

1. **Given** a known portfolio, **When** the positions endpoint is called after the change, **Then** each position's Greeks match the values returned by the current sequential implementation for the same market snapshot.
2. **Given** a symbol that appears in both `callExpDateMap` and `putExpDateMap`, **When** Greeks are merged, **Then** the correct leg is returned with no cross-contamination between underlyings.

---

### User Story 3 - Resilience: One Failing Chain Does Not Block Others (Priority: P2)

Today if one `get_option_chain` call throws, the entire `_fetch_greeks` function may silently swallow it and return empty Greeks for that underlying (the `except Exception: pass` branch). After the change, a failure for one underlying must not prevent Greeks from being populated for the others.

**Why this priority**: The current `except Exception: pass` pattern already handles this per-underlying. The parallel version must preserve that isolation — a broken concurrent task must not propagate and blank out the whole result.

**Independent Test**: Mock one underlying's option chain call to raise an exception. Verify the other underlyings' Greeks are still returned correctly and the failed one returns empty Greeks (falling back to Black-Scholes).

**Acceptance Scenarios**:

1. **Given** N underlyings where one raises a network error, **When** the positions endpoint is called, **Then** the N-1 healthy underlyings have Greeks populated and the failed one falls back to Black-Scholes (or returns None values), with no error surfaced to the caller.
2. **Given** all underlyings succeed, **When** results are merged, **Then** no data from one underlying is attributed to another.

---

### Edge Cases

- What happens when `symbols` is empty? The function returns `{}` immediately — this must be unchanged.
- What happens with a single underlying? `asyncio.gather` with one coroutine must behave identically to a single `await`.
- What happens if all concurrent fetches fail? `_fetch_greeks` returns `{}` and all positions fall back to Black-Scholes, consistent with current behaviour.
- What happens with duplicate underlyings mapped from different OCC symbols? They must be grouped and deduplicated the same way as today before any fetch is issued.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST fire all `get_option_chain` requests for distinct underlyings concurrently rather than sequentially.
- **FR-002**: Results from all concurrent fetches MUST be merged into a single symbol-keyed Greeks dictionary before being returned to the caller.
- **FR-003**: A failure fetching the option chain for one underlying MUST NOT prevent Greeks from being returned for any other underlying.
- **FR-004**: The Greeks values and structure returned by `_fetch_greeks` MUST be byte-for-byte identical to the current implementation for any given market snapshot.
- **FR-005**: The public signature and return type of `_fetch_greeks` and `fetch_positions_and_greeks` MUST remain unchanged.
- **FR-006**: No new endpoints, UI changes, caching layers, or data models are introduced by this change.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A portfolio with 4 unique underlyings loads Greeks in no more than 1.5× the time of a single option chain round-trip (down from 4×).
- **SC-002**: The JSON response for any given portfolio is identical before and after the change — all Greeks values, sources, and field presence match.
- **SC-003**: A simulated failure on one underlying's chain fetch has zero effect on the Greeks returned for all other underlyings.
- **SC-004**: All existing unit and contract tests pass without modification.

## Assumptions

- The Schwab async client supports issuing multiple concurrent `get_option_chain` requests on the same client instance without connection-level conflicts.
- Schwab's API rate limits are not a concern for the number of underlyings in a typical portfolio (generally under 10 distinct underlyings).
- The existing `except Exception: pass` error-isolation pattern per underlying is intentional and must be preserved in the parallel implementation.
- No change to how Black-Scholes fallback is triggered — it remains driven by missing API values, not by fetch strategy.
