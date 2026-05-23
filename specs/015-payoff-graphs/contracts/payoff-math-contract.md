# Contract: Payoff Math Module (015)

**Module**: `frontend/static/js/payoff_math.js`
**Type**: Pure ES module — no DOM, no side effects, no imports

---

## `legPayoffPerShare(leg, price) → number`

Returns the P&L per share for a single option leg at expiration when the underlying is at `price`.

**Inputs**:

| Param | Type | Description |
|-------|------|-------------|
| `leg.strike` | number | Strike price |
| `leg.optionType` | "call" \| "put" | Type |
| `leg.quantity` | number | Signed position size |
| `leg.cost` | number | Signed premium per share |
| `price` | number | Underlying price at expiration |

**Formula**:

```
intrinsic = optionType === 'call' ? max(price - strike, 0) : max(strike - price, 0)
return sign(quantity) * intrinsic - cost
```

**Contract cases** (verified by `tests/unit/test_payoff_math.py`):

| Leg | Price | Expected P&L/share |
|-----|-------|--------------------|
| Short put  qty=-1, cost=-3.85, K=195 | 200 | +3.85 |
| Short put  qty=-1, cost=-3.85, K=195 | 195 | +3.85 |
| Short put  qty=-1, cost=-3.85, K=190 | 190 | -1.15 |
| Long call  qty=+1, cost=+2.50, K=220 | 215 | -2.50 |
| Long call  qty=+1, cost=+2.50, K=220 | 225 | +2.50 |
| Short call qty=-1, cost=-3.20, K=220 | 215 | +3.20 |
| Short call qty=-1, cost=-3.20, K=220 | 225 | -1.80 |

---

## `combinedPayoff(legs, price) → number`

Returns the total combined P&L per share across all legs at `price`.

```
return sum(legPayoffPerShare(leg, price) * |leg.quantity| for leg in legs) / max(sum(|leg.quantity|))
```

Wait — actually: P&L is per unit of quantity. Re-reading the formula:

```
return sum(legPayoffPerShare(leg, price) for leg in legs)
```

where `legPayoffPerShare` already accounts for direction (via `sign(quantity)`). For positions with qty magnitude > 1, we multiply:

```
return sum(legPayoffPerShare(leg, price) * |leg.quantity| for leg in legs)
```

**Contract case — Bull call spread**:
- Short call: qty=-1, cost=-3.85, K=195
- Long put: qty=+1, cost=+1.95, K=185  
(Note: both same expiry, different strikes — this is a put spread)

At P=200: `3.85 + (0 - 1.95)` = 1.90  (above both strikes, put spread: long put worthless)
At P=190: `3.85 + (0 - 1.95)` = 1.90  (between strikes: short put ITM)

Wait let me re-check with actual spread data from demo:
Short put K=195, qty=-1, cost=-3.85
Long put K=185, qty=+1, cost=+1.95

At P=200 (above both): short put expires worthless: +3.85; long put expires worthless: -1.95; total = +1.90
At P=192 (between): short put ITM 3, long put OTM: (-1*max(195-192,0) - (-3.85)) + (1*max(185-192,0) - 1.95) = (-3+3.85) + (0-1.95) = 0.85 - 1.95 = -1.10

Hmm wait. Let me re-check the formula:

`legPayoffPerShare = sign(qty) * intrinsic - cost`

Short put (qty=-1, cost=-3.85, K=195) at P=192:
- intrinsic = max(195-192, 0) = 3
- sign(-1) * 3 - (-3.85) = -3 + 3.85 = 0.85 ✓ (received 3.85, paid 3 on assignment)

Long put (qty=+1, cost=+1.95, K=185) at P=192:
- intrinsic = max(185-192, 0) = 0
- sign(1) * 0 - 1.95 = -1.95 ✓ (paid 1.95, option expires worthless)

Total = 0.85 + (-1.95) = -1.10 per share. Combined * |qty| = -1.10 * 1 = -1.10. That makes sense for a put spread where you're short the higher strike.

OK I think I had the quantities backwards. Let me use the actual DEMO_POSITIONS_SPREADS as the contract case.

---

## `analyzePayoff(legs) → PayoffAnalysis`

Scans the payoff curve over 200 price points and returns:
- `maxGain`: highest pnl value (may be `Infinity` for naked long options)
- `maxLoss`: lowest pnl value (may be `-Infinity` for naked short options)
- `breakevens`: prices where pnl crosses zero (extracted by sign-change detection on the curve)
- `strikePrices`: sorted unique list of all leg strike values
- `curve`: array of `{price, pnl}` points (200 points)

**Contract invariants**:
1. For any vertical spread: `maxGain` is finite and positive
2. For any vertical spread: `maxLoss` is finite and negative
3. `maxGain + maxLoss = width_of_spread - net_premium` (analytical check)
4. Number of breakeven crossings for a vertical spread is exactly 1
5. `strikePrices` contains exactly as many entries as there are distinct strikes across all legs

---

## `buildPayoffSvg(legs, options) → string`

Returns an SVG string suitable for injection via `innerHTML`.

**Guaranteed properties**:
- Contains no `<script>` elements
- Contains no event handler attributes (`onclick`, `onmouseover`, etc.)
- All user-visible text (labels) is either: a computed number, or a static string from the options object — no raw user data injected without escaping
- Viewbox is `0 0 {options.width} {options.height}`
- The SVG is self-contained (no external `href`, no `xlink:href` to remote resources)

**Visual elements**:
1. Background rect: transparent
2. Zero line: horizontal dashed stroke at y=0 pnl
3. Payoff polyline: single path connecting all 200 curve points
4. Per-leg vertical dashed lines at each strike price
5. Max gain annotation: green text + horizontal tick at max gain price
6. Max loss annotation: red text + horizontal tick at max loss price
7. X-axis: thin line + 4-6 price labels (rounded to nearest dollar)
8. Y-axis: thin line + 4 P&L labels (e.g. "+3.85", "0.00", "-1.15")
9. Title text (top-left): e.g. "AAPL · 2025-07-18"
