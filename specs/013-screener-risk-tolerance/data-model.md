# Data Model: Screener Risk Tolerance Controls

**Feature**: 013-screener-risk-tolerance  
**Date**: 2026-05-17

## Modified Entity: ScreenerResultView

`src/data/models.py` — one new field added, all existing fields unchanged.

| Field | Type | Change | Notes |
|-------|------|--------|-------|
| ticker | str | unchanged | |
| shares | int | unchanged | |
| contracts | int | unchanged | |
| stock_price | float | unchanged | |
| iv_rank | float \| None | unchanged | |
| recommended_strike | float \| None | unchanged | Reflects Balanced profile (server default) |
| recommended_expiry | str \| None | unchanged | Reflects Balanced profile |
| bid_premium | float \| None | unchanged | Reflects Balanced profile |
| annualised_yield | float \| None | unchanged | Reflects Balanced profile |
| call_delta | float \| None | unchanged | Reflects Balanced profile |
| days_to_earnings | int \| None | unchanged | |
| composite_score | float | unchanged | Reflects Balanced profile |
| recommendation_status | Literal | unchanged | |
| sort_order | int | unchanged | |
| **candidates** | **list[CandidateOption]** | **NEW** | All liquid options in 7–60 DTE window |

## New Entity: CandidateOption (inline dict in candidates list)

Embedded in `ScreenerResultView.candidates`. Not a separate Pydantic model — serialised as plain dicts to keep the response lean.

| Field | Type | Description |
|-------|------|-------------|
| delta | float | Absolute delta value |
| bid | float | Bid price in dollars |
| dte | int | Days to expiry at time of fetch |
| strike | float | Strike price |
| expiry | str | Expiry date string (YYYY-MM-DD) |
| open_interest | int | Open interest (contracts) |

**Liquidity pre-filter applied server-side**: only candidates with `bid ≥ 0.05` and `open_interest ≥ 100` are included. Client does not need to re-apply liquidity rules.

## New Client-Side Entity: RiskProfile (JS only, never sent to server)

Lives in `screener_ui.js`. Never persisted except for the profile name in sessionStorage.

| Field | Type | Conservative | Balanced | Aggressive |
|-------|------|-------------|---------|------------|
| name | string | "conservative" | "balanced" | "aggressive" |
| targetDelta | number | 0.15 | 0.25 | 0.35 |
| dteMin | number | 30 | 30 | 7 |
| dteMax | number | 60 | 45 | 30 |
| yieldWeight | number | 0.15 | 0.30 | 0.40 |
| safetyWeight | number | 0.35 | 0.20 | 0.10 |
| ivWeight | number | 0.50 | 0.50 | 0.50 |

## SessionStorage Keys (client-side)

| Key | Value | Cleared |
|-----|-------|---------|
| `screener_results_<hash>` | JSON array of ScreenerResultView (existing) | On tab close / logout |
| `screener_profile` | `"conservative"` \| `"balanced"` \| `"aggressive"` | On tab close / logout |

## Scoring Algorithm (client-side, mirrors server)

```
For a given ticker and profile:

1. Filter candidates: dteMin ≤ candidate.dte ≤ dteMax
2. If no candidates: status = "insufficient_data"
3. Pick best: candidate with delta closest to profile.targetDelta
4. Compute annYield = (best.bid / stockPrice) * (365 / best.dte) * 100
5. Compute yieldScore = min(100, annYield * 5)
6. Compute deltaSafety = max(0, 100 - |best.delta - profile.targetDelta| * 400)
7. Compute score = ivRank * 0.50 + yieldScore * profile.yieldWeight
                  + deltaSafety * profile.safetyWeight (normalised: weights sum to 1.0)

Note: When profile = Balanced, output matches server-computed composite_score exactly.
```

## Unchanged: PositionView

No changes. Positions tab is completely isolated from this feature.
