# Research: T+0 Payoff Overlay (016)

## D-001 — Sourcing `underlying_price` Without a New Endpoint

**Decision**: Add `underlying_price: Decimal | None = None` to `PositionView` (`src/data/models.py`) and populate it in `schwab_client.py` from the value `_fetch_greeks()` already retrieves per symbol.

**Rationale**: `_fetch_greeks()` calls `client.get_option_chain(..., include_underlying_quote=True)` and already extracts `underlying_price = data.get("underlyingPrice") or ...`, storing it in each symbol's greeks dict (`result[req_sym] = {..., "underlying_price": underlying_price}`). `fetch_positions_and_greeks()` reads this dict (`greeks_raw`) to build Greeks but discards `underlying_price` before constructing `PositionView`. Specs/015's FR-012 ("current price marker") depended on this value and was never implemented for exactly this reason — grepping the shipped feature turns up zero references to a price marker anywhere. No new Schwab API call, no new endpoint, no new round trip: the value is already in memory for the duration of the request.

**Alternatives considered**:
- **New `/api/quote` endpoint**: Rejected — the value already exists in the same request; a second endpoint would add a network round trip for data already fetched.
- **Compute underlying price client-side from option mark + Greeks**: Rejected — solving for spot from delta/mark is unnecessary and less accurate than the value Schwab already returns directly.

---

## D-002 — Black-Scholes Pricing in JavaScript, Not a Server Endpoint

**Decision**: Port the pricing formula from `bs_calculator.py::_bs_price` into a new pure JS function `bsPrice(S, K, T, r, sigma, optionType)` in `payoff_theoretical.js`. A Python test file (`test_bs_pricing.py`) is the correctness oracle, following the exact pattern specs/015 established for `payoff_math.js`/`test_payoff_math.py`.

**Rationale**: The project has no JS test runner (specs/015, D-007, still true here). The existing `payoff_math.js` module is deliberately zero-dependency and computed entirely client-side so that switching checkpoints triggers no network request (FR-010) — a server endpoint would reintroduce exactly the round trip specs/015 avoided. `_bs_price` is a small, closed-form, side-effect-free function (no iteration, unlike `implied_volatility`'s Brent's-method solver) — well suited to a direct port.

```
d1 = (ln(S/K) + (r + 0.5·σ²)·T) / (σ·√T)
d2 = d1 - σ·√T
call price = S·Φ(d1) - K·e^(-rT)·Φ(d2)
put price  = K·e^(-rT)·Φ(-d2) - S·Φ(-d1)
```

`Φ` (standard normal CDF) has no built-in in JS; a standard rational (Abramowitz & Stegun) approximation is used, accurate to ~1e-7 — more than sufficient for a visual chart.

**Alternatives considered**:
- **New server endpoint accepting legs + returning curve points**: Rejected — see Rationale; also would need per-request validation of a new user-shaped input, expanding Principle II's threat surface for no benefit.
- **Reuse `_bs_price` via a WASM/Pyodide bridge**: Rejected — wildly disproportionate for one formula; adds a large dependency for something 15 lines of JS already solves.

---

## D-003 — Risk-Free Rate: Duplicated Constant, Not Piped from the Server

**Decision**: Hardcode `RISK_FREE_RATE = 0.045` in `payoff_theoretical.js` with a comment pointing back to `.env` / `greeks_service.py`, rather than injecting the server's configured value into the page.

**Rationale**: The frontend has no existing mechanism for injecting arbitrary server config into JS (position data arrives only via the JSON position payload). The rate is a slow-moving macro constant (updated "annually" per its own `.env.example` comment) already effectively hardcoded app-wide. Piping it through would require a new template variable or endpoint for a value that changes on the order of once a year — disproportionate per Principle V.

**Alternatives considered**:
- **Fetch rate from a new `/api/config` endpoint**: Rejected — a new endpoint for a constant that rarely changes; also a network round trip on every graph open.
- **Inline the rate into the Jinja template as a JS global**: Rejected — works, but adds a template-to-JS coupling for one number where a documented constant (already the project's pattern for the risk-free rate itself, which is a hardcoded default with an env override) is simpler and lower-risk.

---

## D-004 — Mixed-Expiry Exclusion (FR-011) Requires No Guard Code

**Decision**: No additional detection logic is needed to keep mixed-expiry (calendar/diagonal) positions out of the Today/checkpoint overlay.

**Rationale**: `buildSpreadGroups()` in `positions_ui.js` (specs/011) keys groups by `encodeURIComponent(p.underlying_symbol + '|' + p.expiry_date)` — a group can only ever contain legs that already share one underlying **and** one expiry. It is structurally impossible for a rendered group to contain mixed expiries today. A calendar/diagonal spread's two legs simply land in two separate groups (or as standalone rows), each independently eligible for its own single-expiry overlay. This confirms the spec's own design intent: the "view as of" checkpoint is independent of any single leg's expiry (it operates on whatever single-expiry group it's handed), so lifting the mixed-expiry exclusion later — if grouping is ever extended to span expiries — would only require extending `payoff_theoretical.js`'s per-leg time calculation, not redesigning the checkpoint mechanism.

**Alternatives considered**:
- **Explicit "all legs share one expiry" check inside `payoff_theoretical.js`**: Considered as a defensive assertion. Kept out of the initial implementation per Principle V (no code for a state that cannot currently occur), but noted as a one-line guard worth adding if grouping logic ever changes — see `tasks.md` follow-up note.

---

## D-005 — Checkpoint Representation and Availability

**Decision**: A fixed, ordered array of four checkpoints:

```js
export const CHECKPOINTS = [
  { id: 'today',      label: 'Today',      offsetDays: 0    },
  { id: 'plus1wk',    label: '+1 week',    offsetDays: 7    },
  { id: 'plus2wk',    label: '+2 weeks',   offsetDays: 14   },
  { id: 'expiration', label: 'Expiration', offsetDays: null }, // null = use the existing intrinsic-only formula
];
```

A checkpoint (other than "Expiration") is available only if `offsetDays < daysToExpiry` (FR-004) — strictly less than, so a checkpoint landing exactly on the expiration date is excluded, avoiding the degenerate `T = 0` case in the pricing formula (see D-006).

**Rationale**: A small fixed set (rather than a continuous slider, per user direction) is the cheapest control that still delivers Story 3's value. Using `null` for "Expiration" rather than `offsetDays === daysToExpiry` sidesteps floating-point/off-by-one edge cases entirely and routes that checkpoint through the already-correct, already-tested intrinsic-value formula instead of the Black-Scholes formula at a numerically unstable `T → 0`.

---

## D-006 — Curve Computation and the Expiration "Collapse" Behavior

**Decision**: For the "Expiration" checkpoint, reuse `combinedPayoff()` from `payoff_math.js` unchanged (intrinsic value; `T` is irrelevant). For all other checkpoints, compute `T = (daysToExpiry - offsetDays) / 365` per leg and price it via `bsPrice()`, using the same sign convention as the existing formula:

```
theoreticalPayoffPerShare(leg, price, T) = sign(leg.quantity) * bsPrice(price, leg.strike, T, RISK_FREE_RATE, leg.impliedVolatility, leg.optionType) - leg.cost
```

This is the same shape as `payoff_math.js`'s `legPayoffPerShare`, with `bsPrice(...)` standing in for `intrinsic(...)`. When "Expiration" is selected, the checkpoint-controlled curve is computed via the intrinsic formula and therefore coincides exactly with the reference curve (FR-005) by construction — no special-case branch needed beyond "which pricing function to call."

**Rationale**: Reusing the existing, tested intrinsic formula for the Expiration case guarantees no regression is possible in specs/015's existing behavior (it's the same function, untouched). Parallel structure between the two formulas (swap `intrinsic` for `bsPrice`) keeps the new module easy to verify against the old one.

**Verification** (T → 0 boundary): `bs_calculator.py::bs_greeks` already returns `nan` for `T <= 0` — confirming the deliberate choice in D-005 to exclude any checkpoint at or after expiration rather than attempt Black-Scholes pricing there.

---

## D-007 — Underlying Price Threading Through Existing Grouping

**Decision**: Add `underlying_price` to the `sharedOrNull(...)` fields already computed in `aggregateLegs()` (`positions_ui.js`), alongside `underlying_symbol`, `expiry_date`, and `days_to_expiry`.

**Rationale**: Every leg in a group shares one underlying (by construction, D-004), so every leg already carries the same `underlying_price` value (it comes from one option-chain call per underlying in `_fetch_greeks`). The existing `sharedOrNull` helper already implements exactly this "all legs agree, or null" pattern for other underlying-level fields — no new aggregation logic needed, just one more key in the list.

---

## D-008 — Test Strategy

**Decision**: `tests/unit/test_bs_pricing.py` ports `_bs_price` and the checkpoint-curve formula from D-006 into Python reference functions (mirroring the existing `test_payoff_math.py` structure exactly), asserting numeric expectations that `payoff_theoretical.js` must match. Covered cases:

1. `bsPrice` matches `bs_calculator.py::_bs_price` for representative calls and puts at various moneyness.
2. A single short put's theoretical value at `T > 0` sits strictly between its intrinsic value and its cost-adjusted max (i.e., contains positive extrinsic value away from expiration).
3. The "Expiration" checkpoint's combined P&L exactly equals `combinedPayoff()`'s output for the same legs and price (confirms the D-006 collapse).
4. A checkpoint whose `offsetDays >= daysToExpiry` is excluded from `availableCheckpoints()`.
5. A leg with `impliedVolatility <= 0` or missing renders the position ineligible for the overlay (falls back to Expiration-only), matching FR-008.

**Rationale**: Same reasoning as specs/015 D-007 — no JS test runner exists; the math is pure and side-effect-free, so a Python oracle is sufficient to satisfy Principle IV before the JS is written.
