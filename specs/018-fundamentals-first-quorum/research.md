# Research: Fundamentals-First Quorum

Decisions for spec 018. Numbering continues from spec 017 (D-001–D-008) as D-101 onwards.

## D-101 — Where fundamentals are computed

**Decision**: New pure module `src/services/fundamentals.py` with three entry points:
`realised_volatility(closes)`, `leg_fundamentals(leg, realised_vol, r)`, and
`position_fundamentals(legs)`. `fetch_positions_and_greeks` calls the first two during a
positions refresh; the quorum route calls `leg_fundamentals` again (re-derivation, D-105)
and `position_fundamentals` on the legs it receives.

**Rationale**: One implementation serves refresh and quorum, so the figures the analysts
see can never disagree with the legs. Pure functions (no I/O) are trivially unit-testable
against hand-worked references (SC-103).

**Alternatives considered**: Computing in JavaScript (the browser already has
`payoff_math.js`) — rejected: FR-104 requires deterministic server-side figures, and a
second implementation would drift. Letting the model compute — rejected: the whole point
of the feature is that LLM arithmetic is unreliable.

## D-102 — Realised volatility source and method

**Decision**: `client.get_price_history_every_day(underlying, start_datetime=now-60d,
end_datetime=now)` once per distinct underlying per refresh, run concurrently with the
option-chain fetches. Take the last 31 daily closes → 30 log returns → sample standard
deviation × √252. Fewer than 20 returns, any non-positive close, or any fetch error →
`None` (unavailable, FR-105). A Schwab 4xx/5xx or transport error on this call is logged to
the `security` logger as `SECURITY schwab_api_error source=price_history status=<code>`
(no symbol, no values), per Constitution II security-event logging. Index underlyings are looked up with Schwab's `$` prefix
(`SPX` → `$SPX`, `SPXW` → `$SPX`, `NDX` → `$NDX`, `RUT` → `$RUT`, `VIX` → `$VIX`); other
symbols as-is.

**Rationale**: 60 calendar days always contains ≥ 31 trading days. Close-to-close
volatility is the standard, well-understood estimator and matches how traders quote
"30-day realised". One call per underlying keeps the added Schwab load to a handful of
requests per refresh (well under the ~120/min limit).

**Alternatives considered**: Parkinson/Garman-Klass range estimators — more efficient but
less familiar and need high/low data quality we cannot verify. Stored daily IV for a true
IV rank — requires persistence, which the constitution forbids on the server (out of scope).

## D-103 — Per-leg fundamental formulas

All inputs are already on `PositionView`. `S` = underlying price, `K` = strike, `q` =
signed quantity, `σ` = implied volatility (decimal), `T = max(dte, 1) / 365`, `r` =
`RISK_FREE_RATE` (existing env, default 0.045), multiplier 100.

| Figure | Formula | Unavailable when |
|---|---|---|
| `moneyness_pct` | call `(S−K)/S×100`; put `(K−S)/S×100` (positive = in the money) | no `S` |
| `expected_move` | `S × σ × √T` (1-σ move to expiry, in price units) | no `S` or no `σ` |
| `prob_itm` | call `N(d2)`; put `N(−d2)` (Black-Scholes risk-neutral) | no `S` or no `σ` |
| `position_delta` | `delta × q × 100` (share-equivalent) | no delta |
| `dollar_delta` | `position_delta × S` | no delta or no `S` |
| `position_gamma` | `gamma × q × 100` | no gamma |
| `dollar_theta` | `theta × q × 100` ($/day) | no theta |
| `dollar_vega` | `vega × q × 100` ($ per 1 vol point) | no vega |
| `realised_volatility` | D-102 | per D-102 |
| `iv_rv_ratio` | `σ / realised_volatility` | either missing or RV = 0 |

`T` floors at one day so expiration day never divides by zero (spec edge case).

## D-104 — Position-level formulas (any 1–4 legs, one underlying)

**Decision**: Treat the expiry payoff as a piecewise-linear function of the underlying
price `P`: `payoff(P) = Σ q·100·(intrinsic(P) − cost)`. Evaluate it at `P = 0`, at every
strike, and read the slope beyond the highest strike (`Σ q·100` over calls).

- **Breakevens**: zero crossings between consecutive evaluation points (linear
  interpolation), plus the crossing beyond the top strike if the tail slope reaches zero.
- **Max profit / max loss**: the max / min over evaluation points; `None` (unbounded) when
  the tail slope is positive / negative. Legs with different expiries (calendars) → all
  expiry-payoff figures unavailable; payoff at a single expiry is undefined for them.
- **`pct_max_profit_captured`**: `net_unrealised_pnl / max_profit × 100` when max profit is
  finite and > 0.
- **Net Greeks**: sums of the per-leg position/dollar Greeks (a missing leg Greek makes the
  sum unavailable rather than silently partial).
- **`theta_pct_of_remaining`**: `net dollar_theta / |Σ q·100·mark| × 100` — daily decay as a
  share of the premium still in the position. Unavailable if that premium is 0.

**Rationale**: Exact for every standard structure (verticals, strangles, condors,
butterflies, ratio spreads) with no pattern-matching per strategy.

**Alternatives considered**: Per-strategy formulas — brittle and incomplete. Numerical
grid search — approximate and slower for no gain.

## D-105 — Quorum request carries leg fields + realised vol; server re-derives the rest

**Decision**: The browser sends, per leg: underlying, option type, strike, expiry, days to
expiry, signed quantity, cost, mark, unrealised P&L, the four Greeks, IV, underlying price,
and `realised_volatility`; plus one `as_of`. The server re-runs `leg_fundamentals` on these
fields and runs `position_fundamentals`. No leg OCC symbol and no account hash are sent.

**Rationale**: Realised vol is the only fundamental that needs data (price history) the leg
fields do not contain. Re-deriving the rest costs microseconds, removes a whole class of
"fundamentals inconsistent with legs" inputs, and shrinks the validated surface. This is
still "no re-fetch" (FR-110): nothing is fetched from Schwab except the token check.

**Alternatives considered**: Send the full fundamentals object and trust it — more fields to
bound, and a tampered or stale-cached object could disagree with its own legs.

## D-106 — Request validation and error bodies

**Decision**: Pydantic v2 models with `model_config = ConfigDict(extra="forbid")`, bounded
`Field`s (ranges in data-model.md), `Literal` enums, and a ticker regex
`^\$?[A-Z0-9./^-]{1,10}$`. The route reads the JSON body itself (≤ 16 KiB) and calls
`model_validate`; on failure it returns `422 {"detail": "Invalid quorum request",
"fields": [<dotted locations>]}` — field locations only, never the submitted values.

**Rationale**: FastAPI's default 422 body echoes the submitted input; the constitution
(Principle II, "Zero sensitive output") forbids position data in any error message.

**Alternatives considered**: A global `RequestValidationError` handler — would change every
other endpoint's error contract; out of scope.

## D-107 — Token validation without re-fetching positions

**Decision**: One `client.get_account_numbers()` call before any model or feed work.
Schwab 401 → `401 {"detail": "Missing or invalid token"}` plus the existing
`401_invalid_token` security event; any other non-2xx or transport error → the
`schwab_api_error` security event plus `502 {"detail": "Could not verify Schwab login"}`. The response body is discarded unread.

**Rationale**: The lightest authenticated Schwab endpoint; without it any non-empty Bearer
string would reach Vertex AI (cost abuse), since `get_schwab_client` never validates.

**Alternatives considered**: `get_user_preferences` — larger payload containing
identifying data we would then have to avoid logging. Skipping validation — rejected above.

## D-108 — Freshness

**Decision**: Every `PositionView` gains `as_of` (UTC, one value per refresh). The quorum
request's `as_of` must satisfy `now − 15 min ≤ as_of ≤ now + 2 min`; otherwise
`409 {"detail": "Position data is stale — refresh positions and try again"}`. The browser
sends the oldest `as_of` among the chosen legs.

**Rationale**: 409 is distinct from 422 so the panel can show a targeted "refresh first"
message. Two minutes of forward skew tolerates client/server clock drift.

## D-109 — Greek placeholder guard (FR-106, FR-107)

**Decision**: In `greeks_service.build_greeks`, a raw value is kept only if it is a finite
float within its valid range; otherwise it is `None` and the Black-Scholes fallback
applies. Ranges: delta [−1, 1]; gamma [0, 10]; theta [−10 000, 10 000]; vega [0, 10 000];
IV (Schwab percent) (0, 1000] then ÷ 100. The fallback trigger changes from
`not all([delta, gamma, theta, vega])` (true for a 0) to "any value is None".

**Rationale**: Covers −999, NaN, ±inf, and absurd magnitudes with one rule; zero survives.

## D-110 — Narrow option-chain request (FR-108)

**Decision**: `_fetch_greeks` groups held contracts by underlying and calls
`get_option_chain(symbol, contract_type=CALL|PUT|ALL, from_date=min expiry,
to_date=max expiry, strike=<K> if exactly one distinct strike, include_underlying_quote=True)`.
The underlying key is parsed from the OCC symbol (existing `_parse_occ_symbol`) rather than
`symbol[:6]`.

**Rationale**: Date-range filtering alone removes most expiries (the bulk of the payload for
SPY/QQQ); single-strike filtering removes nearly all the rest for single-leg holdings. The
existing matching loop is unchanged, so Greeks are identical (SC-108). If any held symbol is left unmatched after the narrowed call, that underlying is re-fetched once with the full chain (safety net for adjusted or non-standard contracts).

## D-111 — Seat recast and concurrency

**Decision**: `SEATS` becomes the five FR-114 lenses (ids `greeks_exposure`,
`volatility_pricing`, `time_decay_pnl`, `strike_assignment`, `macro_news_overlay`).
Seats 1–4 share one instruction template ("form your vote from the FUNDAMENTALS block;
cite at least one figure") and one message (position + leg + position fundamentals, no
news). Seat 5 has its own template and message (fundamentals + brief + headlines).
`run_quorum` starts, concurrently: `fetch_headlines`, `_research`, and seats 1–4; seat 5
starts when headlines and research both finish. `fetch_headlines` moves from the route into
`run_quorum`. The research instruction is refocused on the underlying and scheduled events
before expiry (FR-117). Tally unchanged.

**Rationale**: Critical path becomes `max(seats 1–4, max(feeds, research) + seat 5)` instead
of `feeds + research + slowest seat` (SC-101).

## D-112 — Headline selection (FR-116, FR-118)

**Decision**: `fetch_headlines` returns ticker-feed and general items separately to a pure
`select_headlines(ticker, general, now, limit=12, ticker_quota=5, max_age=48h)`: drop items
without a timestamp or older than 48 h, de-duplicate by case-folded title across both
lists, take up to 5 newest ticker items, fill to 12 with newest general items, return
newest first. `FEED_TIMEOUT_SECONDS = 3.0`.

## D-113 — Screener volatility (FR-109)

**Decision**: Remove `iv_rank`; add `implied_volatility`, `realised_volatility`,
`iv_rv_ratio`, and `vol_score` (0–100) to `ScreenerResultView`. IV is the recommended
call's contract volatility (percent → decimal), so suppressed and insufficient-data rows
(no recommended call) have IV/RV unavailable; realised vol from D-102 (one price-history
call per ticker, concurrent with the chain fetch). `vol_score = clamp((ratio − 0.8) /
(1.5 − 0.8), 0, 1) × 100` — ratio ≤ 0.8 (IV cheap) scores 0, ≥ 1.5 (IV rich, good for
selling calls) scores 100. Missing ratio → `vol_score = None`, contributes 0 to the
composite. The composite weighting (server `_compute_composite_score` and client
`screener_ui.js` risk profiles) swaps `iv_rank` for `vol_score` unchanged otherwise. The
"IV Rank" column becomes "IV/RV" showing e.g. `1.42×`.

**Rationale**: The current `instrument.get("volatility")` on an account EQUITY position is
typically absent, and `×200` is not a rank. IV/RV is the honest "rich vs cheap" signal
available without stored history; the 0.8–1.5 band spans the typical range of the ratio.

## D-114 — Positions refresh response shape

**Decision**: `GET /api/positions/refresh` keeps returning a JSON array of `PositionView`;
each gains `as_of` and a nested `fundamentals` object (D-103 fields). Additive only, so the
dashboard, payoff graphs, and sessionStorage cache keep working unchanged.

## Follow-ups (out of scope)

- Show fundamentals on dashboard rows.
- Days-to-earnings as a leg fundamental for the Volatility & Pricing seat.
- True IV rank from client-side IV history.
