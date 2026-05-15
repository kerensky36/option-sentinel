# Data Model: Stateless Ephemeral Refactor

**Feature**: 004-stateless-ephemeral-refactor  
**Date**: 2026-05-03 (updated 2026-05-13 for multi-user-oauth.md extension)  
**Note**: All server-side entities are in-memory Pydantic models. No database tables. No ORM.

---

## Token Flow Summary

```
Browser                          Cloud Run                     Schwab
  │                                  │                            │
  │  GET /auth/start                 │                            │
  ├─────────────────────────────────►│  generate PKCE state        │
  │◄── 302 redirect to Schwab ───────┤  store in-memory dict       │
  │                                  │                            │
  │  [user logs in at Schwab]        │                            │
  │◄── redirect /auth/callback?code= ┤◄── Schwab sends code ─────┤
  │                                  │                            │
  │  GET /auth/callback?code=...     │                            │
  ├─────────────────────────────────►│  lookup + delete PKCE state │
  │                                  ├── POST token endpoint ────►│
  │                                  │◄── {access_token, ...} ───┤
  │◄── HTML + inline <script> ───────┤  (token never stored here)  │
  │    sessionStorage['schwab_access_token'] = access_token        │
  │    window.location.replace('/')  │                            │
  │                                  │                            │
  │  [user clicks Refresh]           │                            │
  │  fetchWithAuth('/api/positions/refresh')                       │
  │  Authorization: Bearer <access_token>                         │
  ├─────────────────────────────────►│  build_schwab_client(token) │
  │                                  ├── get_account_numbers() ──►│
  │                                  │◄── [{"hashValue": ...}] ──┤
  │                                  ├── get_account(hash) ──────►│
  │                                  │◄── positions JSON ─────────┤
  │◄── positions JSON ───────────────┤  (no storage, no logging)  │
  │  IndexedDB.put(positions)        │                            │
  │  render table                    │                            │
  │                                  │                            │
  │  [401 received mid-session]      │                            │
  │  fetchWithAuth → eraseAll()      │                            │
  │  sessionStorage cleared          │                            │
  │  IndexedDB deleted               │                            │
  │  window.location → /auth/login   │                            │
```

---

## Server-Side (In-Memory, Pydantic)

### PositionView

Single open options position enriched with computed Greeks. Exists only during a positions refresh request.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
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

Covered-call recommendation for a long stock position. Exists only during a screener refresh request.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `ticker` | str | Schwab | stock symbol |
| `shares` | int | Schwab | quantity held |
| `stock_price` | float | Schwab | current price |
| `iv_rank` | float \| None | Schwab | 0–100 proxy |
| `recommended_strike` | float \| None | computed | target delta 0.20–0.30 |
| `recommended_expiry` | str \| None | computed | e.g. "2026-06-20" |
| `bid_premium` | float \| None | Schwab | option bid at recommended strike |
| `annualised_yield` | float \| None | computed | (premium / stock_price) × (365 / dte) |
| `call_delta` | float \| None | Schwab | delta of recommended call |
| `days_to_earnings` | int \| None | Schwab | None if unknown |
| `composite_score` | float | computed | weighted rank signal |
| `recommendation_status` | Literal["recommended","suppressed","insufficient_data"] | computed | suppressed within 7d of earnings |
| `sort_order` | int | computed | rank within results list |

### PKCE State (In-Memory Dict — NOT Pydantic)

Held in `src/auth/router.py` module-level `_pkce_store: dict[str, dict]`. Each entry lives for at most 10 minutes and is deleted on first use.

| Key | Type | Notes |
|-----|------|-------|
| `code_verifier` | str | URL-safe random string, 64 chars (86 after base64url) |
| `created_at` | float | `time.time()` at creation; entries older than 600s are invalid |

**Dict key**: random URL-safe `state` string (32 chars). Passed to Schwab and echoed back in the callback.

---

## Client-Side (Browser)

### sessionStorage — Token (string)

| Key | Type | Notes |
|-----|------|-------|
| `schwab_access_token` | string | Raw Schwab access token (JWT). Written by `/auth/callback` inline script. Never sent to server log. Expires ~30 min after issue. |

On 401 from any API call: `eraseAll()` is called → sessionStorage cleared → redirect to login.
Cleared by: tab close, `sessionStorage.clear()`, `eraseAll()`.

`schwab_refresh_token` is **not stored**. The browser does not perform silent refresh.

### localStorage — User Metadata

#### LocalThesisGroup

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

#### LocalThesisAssignment

```json
{
  "symbol": "OCC-option-symbol-string",
  "thesis_group_id": "uuid-string | null"
}
```

Stored as: `localStorage.setItem("thesis_assignments", JSON.stringify(ThesisAssignment[]))`

#### LocalSpreadDefinition

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

#### LocalExitGoal

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

### IndexedDB — Position Cache (`option-sentinel` database)

| Store | Key | Value |
|-------|-----|-------|
| `positions` | `"latest"` | `{positions: PositionView[], savedAt: ISO8601 string}` |

Written after each successful `/api/positions/refresh`. Read on page load to render immediately.
Deleted by `eraseAll()` (`indexedDB.deleteDatabase('option-sentinel')`).

---

## Entities Removed

| Table | Disposition |
|-------|-------------|
| `position` | → `PositionView` in-memory |
| `greeks` | → fields on `PositionView` |
| `thesis` | → `LocalThesisGroup` in localStorage |
| `spread` | → `LocalSpreadDefinition` in localStorage |
| `exit_goal` | → `LocalExitGoal` in localStorage |
| `alert` | → removed; alerts deferred |
| `auth_token` | → `schwab_access_token` / `schwab_refresh_token` in sessionStorage |
| `binary_event_flag` | → removed |
| `thesis_health_snapshot` | → removed; trend data deferred |
| `screener_result` | → `ScreenerResultView` in-memory |
