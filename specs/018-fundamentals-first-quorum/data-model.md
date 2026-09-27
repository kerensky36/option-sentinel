# Data Model: Fundamentals-First Quorum

All models live in `src/data/models.py` (Pydantic v2). Nothing is persisted server-side.
"Unavailable" is always `null`, never `0` (FR-105). Changes relative to spec 017's
data-model are marked **NEW** / **CHANGED** / **REMOVED**.

## LegFundamentals — NEW

Per-leg figures computed at positions refresh (D-103) and re-derived at quorum time (D-105).

| Field | Type | Meaning |
|---|---|---|
| `realised_volatility` | float \| null | Underlying 30-day close-to-close RV, annualised decimal |
| `iv_rv_ratio` | float \| null | IV ÷ RV |
| `moneyness_pct` | float \| null | % in the money (+) / out of the money (−) |
| `expected_move` | float \| null | 1-σ underlying move to expiry, price units |
| `prob_itm` | float \| null | 0–1, Black-Scholes N(±d2) |
| `position_delta` | float \| null | Share-equivalent delta (delta × q × 100) |
| `dollar_delta` | float \| null | position_delta × underlying price |
| `position_gamma` | float \| null | gamma × q × 100 |
| `dollar_theta` | float \| null | $ per day for the leg |
| `dollar_vega` | float \| null | $ per 1 vol point for the leg |

## PositionView — CHANGED

Adds two fields (additive; D-114):

| Field | Type | Notes |
|---|---|---|
| `as_of` | datetime (UTC) | Same value for every position in one refresh (FR-103) |
| `fundamentals` | LegFundamentals | Always present; individual fields may be null |

Greeks `*_source` semantics unchanged; placeholder values now become `"calculated"` (FR-106)
and zeros stay `"api"` (FR-107).

## QuorumLegIn — NEW (request, strict)

`model_config = ConfigDict(extra="forbid")`. Replaces 017's `symbols` list.

| Field | Type / bound |
|---|---|
| `underlying_symbol` | str, regex `^\$?[A-Z0-9./^-]{1,10}$` |
| `option_type` | `"call"` \| `"put"` |
| `strike` | Decimal, 0 < x ≤ 1 000 000 |
| `expiry_date` | date, today − 1 day ≤ x ≤ today + 4 years |
| `days_to_expiry` | int, 0 ≤ x ≤ 1 500 |
| `quantity` | int, −100 000 ≤ x ≤ 100 000, x ≠ 0 |
| `cost` | Decimal, 0 ≤ x ≤ 1 000 000 (per share) |
| `current_mark` | Decimal, 0 ≤ x ≤ 1 000 000 (per share) |
| `unrealised_pnl` | Decimal, \|x\| ≤ 1 000 000 000 |
| `delta` | float \| null, −1 ≤ x ≤ 1 |
| `gamma` | float \| null, 0 ≤ x ≤ 10 |
| `theta` | float \| null, \|x\| ≤ 10 000 |
| `vega` | float \| null, 0 ≤ x ≤ 10 000 |
| `implied_volatility` | float \| null, 0 < x ≤ 10 (decimal) |
| `underlying_price` | Decimal \| null, 0 < x ≤ 1 000 000 |
| `realised_volatility` | float \| null, 0 ≤ x ≤ 10 |

All floats must be finite. No free-text fields.

## QuorumRequest — CHANGED

`extra="forbid"`.

| Field | Type | Rule |
|---|---|---|
| `as_of` | datetime (tz-aware) | Freshness checked in the route (D-108 → 409) |
| `legs` | list[QuorumLegIn] | 1–4 items; one distinct `underlying_symbol` |

**REMOVED**: `symbols`, `account_hash`.

## PositionLegContext — CHANGED

The model-facing allow-list (FR-113). 017 fields unchanged, plus
`fundamentals: LegFundamentals`. Built from `QuorumLegIn` (not from `PositionView` any more).

## PositionFundamentals — NEW

| Field | Type |
|---|---|
| `net_position_delta`, `net_dollar_delta`, `net_position_gamma`, `net_dollar_theta`, `net_dollar_vega` | float \| null |
| `breakevens` | list[float] (empty if none or unavailable) |
| `max_profit`, `max_loss` | float \| null (null = unbounded or unavailable) |
| `max_profit_unbounded`, `max_loss_unbounded` | bool |
| `pct_max_profit_captured` | float \| null |
| `theta_pct_of_remaining` | float \| null |
| `single_expiry` | bool (false → expiry-payoff figures null) |

## PositionContext — CHANGED

017 fields plus `position_fundamentals: PositionFundamentals` and `as_of: datetime`.

## Headline — unchanged

## AnalystVote / AnalystBallot / TallyEntry — unchanged

`seat` / `lens` values change to the FR-114 set (D-111).

## QuorumResult — CHANGED

Adds:

| Field | Type | Notes |
|---|---|---|
| `as_of` | datetime | Echo of request `as_of` (FR-112) |
| `position_fundamentals` | PositionFundamentals | What the analysts were given |

`headlines` now holds ≤ 12 items (FR-116). `macro_brief` is the brief seat 5 saw.

## ScreenerResultView — CHANGED (FR-109, D-113)

**REMOVED**: `iv_rank`. **NEW**: `implied_volatility`, `realised_volatility`, `iv_rv_ratio`,
`vol_score` (all float \| null).

## Validation → HTTP mapping (quorum)

| Condition | Status | Body |
|---|---|---|
| Body not JSON / > 16 KiB / schema or range failure / >1 underlying | 422 | `{"detail": "Invalid quorum request", "fields": [...]}` — no values echoed |
| `as_of` older than 15 min or > 2 min in future | 409 | `{"detail": "Position data is stale — refresh positions and try again"}` |
| Schwab rejects token | 401 | `{"detail": "Missing or invalid token"}` |
| Schwab token check fails otherwise | 502 | `{"detail": "Could not verify Schwab login"}` |
