# Data Model: Option Sentinel

**Date**: 2026-04-29 | **Branch**: `001-option-sentinel-monitor`

## Entity Relationship Overview

```
Thesis (1) ──────< Position (N)
                      │
              ┌───────┼───────┐
              │       │       │
           Greeks  ExitGoal  Spread (N:1)
              │
           Alert (N) ─── position_id

AuthToken      (singleton)
BinaryEventFlag (singleton)
```

---

## Position

Represents a single open options leg at a brokerage account.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `schwab_account_id` | str(20) | NOT NULL | From Schwab API |
| `symbol` | str(21) | NOT NULL | OCC symbol e.g. `SPY 240119C00520000` |
| `underlying_symbol` | str(10) | NOT NULL | e.g. `SPY` |
| `option_type` | enum | NOT NULL | `call` \| `put` |
| `strike` | Decimal(10,2) | NOT NULL | |
| `expiry_date` | date | NOT NULL | |
| `quantity` | int | NOT NULL | Positive = long, negative = short |
| `opening_credit_debit` | Decimal(10,4) | nullable | Negative = debit, positive = credit |
| `current_mark` | Decimal(10,4) | nullable | Latest from Schwab |
| `unrealised_pnl` | Decimal(10,4) | nullable | Computed: `(current_mark - opening_credit_debit) * quantity * 100` |
| `days_to_expiry` | int | nullable | Computed from `expiry_date` |
| `status` | enum | NOT NULL | `open` \| `closed` |
| `thesis_id` | UUID | nullable FK → Thesis | NULL = Unassigned group |
| `spread_id` | UUID | nullable FK → Spread | NULL = standalone leg |
| `last_updated` | datetime | NOT NULL | Last Schwab poll timestamp |
| `created_at` | datetime | NOT NULL | |

**State transitions**: `open` → `closed` (when Schwab no longer returns position).
**Uniqueness**: (`symbol`, `schwab_account_id`, `status='open'`) must be unique.

---

## Greeks

Option sensitivity values for a Position, one row per position.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `position_id` | UUID | NOT NULL, FK → Position, UNIQUE | 1:1 |
| `delta` | float | nullable | |
| `delta_source` | enum | NOT NULL | `api` \| `calculated` \| `unavailable` |
| `gamma` | float | nullable | |
| `gamma_source` | enum | NOT NULL | `api` \| `calculated` \| `unavailable` |
| `theta` | float | nullable | Per-day decay |
| `theta_source` | enum | NOT NULL | `api` \| `calculated` \| `unavailable` |
| `vega` | float | nullable | Per 1% IV change |
| `vega_source` | enum | NOT NULL | `api` \| `calculated` \| `unavailable` |
| `implied_volatility` | float | nullable | As a decimal (e.g. 0.32 = 32%) |
| `iv_source` | enum | NOT NULL | `api` \| `calculated` \| `unavailable` |
| `computed_at` | datetime | NOT NULL | Timestamp of last update |

---

## ExitGoal

Exit targets and computed proximity score for a Position, one row per position.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `position_id` | UUID | NOT NULL, FK → Position, UNIQUE | 1:1 |
| `profit_target_pct` | float | nullable | e.g. 50.0 = exit at 50% of max profit |
| `dte_threshold` | int | nullable | e.g. 21 = exit when DTE ≤ 21 |
| `underlying_price_target` | Decimal(10,2) | nullable | Underlying price trigger |
| `price_target_direction` | enum | nullable | `above` \| `below` |
| `exit_proximity_score` | int | NOT NULL, default 0 | 0–100; 100 = any goal met |
| `last_scored_at` | datetime | nullable | Timestamp of last score computation |

**Scoring rule**: Score = `max(pnl_score, dte_score, price_score)` where each dimension
maps linearly from 0 (no progress) to 100 (threshold met). If no goal is defined,
score stays at 0 and is displayed as `—`.

---

## Thesis

A named grouping of positions sharing a market thesis.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `name` | str(100) | NOT NULL | Trader-assigned label |
| `template_type` | enum | NOT NULL | `iv_crush` \| `earnings_fade` \| `directional_momentum` \| `mean_reversion` \| `custom` |
| `description` | text | nullable | Free-text notes |
| `alignment_rating` | enum | NOT NULL, default `unrated` | `aligned` \| `partially_aligned` \| `misaligned` \| `unrated` |
| `status` | enum | NOT NULL, default `active` | `active` \| `closed` |
| `created_at` | datetime | NOT NULL | |
| `updated_at` | datetime | NOT NULL | |

**Deletion rule**: Deleting a Thesis sets `thesis_id = NULL` on all member Positions
(move to Unassigned); no cascade delete.

---

## Spread

Groups related Position legs into a named strategy.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `name` | str(100) | NOT NULL | e.g. `SPY 520/515 Put Credit Spread` |
| `strategy_type` | enum | NOT NULL | `put_credit_spread` \| `call_credit_spread` \| `iron_condor` \| `vertical` \| `custom` |
| `net_credit_received` | Decimal(10,4) | NOT NULL | Positive = credit |
| `maximum_profit` | Decimal(10,4) | NOT NULL | = `net_credit_received` for credit spreads |
| `maximum_loss` | Decimal(10,4) | NOT NULL | |
| `created_at` | datetime | NOT NULL | |

---

## Alert

A triggered notification event.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `alert_type` | enum | NOT NULL | `profit_target` \| `expiry_14d` \| `expiry_7d` \| `expiry_3d` \| `binary_event_exit` |
| `position_id` | UUID | nullable FK → Position | |
| `spread_id` | UUID | nullable FK → Spread | |
| `severity` | enum | NOT NULL | `info` \| `warning` \| `critical` |
| `trigger_timestamp` | datetime | NOT NULL | |
| `delivery_status` | enum | NOT NULL, default `pending` | `pending` \| `delivered` \| `failed` \| `max_retries` |
| `retry_count` | int | NOT NULL, default 0 | Max 3 |
| `acknowledged_at` | datetime | nullable | |

**Idempotency**: `(alert_type, position_id, trigger_timestamp::date)` uniqueness
ensures no double-firing per day per position per type.

---

## AuthToken

Singleton row holding Schwab OAuth token state.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | int | PK, default 1 | Always 1 (singleton) |
| `access_token` | text | NOT NULL | Stored encrypted at rest |
| `access_expiry` | datetime | NOT NULL | |
| `refresh_token` | text | NOT NULL | Stored encrypted at rest |
| `refresh_expiry` | datetime | NOT NULL | 7-day TTL |
| `re_auth_required` | bool | NOT NULL, default false | True when refresh_expiry < now + 24h |
| `last_refreshed` | datetime | NOT NULL | |

---

## BinaryEventFlag

Singleton row tracking the trader's manual full-exit signal.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | int | PK, default 1 | Always 1 (singleton) |
| `is_active` | bool | NOT NULL, default false | |
| `activated_at` | datetime | nullable | |
| `cleared_at` | datetime | nullable | |
