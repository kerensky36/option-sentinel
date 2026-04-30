# option-sentinel — AI Context Map

> **Stack:** fastapi | sqlalchemy | unknown | python

> 4 routes | 8 models | 0 components | 12 lib files | 13 env vars | 0 middleware | 33% test coverage
> **Token savings:** this file is ~1,600 tokens. Without it, AI exploration would cost ~14,000 tokens. **Saves ~12,300 tokens per conversation.**
> **Last scanned:** 2026-04-30 03:56 — re-run after significant changes

---

# Routes

- `GET` `/` params() [auth, db] ✓
- `GET` `/health` params() [auth, db] ✓
- `GET` `/positions` params() [auth, db]
- `GET` `/sse` params() [auth, queue]

---

# Schema

### Thesis
- id: String (pk, default)
- name: String
- template_type: Enum
- description: Text (nullable)
- alignment_rating: Enum (default)
- status: Enum (default)
- created_at: DateTime (default)
- updated_at: DateTime (default)
- _relations_: positions: Position

### Spread
- id: String (pk, default)
- name: String
- strategy_type: Enum
- net_credit_received: Numeric
- maximum_profit: Numeric
- maximum_loss: Numeric
- created_at: DateTime (default)
- _relations_: positions: Position, alerts: Alert

### Position
- id: String (pk, default)
- schwab_account_id: String
- symbol: String
- underlying_symbol: String
- option_type: Enum
- strike: Numeric
- expiry_date: Date
- quantity: Integer
- opening_credit_debit: Numeric (nullable)
- current_mark: Numeric (nullable)
- unrealised_pnl: Numeric (nullable)
- days_to_expiry: Integer (nullable)
- status: Enum (default)
- thesis_id: String (fk, nullable)
- spread_id: String (fk, nullable)
- last_updated: DateTime (default)
- created_at: DateTime (default)
- _relations_: thesis: Thesis, spread: Spread, greeks: Greeks, exit_goal: ExitGoal, alerts: Alert

### Greeks
- id: String (pk, default)
- position_id: String (fk, unique)
- delta: Float (nullable)
- delta_source: Enum
- gamma: Float (nullable)
- gamma_source: Enum
- theta: Float (nullable)
- theta_source: Enum
- vega: Float (nullable)
- vega_source: Enum
- implied_volatility: Float (nullable)
- iv_source: Enum
- computed_at: DateTime (default)
- _relations_: position: Position

### ExitGoal
- id: String (pk, default)
- position_id: String (fk, unique)
- profit_target_pct: Float (nullable)
- dte_threshold: Integer (nullable)
- underlying_price_target: Numeric (nullable)
- price_target_direction: Enum (nullable)
- exit_proximity_score: Integer (default)
- last_scored_at: DateTime (nullable)
- _relations_: position: Position

### Alert
- id: String (pk, default)
- alert_type: Enum
- position_id: String (fk, nullable)
- spread_id: String (fk, nullable)
- severity: Enum
- trigger_timestamp: DateTime
- delivery_status: Enum (default)
- retry_count: Integer (default)
- acknowledged_at: DateTime (nullable)
- _relations_: position: Position, spread: Spread

### AuthToken
- id: Integer (pk, default)
- access_token: Text
- access_expiry: DateTime
- refresh_token: Text
- refresh_expiry: DateTime
- re_auth_required: Boolean (default)
- last_refreshed: DateTime

### BinaryEventFlag
- id: Integer (pk, default)
- is_active: Boolean (default)
- activated_at: DateTime (nullable)
- cleared_at: DateTime (nullable)

---

# Libraries

- `src/api/deps.py` — function get_session: () -> AsyncGenerator[AsyncSession, None]
- `src/api/main.py` — function create_app: () -> FastAPI, function lifespan: (app)
- `src/auth/schwab_oauth.py` — function reset_client: () -> None, function get_schwab_client: () -> schwab.client.AsyncClient
- `src/auth/token_store.py`
  - function get_auth_token: (session) -> AuthToken | None
  - function save_auth_token: (session, access_token, access_expiry, refresh_token, refresh_expiry) -> AuthToken
  - function get_decrypted_tokens: (session) -> tuple[str, str] | None
  - function check_and_update_re_auth: (session) -> bool
- `src/data/database.py` — function get_db: () -> AsyncGenerator[AsyncSession, None]
- `src/data/migrations/env.py`
  - function run_migrations_offline: () -> None
  - function do_run_migrations: (connection) -> None
  - function run_migrations_online: () -> None
  - function run_async_migrations: () -> None
- `src/data/migrations/versions/5f53c99463d7_initial_schema.py` — function upgrade: () -> None, function downgrade: () -> None
- `src/data/models.py`
  - class Base
  - class OptionType
  - class PositionStatus
  - class SourceEnum
  - class PriceTargetDirection
  - class ThesisTemplateType
  - _...14 more_
- `src/services/bs_calculator.py`
  - function bs_greeks: (S, K, T, r, sigma, option_type) -> BSGreeks
  - function implied_volatility: (S, K, T, r, option_price, option_type) -> float | None
  - class BSGreeks
- `src/services/greeks_service.py` — function build_greeks: (position, raw) -> dict
- `src/services/poll_scheduler.py`
  - function get_scheduler: () -> AsyncIOScheduler | None
  - function start_scheduler: () -> None
  - function stop_scheduler: () -> None
- `src/services/schwab_client.py` — function sync_positions_and_greeks: (session, schwab_client) -> None

---

# Config

## Environment Variables

- `ALERT_RECIPIENT` (has default) — .env.example
- `DATABASE_URL` (has default) — .env.example
- `RISK_FREE_RATE` (has default) — .env.example
- `SCHWAB_ACCOUNT_ID` (has default) — .env.example
- `SCHWAB_APP_KEY` (has default) — .env.example
- `SCHWAB_APP_SECRET` (has default) — .env.example
- `SCHWAB_CALLBACK_URL` (has default) — .env.example
- `SCHWAB_TOKEN_PATH` **required** — src/auth/schwab_oauth.py
- `SECRET_KEY` (has default) — .env.example
- `SMTP_HOST` (has default) — .env.example
- `SMTP_PASSWORD` (has default) — .env.example
- `SMTP_PORT` (has default) — .env.example
- `SMTP_USERNAME` (has default) — .env.example

## Config Files

- `.env.example`

---

# Test Coverage

> **33%** of routes and models are covered by tests
> 8 test files found

## Covered Routes

- GET:/
- GET:/health

## Covered Models

- Position
- Greeks

---

_Generated by [codesight](https://github.com/Houseofmvps/codesight) — see your codebase clearly_