# Contract: Theoretical Payoff Module (016)

**Module**: `frontend/static/js/payoff_theoretical.js`
**Type**: Pure ES module — no DOM, no side effects; imports `legPayoffPerShare`/`combinedPayoff` from `payoff_math.js`

---

## `bsPrice(S, K, T, r, sigma, optionType) → number`

Black-Scholes theoretical price of one option, mirroring `src/services/bs_calculator.py::_bs_price` exactly.

**Inputs**:

| Param | Type | Description |
|-------|------|-------------|
| `S` | number | Underlying price |
| `K` | number | Strike price |
| `T` | number | Time to expiry, in years |
| `r` | number | Risk-free rate (e.g. 0.045) |
| `sigma` | number | Implied volatility (e.g. 0.30) |
| `optionType` | "call" \| "put" | Option type |

**Formula**:

```
d1 = (ln(S/K) + (r + 0.5·σ²)·T) / (σ·√T)
d2 = d1 - σ·√T
call: S·Φ(d1) - K·e^(-r·T)·Φ(d2)
put:  K·e^(-r·T)·Φ(-d2) - S·Φ(-d1)
```

where `Φ` is the standard normal CDF (rational approximation acceptable; no built-in exists in JS).

**Contract cases** (verified against `bs_calculator.py::_bs_price`, `tests/unit/test_bs_pricing.py`):

| Inputs | Expected price |
|--------|-----------------|
| S=190, K=195, T=57/365, r=0.045, σ=0.30, put | 10.9995 |
| S=190, K=195, T=0.5/365, r=0.045, σ=0.30, put (near expiry) | 4.9951 (approaches intrinsic value of 5.00) |
| S=288, K=280, T=57/365, r=0.045, σ=0.48, call | 26.7313 |

**Invariant**: as `T → 0`, `bsPrice` converges to the intrinsic value (`max(S-K,0)` for calls, `max(K-S,0)` for puts) — see the near-expiry case above. `bsPrice` is not called for `T <= 0`; that case is always routed to the existing intrinsic-only formula instead (research.md D-005/D-006).

---

## `theoreticalPayoffPerShare(leg, price, daysToExpiry) → number`

Returns the P&L per share for one leg if it were valued today (or at any given `daysToExpiry`), rather than at expiration.

**Inputs**:

| Param | Type | Description |
|-------|------|-------------|
| `leg.strike` | number | Strike price |
| `leg.optionType` | "call" \| "put" | Type |
| `leg.quantity` | number | Signed position size |
| `leg.cost` | number | Signed premium per share |
| `leg.impliedVolatility` | number | Must be > 0 — caller is responsible for the FR-008 eligibility check before calling this |
| `price` | number | Underlying price |
| `daysToExpiry` | number | Days remaining at the point being evaluated (already offset by the selected checkpoint) |

**Formula** (parallel to `legPayoffPerShare` in `payoff_math.js`, substituting `bsPrice` for intrinsic value):

```
T = daysToExpiry / 365
theoretical = bsPrice(price, leg.strike, T, RISK_FREE_RATE, leg.impliedVolatility, leg.optionType)
return sign(leg.quantity) * theoretical - leg.cost
```

`RISK_FREE_RATE` is a module-level constant (`0.045`), documented as mirroring `.env`'s `RISK_FREE_RATE` (research.md D-003).

---

## `combinedTheoreticalPayoff(legs, price, daysToExpiry) → number`

Sum of `theoreticalPayoffPerShare` across all legs — parallel to `combinedPayoff` in `payoff_math.js`.

---

## `CHECKPOINTS` (constant) and `availableCheckpoints(daysToExpiry) → Checkpoint[]`

```js
CHECKPOINTS = [
  { id: 'today',      label: 'Today',      offsetDays: 0    },
  { id: 'plus1wk',    label: '+1 week',    offsetDays: 7    },
  { id: 'plus2wk',    label: '+2 weeks',   offsetDays: 14   },
  { id: 'expiration', label: 'Expiration', offsetDays: null },
];
```

`availableCheckpoints(daysToExpiry)` returns the subset where `offsetDays === null || offsetDays < daysToExpiry` (FR-004 — strictly less than, so a checkpoint landing exactly on the expiration date is excluded).

**Contract cases**:

| `daysToExpiry` | Available checkpoint ids |
|---|---|
| 30 | today, plus1wk, plus2wk, expiration |
| 10 | today, plus1wk, expiration |
| 5 | today, expiration |
| 0 | expiration only |

---

## `isEligibleForOverlay(legs) → boolean`

Returns `false` (triggering the FR-008 fallback to expiration-only rendering) if any leg has a missing or non-positive `impliedVolatility`, or if `daysToExpiry <= 0`.

---

## `computeCheckpointCurve(legs, checkpoint, priceGrid) → PayoffPoint[]`

Evaluates one checkpoint across the same 200-point `priceGrid` that `analyzePayoff(legs).curve` already produces (specs/015), so both curves share one x-axis.

```
if checkpoint.offsetDays === null:
  return priceGrid.map(pt => ({ price: pt.price, pnl: combinedPayoff(legs, pt.price) }))   // existing intrinsic formula
else:
  daysToExpiry = legs[0].daysToExpiry - checkpoint.offsetDays
  return priceGrid.map(pt => ({ price: pt.price, pnl: combinedTheoreticalPayoff(legs, pt.price, daysToExpiry) }))
```

**Contract invariant** (verified in `tests/unit/test_bs_pricing.py`): `computeCheckpointCurve(legs, { offsetDays: null }, priceGrid)` produces output identical, point for point, to `analyzePayoff(legs).curve` — this is what "coincides with the Expiration reference curve" (FR-005) means concretely, and it holds by construction since both call the same underlying `combinedPayoff` function.

---

## Marker values at the current underlying price

Not a grid lookup — evaluated directly, since `underlyingPrice` will rarely land exactly on one of the 200 grid points:

```
referencePnl  = combinedPayoff(legs, underlyingPrice)
checkpointPnl = combinedTheoreticalPayoff(legs, underlyingPrice, daysToExpiryForSelectedCheckpoint)
```

Both values are computed whenever the marker is drawn (FR-006); `null` if `underlyingPrice` is unavailable (FR-007).
