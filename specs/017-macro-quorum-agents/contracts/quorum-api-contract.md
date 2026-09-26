# Contract: `POST /api/quorum/vote`

**Auth**: `Authorization: Bearer <schwab access token>` (same as all `/api` routes).
**Rate limit**: 5/minute per client IP (FR-013).
**Headers on response**: standard security headers + `Cache-Control: no-store`.

## Request

```json
{ "symbols": ["SPY   261017C00560000", "SPY   261017C00570000"], "account_hash": "ABC123…" }
```

## Responses

| Status | When | Body |
|--------|------|------|
| 200 | Quorum ran (even if verdict is NO_QUORUM) | `QuorumResult` (see data-model.md) |
| 401 | Missing/invalid bearer | `{"detail": "Missing or invalid token"}` |
| 404 | Any symbol not in the selected account | `{"detail": "Position not found — refresh positions and try again"}` |
| 422 | Bad body, >4 legs, duplicate symbols, legs span >1 underlying, or unknown `account_hash` | `{"detail": …}` |
| 429 | Rate limit | slowapi default |
| 503 | Quorum not configured (FR-014) | `{"detail": "Quorum is not configured on this server"}` |
| 504 | Whole quorum exceeded 60 s (FR-012) | `{"detail": "Quorum timed out"}` |

## Invariants

- The model never receives `account_hash` or the bearer token (SC-003).
- `votes` always has exactly 5 entries in fixed seat order; `tally` always has CLOSE, HOLD, ROLL.
- `sum(t.votes for t in tally) == valid_votes`.
- `verdict` is a pure function of `votes` (FR-007).
- Nothing about the request or result is logged except the existing anonymised security events.

## Service API (`src/services/quorum_agents.py`)

```python
SEATS: tuple[Seat, ...]                       # 5 fixed seats (FR-004)
def quorum_configured() -> bool               # FR-014
def build_position_context(legs: list[PositionView]) -> PositionContext   # raises ValueError on mixed underlyings
async def run_quorum(ctx, headlines, *, model=None, seat_timeout=45.0) -> QuorumResult
```

`model` accepts a model name or an ADK `BaseLlm` instance (tests inject a fake); default `os.getenv("QUORUM_MODEL", "gemini-2.5-flash")`.

## Service API (`src/services/quorum_tally.py`)

```python
def tally_votes(votes: list[AnalystVote]) -> tuple[verdict, quorum_met, valid_votes, list[TallyEntry]]
```

## Service API (`src/services/news_feeds.py`)

```python
FEEDS: tuple[FeedSource, ...]
def parse_feed(publisher: str, content: bytes) -> list[Headline]
async def fetch_headlines(underlying: str, *, client: httpx.AsyncClient | None = None, limit: int = 30) -> list[Headline]
```
