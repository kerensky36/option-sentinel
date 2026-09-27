# Contract: `POST /api/quorum/vote` (v2, spec 018)

Supersedes `specs/017-macro-quorum-agents/contracts/quorum-api-contract.md` for the request
shape, error table, and service signatures. Auth, rate limit (5/min), security headers and
`Cache-Control: no-store` are unchanged.

## Request

Body ≤ 16 KiB. Unknown fields anywhere → 422. Field bounds: see `data-model.md` → QuorumLegIn.

```json
{
  "as_of": "2026-09-27T14:42:10Z",
  "legs": [
    {
      "underlying_symbol": "SPY",
      "option_type": "put",
      "strike": "560",
      "expiry_date": "2026-10-17",
      "days_to_expiry": 20,
      "quantity": -2,
      "cost": "4.10",
      "current_mark": "0.82",
      "unrealised_pnl": "656.00",
      "delta": -0.11, "gamma": 0.008, "theta": -0.06, "vega": 0.21,
      "implied_volatility": 0.17,
      "underlying_price": "598.40",
      "realised_volatility": 0.12
    }
  ]
}
```

No `account_hash`, no leg OCC symbol.

## Processing order (all before any model call)

1. `quorum_configured()` else 503.
2. Read body, size check, `QuorumRequest.model_validate` else 422 (generic, no values echoed).
3. Freshness (`as_of` within −15 min / +2 min of server time) else 409.
4. Token check: one `get_account_numbers()` → 401 / 502.
5. `build_position_context(legs)` — re-derives leg fundamentals, computes position
   fundamentals.
6. `run_quorum(ctx)` under a 60 s budget else 504.

The route makes **no** positions, option-chain, or price-history call (SC-102).

## Responses

| Status | When | Body |
|---|---|---|
| 200 | Quorum ran (any verdict) | `QuorumResult` (data-model.md), incl. `as_of`, `position_fundamentals` |
| 401 | Missing bearer, or Schwab rejects it | `{"detail": "Missing or invalid token"}` |
| 409 | `as_of` stale or in the future | `{"detail": "Position data is stale — refresh positions and try again"}` |
| 422 | Not JSON, > 16 KiB, extra field, out-of-range value, 0 or > 4 legs, > 1 underlying | `{"detail": "Invalid quorum request", "fields": ["legs.0.delta", …]}` |
| 429 | Rate limit | slowapi default |
| 502 | Token check failed for a non-auth reason | `{"detail": "Could not verify Schwab login"}` |
| 503 | Not configured | `{"detail": "Quorum is not configured on this server"}` |
| 504 | > 60 s | `{"detail": "Quorum timed out"}` |

**REMOVED**: 404 (symbol not in account) — no account lookup any more.

## Invariants

- Model requests contain only FR-113 fields; seats 1–4 receive no headlines and no brief;
  seat 5 is the only recipient of headlines/brief (SC-105, SC-107).
- `votes` has exactly 5 entries in fixed FR-114 seat order; tally rule unchanged (017 FR-007).
- `headlines` ≤ 12, all ≤ 48 h old, ≤ 5 from the underlying's own feed.
- Request/result values are never logged; 4xx bodies never echo submitted values.

## Changed endpoint: `GET /api/positions/refresh`

Response stays a JSON array of `PositionView`; each item gains `as_of` and `fundamentals`
(LegFundamentals). Otherwise unchanged. One extra Schwab price-history call per distinct
underlying; the option-chain call is narrowed (D-110).

## Changed endpoint: `GET /api/screener/refresh`

`ScreenerResultView.iv_rank` removed; `implied_volatility`, `realised_volatility`,
`iv_rv_ratio`, `vol_score` added.

## Service API

```python
# src/services/fundamentals.py (NEW, pure)
def realised_volatility(closes: list[float], *, window: int = 30) -> float | None
def leg_fundamentals(leg: LegInputs, realised_vol: float | None, *, r: float) -> LegFundamentals
def position_fundamentals(legs: list[PositionLegContext], net_unrealised_pnl: Decimal) -> PositionFundamentals

# src/services/schwab_client.py
async def fetch_realised_vols(client, underlyings: set[str]) -> dict[str, float | None]   # NEW
async def fetch_positions_and_greeks(schwab_client, account_hash=None) -> list[PositionView]  # + as_of, fundamentals
async def verify_token(client) -> None   # NEW; raises TokenRejected / TokenCheckFailed

# src/services/news_feeds.py
FEED_TIMEOUT_SECONDS = 3.0
def select_headlines(ticker_items, general_items, *, now, limit=12, ticker_quota=5,
                     max_age=timedelta(hours=48)) -> list[Headline]            # NEW, pure
async def fetch_headlines(underlying, *, client=None) -> list[Headline]        # uses select_headlines

# src/services/quorum_agents.py
SEATS: tuple[Seat, ...]            # FR-114 order; Seat gains `uses_news: bool`
def build_position_context(legs: list[QuorumLegIn], as_of: datetime) -> PositionContext
async def run_quorum(ctx, *, model=None, seat_timeout=40.0, research_timeout=15.0,
                     headline_fetcher=fetch_headlines) -> QuorumResult     # fetches news itself
```
