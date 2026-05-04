# Data Model: Stateless Ephemeral Refactor

**Feature**: 004-stateless-ephemeral-refactor
**Date**: 2026-05-03
**Note**: All server-side entities are in-memory Pydantic models. No database tables. No ORM.

---

## Token Flow Summary

```
Browser                          Cloud Run                     Schwab
  │                                  │                            │
  │  GET /auth/connect               │                            │
  ├─────────────────────────────────►│                            │
  │◄── 302 redirect to Schwab ───────┤                            │
  │                                  │                            │
  │  [user logs in at Schwab]        │                            │
  │◄── redirect /auth/callback?code= ┤ ◄── Schwab sends code ────┤
  │                                  │                            │
  │  GET /auth/callback?code=...     │                            │
  ├─────────────────────────────────►│                            │
  │                                  ├── exchange code ──────────►│
  │                                  │◄─ token dict ─────────────┤
  │◄── HTML + inline <script> ───────┤  (token never stored here) │
  │    sessionStorage.setItem(token) │                            │
  │    window.location.replace('/') │                            │
  │                                  │                            │
  │  [user clicks Refresh]           │                            │
  │  fetch('/api/positions/refresh') │                            │
  │  Authorization: Bearer <token>  │                            │
  ├─────────────────────────────────►│                            │
  │                                  ├── GET /accounts (Bearer) ─►│
  │                                  │◄─ positions JSON ──────────┤
  │◄── positions JSON ───────────────┤  (no storage, no logging)  │
  │  IndexedDB.put(positions)        │                            │
  │  render table                    │                            │
```

---

## Server-Side (In-Memory, Pydantic)

### PositionView

Represents a single open options position as returned by the Schwab API, enriched with computed Greeks. Exists only for the duration of a positions refresh request.

| Field | Type | Source | Notes |
|---|---|---|---|
| `symbol` | str | Schwab | OCC option symbol |
| `underlying_symbol` | str | Schwab | e.g. "QQQ" |
| `option_type` | Literal["call","put"] | Schwab | parsed from OCC symbol |
| `strike` | Decimal | Schwab | parsed from OCC symbol |
| `expiry_date` | date | Schwab | parsed from OCC symbol |
| `quantity` | int | Schwab | negative = short |
| `cost` | Decimal | Schwab | average price at open |
| `current_mark` | Decimal | Schwab | current market price |
| `unrealised_pnl` | Decimal | computed | (mark - cost) × qty × 100 |
| `days_to_expiry` | int | computed | expiry_date - today |
| `delta` | float \| None | Schwab or BS | |
| `gamma` | float \| None | Schwab or BS | |
| `theta` | float \| None | Schwab or BS | |
| `vega` | float \| None | Schwab or BS | |
| `implied_volatility` | float \| None | Schwab or BS | |
| `delta_source` | Literal["api","calculated"] | computed | |
| `gamma_source` | Literal["api","calculated"] | computed | |
| `theta_source` | Literal["api","calculated"] | computed | |
| `vega_source` | Literal["api","calculated"] | computed | |
| `iv_source` | Literal["api","calculated"] | computed | |

### ScreenerResultView

Represents a single covered-call recommendation for a long stock position. Exists only for the duration of a screener refresh request.

| Field | Type | Source | Notes |
|---|---|---|---|
| `ticker` | str | Schwab | stock symbol |
| `shares` | int | Schwab | quantity held |
| `stock_price` | float | Schwab | current price |
| `iv_rank` | float \| None | Schwab | 0–100 |
| `recommended_strike` | float \| None | computed | target delta 0.20–0.30 |
| `recommended_expiry` | str \| None | computed | e.g. "2026-06-20" |
| `bid_premium` | float \| None | Schwab | option bid at recommended strike |
| `annualised_yield` | float \| None | computed | (premium / stock_price) × (365 / dte) |
| `call_delta` | float \| None | Schwab | delta of recommended call |
| `days_to_earnings` | int \| None | Schwab | None if unknown |
| `composite_score` | float | computed | weighted rank signal |
| `recommendation_status` | Literal["recommended","suppressed","insufficient_data"] | computed | suppressed within 7d of earnings |
| `sort_order` | int | computed | rank within results list |

### Session (Cookie)

Stored as a signed, encrypted cookie via Starlette `SessionMiddleware`. Not a Pydantic model — a plain dict serialised by itsdangerous.

| Key | Type | Notes |
|---|---|---|
| `token` | dict | Raw token dict from schwab-py (access_token, refresh_token, expiry fields) |

---

## Client-Side (Browser localStorage)

The server has no knowledge of these structures. They are defined here as a contract for the JavaScript layer.

### LocalThesisGroup

```json
{
  "id": "uuid-string",
  "name": "string",
  "template_type": "credit_spread | covered_call | protective_put | custom",
  "description": "string | null",
  "alignment_rating": "strong | moderate | weak | misaligned",
  "status": "active | paused | closed"
}
```

Stored as: `localStorage.setItem("thesis_groups", JSON.stringify(ThesisGroup[]))`

### LocalThesisAssignment

```json
{
  "symbol": "OCC-option-symbol-string",
  "thesis_group_id": "uuid-string | null"
}
```

Stored as: `localStorage.setItem("thesis_assignments", JSON.stringify(ThesisAssignment[]))`

### LocalSpreadDefinition

```json
{
  "symbol": "OCC-option-symbol-string",
  "net_credit_received": "decimal-string",
  "maximum_profit": "decimal-string",
  "maximum_loss": "decimal-string",
  "strategy_type": "bull_put | bear_call | iron_condor | custom"
}
```

Stored as: `localStorage.setItem("spread_definitions", JSON.stringify(SpreadDefinition[]))`

### LocalExitGoal

```json
{
  "symbol": "OCC-option-symbol-string",
  "profit_target_pct": "number | null",
  "dte_threshold": "number | null",
  "underlying_price_target": "decimal-string | null",
  "price_target_direction": "above | below | null"
}
```

Stored as: `localStorage.setItem("exit_goals", JSON.stringify(ExitGoal[]))`

---

## Entities Removed

The following DB tables are deleted with no replacement:

| Table | Disposition |
|---|---|
| `position` | → `PositionView` in-memory |
| `greeks` | → fields on `PositionView` |
| `thesis` | → `LocalThesisGroup` in localStorage |
| `spread` | → `LocalSpreadDefinition` in localStorage |
| `exit_goal` | → `LocalExitGoal` in localStorage |
| `alert` | → removed; alerts deferred |
| `auth_token` | → session cookie |
| `binary_event_flag` | → removed |
| `thesis_health_snapshot` | → removed; trend data deferred |
| `screener_result` | → `ScreenerResultView` in-memory |
