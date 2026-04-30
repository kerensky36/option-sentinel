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
