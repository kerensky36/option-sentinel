# Research: Fix Covered Call Screener — 100-Share Lot Filter

## Decision 1: Where to apply the lot-size gate

**Decision**: Filter in `run_screener()` in `src/services/covered_call_screener.py`,
immediately after `_fetch_stock_positions()` returns, before any option chain fetches.

**Rationale**: Filtering before option chain fetches avoids wasted Schwab API calls for
ineligible positions. The fix is a single `continue` guard (`shares <= 0 or shares % 100 != 0`)
at the top of the position loop. This is the least invasive change.

**Alternatives considered**:
- Filter in `_fetch_stock_positions()`: Rejected — that function's job is to fetch and
  normalise raw data, not apply business rules. Keeping the gate in `run_screener()` keeps
  the data layer clean.
- Filter in the API route handler: Rejected — business logic belongs in the service layer.

## Decision 2: `contracts` field on ScreenerResultView

**Decision**: Add `contracts: int` field to `ScreenerResultView` in `src/data/models.py`,
computed as `shares // 100` when building each result.

**Rationale**: The UI displays "available contracts" and the value is derivable from `shares`,
but it is cleaner to compute it once in the service and expose it explicitly on the model
rather than leave the derivation implicit or push it to the frontend.

**Alternatives considered**:
- Compute in frontend JS: Rejected — the backend is the authoritative source of business logic.
- Add a `@property` / computed field on ScreenerResultView: Rejected — Pydantic v2 computed
  fields add complexity; a plain `int` field set at construction is simpler.

## Decision 4: Screener result cache storage medium

**Decision**: sessionStorage under key `screener_results`.

**Rationale**: `eraseAll()` in `auth.js` already calls `sessionStorage.clear()` — logout
invalidation requires zero new code. sessionStorage survives same-tab navigation so the
cache is warm when the user navigates away from and back to the screener within a session.
The data is tab-scoped (no cross-tab bleed), which is consistent with Principle I. A
sessionStorage read + JSON.parse + DOM render completes in <50ms, satisfying the sub-second
target for cached loads.

**Alternatives considered**:
- IndexedDB: Overkill for a single array; async API adds complexity. Reserved for positions.
- In-memory module variable: Lost on page navigation within the same origin.
- localStorage: Persists across logout. Rejected — violates Principle I (session-local only).

## Decision 3: Empty-state handling

**Decision**: When `run_screener()` returns an empty list (all positions filtered), the
existing screener route returns an empty `results` array with a `screener_status` indicating
no results. No new empty-state route change is required — the frontend already handles the
empty array case. The spec's FR-003 (clear message) is satisfied by the existing empty-array
response, which the UI renders as "no results found".

**Rationale**: No UI change is required to satisfy FR-003 — the empty state is already handled.
