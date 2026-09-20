# Data Model: T+0 Payoff Overlay (016)

One new backend field. No new server-side models, no new sessionStorage keys. Everything else is client-side, in-memory only.

## Backend Change: `PositionView.underlying_price`

| Field | Type | Description |
|-------|------|-------------|
| `underlying_price` | `Decimal \| None` | Current price of the position's underlying instrument, as already returned by Schwab's option-chain quote. `None` if unavailable (e.g., quote fetch failed) — matches existing graceful-degradation pattern for other optional fields. |

Populated in `schwab_client.py::fetch_positions_and_greeks` from `greeks_raw.get("underlying_price")` (already present in the dict `_fetch_greeks()` builds — see research.md D-001). No new Schwab API call.

## Input: PositionView (extended — read-only from the graph's perspective)

Fields the overlay consumes, in addition to everything specs/015 already reads:

| Field | Type | Description |
|-------|------|-------------|
| `underlying_price` | string/Decimal \| null | New field, above |
| `implied_volatility` | float \| null | Already existed; now also drives the theoretical-value curve, not just the Greeks table |
| `days_to_expiry` | integer | Already existed; now also drives the checkpoint offsets |

## Computed Shapes (client-side only, never persisted)

### PayoffLeg (extended)

The existing `PayoffLeg` shape from specs/015 gains two fields, both already available on `PositionView`:

```
{
  strike:             number,
  optionType:         "call" | "put",
  quantity:           number,
  cost:               number,
  impliedVolatility:  number | null,   // NEW — from PositionView.implied_volatility
  daysToExpiry:       number,          // NEW — from PositionView.days_to_expiry
}
```

### Checkpoint

One of a fixed set of four, defined once in `payoff_theoretical.js` (research.md D-005):

```
{
  id:         string,           // "today" | "plus1wk" | "plus2wk" | "expiration"
  label:      string,           // display label
  offsetDays: number | null,    // days from today; null = use the intrinsic-only formula
}
```

### CheckpointCurve

The result of evaluating one checkpoint across the same 200-point price grid `analyzePayoff()` already produces (so both curves share one x-axis):

```
{
  checkpointId: string,
  points:       PayoffPoint[],   // same {price, pnl} shape as specs/015
}
```

### OverlayAnalysis

Everything the graph needs for one position/group, computed once when the position's data is prepared (not on every click, consistent with specs/015's precompute-at-init discipline):

```
{
  eligible:          boolean,           // false if any leg lacks usable IV, or daysToExpiry <= 0
  underlyingPrice:   number | null,     // from PositionView.underlying_price (or sharedOrNull across a group)
  referenceCurve:    PayoffPoint[],     // the existing expiration curve (specs/015, unchanged)
  checkpoints:       Checkpoint[],      // filtered to those available for this position's daysToExpiry
  curvesByCheckpoint: Map<string, PayoffPoint[]>,  // precomputed once per available checkpoint
  markerValues: {
    referencePnl:   number | null,      // combinedPayoff at underlyingPrice, if underlyingPrice is known
    checkpointPnl:  (checkpointId) => number | null,  // combinedTheoreticalPayoff at underlyingPrice for a given checkpoint
  }
}
```

If `eligible` is `false`, the graph renders exactly as specs/015 already does — `referenceCurve` only, no checkpoint control, no second curve. This is the FR-008 fallback path.

## State (module-level, session-scoped, never persisted)

Extends the existing specs/015 state:

| Variable | Type | Description |
|----------|------|-------------|
| `openGraphId` | string \| null | Unchanged from specs/015 |
| *(per open graph)* selected checkpoint | string | Not module-level — lives on the graph row's own DOM state (e.g. a `data-checkpoint` attribute), so it is naturally discarded when the row is removed. Always initializes to `"today"` on open, per Clarification Session 2026-09-19 (FR-013) — never carried over from a previously opened graph. |

## Storage

No new sessionStorage keys. `underlying_price` rides inside the existing cached position array (`position_cache.js` already stores whatever the `/api/positions/refresh` response contains) — no changes needed to the caching layer itself.
