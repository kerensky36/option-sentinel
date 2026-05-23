# Data Model: Option Payoff Graphs (015)

No new server-side models. Feature is entirely client-side.

## Input: PositionView (existing — read-only)

Fields consumed by the payoff engine:

| Field | Type | Description |
|-------|------|-------------|
| `strike` | string/Decimal | Strike price (e.g. "195.00") |
| `option_type` | "call" \| "put" | Type of option |
| `quantity` | integer | Signed position size: negative = short, positive = long |
| `cost` | string/Decimal | Signed premium per share: negative = received (short), positive = paid (long) |
| `underlying_symbol` | string | Used only for graph title label |
| `expiry_date` | string | Used only for graph title label |

All other fields (greeks, IV, current_mark, unrealised_pnl) are NOT used by payoff computation.

## Computed Shapes (client-side only, never persisted)

### PayoffLeg

Normalised representation of a single leg for computation:

```
{
  strike:     number,   // parsed from PositionView.strike
  optionType: "call" | "put",
  quantity:   number,   // signed (negative = short)
  cost:       number,   // signed (negative = received premium)
}
```

### PayoffPoint

One point on the payoff curve:

```
{
  price: number,   // underlying price at expiration
  pnl:   number,   // combined net P&L per share at this price
}
```

### PayoffAnalysis

Summary of a position's risk/reward:

```
{
  maxGain:      number | Infinity,   // maximum theoretical gain per share
  maxLoss:      number | -Infinity,  // maximum theoretical loss per share (negative)
  maxGainPrice: number | null,       // underlying price at which max gain occurs
  maxLossPrice: number | null,       // underlying price at which max loss occurs
  breakevens:   number[],            // price(s) where P&L crosses zero
  strikePrices: number[],            // sorted list of all leg strikes (de-duplicated)
  curve:        PayoffPoint[],       // full payoff curve (200 points)
}
```

### GraphOptions (configuration passed to SVG renderer)

```
{
  width:  number,   // viewBox width (default 800)
  height: number,   // viewBox height (default 180)
  title:  string,   // e.g. "AAPL · 2025-07-18"
}
```

## State (module-level, session-scoped, never persisted)

| Variable | Type | Description |
|----------|------|-------------|
| `openGraphId` | string \| null | The `id` of the currently visible graph `<tr>`, or null |

Only one graph is open at a time. State lives in `payoff_graph.js` module scope. Cleared automatically when the positions table is re-rendered.

## Storage

No new sessionStorage keys. No server-side storage. No changes to existing caches.
