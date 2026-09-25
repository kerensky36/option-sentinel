# Data Model: Macro News Voting Quorum

All models are in-memory Pydantic models in `src/data/models.py`, living only for one request (Constitution I).

## QuorumRequest (request body)

| Field | Type | Rules |
|-------|------|-------|
| `symbols` | `list[str]` | 1–4 items, each 1–64 chars, unique |
| `account_hash` | `str \| None` | ≤ 256 chars; validated against the token by `fetch_positions_and_greeks` |

## PositionLegContext (sent to the model)

`underlying_symbol, option_type, strike, expiry_date, days_to_expiry, quantity, cost, current_mark, unrealised_pnl, delta, gamma, theta, vega, implied_volatility, underlying_price` — exactly the FR-011 list. **Not** included: `symbol` (OCC symbol is public but redundant), any account field, any `_source` flag.

## PositionContext

| Field | Type |
|-------|------|
| `underlying_symbol` | `str` (shared by all legs, else 422) |
| `legs` | `list[PositionLegContext]` (1–4) |
| `net_unrealised_pnl` | `Decimal` |
| `min_days_to_expiry` | `int` |

## Headline

| Field | Type |
|-------|------|
| `publisher` | `Literal["CNBC", "Yahoo Finance", "Bloomberg"]` |
| `title` | `str` (≤ 300) |
| `link` | `str` (http/https only, else dropped) |
| `published` | `datetime \| None` (UTC) |
| `summary` | `str` (≤ 400, HTML stripped) |

## AnalystBallot (ADK `output_schema` for each seat)

| Field | Type | Rules |
|-------|------|-------|
| `action` | `Literal["CLOSE","HOLD","ROLL"]` | required |
| `confidence` | `float` | 0 ≤ x ≤ 1 |
| `rationale` | `str` | truncated to 600 chars |
| `roll_direction` | `Literal["out","up_and_out","down_and_out"] \| None` | required when `action == "ROLL"`, forced `None` otherwise |

## AnalystVote (returned to client)

`seat` (id), `lens` (display name), `action` (`CLOSE|HOLD|ROLL|null` — null = abstained), `confidence`, `rationale`, `roll_direction`, `abstained: bool`.

## TallyEntry

`action`, `votes: int`, `mean_confidence: float | None`.

## QuorumResult

| Field | Type |
|-------|------|
| `verdict` | `Literal["CLOSE","HOLD","ROLL","NO_CONSENSUS","NO_QUORUM"]` |
| `quorum_met` | `bool` |
| `seats` | `int` (always 5) |
| `valid_votes` | `int` |
| `tally` | `list[TallyEntry]` — always CLOSE, HOLD, ROLL in that order |
| `votes` | `list[AnalystVote]` — seat order |
| `macro_brief` | `str \| None` |
| `headlines` | `list[Headline]` |
| `underlying_symbol` | `str` |
| `model` | `str` |
| `generated_at` | `datetime` (UTC) |
| `disclaimer` | `str` (fixed text, FR-017) |

## Tally rule (FR-007)

```
valid = [v for v in votes if not v.abstained]
quorum_met = len(valid) >= 3
counts = Counter(v.action for v in valid)
if not quorum_met: verdict = NO_QUORUM
elif max(counts) >= 3: verdict = argmax(counts)   # at most one action can reach 3 of 5
else: verdict = NO_CONSENSUS
```
