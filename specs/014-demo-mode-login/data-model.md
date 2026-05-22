# Data Model: Demo Mode Login (014)

## Entities

### DemoSession (sessionStorage keys)

Stored in browser `sessionStorage` (tab-scoped, cleared on tab close).

| Key | Type | Values | Purpose |
|-----|------|--------|---------|
| `demo_mode` | string | `'true'` | Marks the tab as a demo session. Absent in real Schwab sessions. |
| `schwab_selected_account` | string | `'demo-spreads-0001'` or `'demo-equity-0002'` | Reuses existing account picker key — demo hashes are prefixed `demo-` to prevent collision with real Schwab hashes |

No new sessionStorage keys are introduced; `demo_mode` is the only addition.

---

### DemoAccount (client-side constant in `demo_data.js`)

Represents one fake Schwab account returned by the mocked `/api/accounts` endpoint.
Matches the shape returned by `src/api/routes/accounts.py`.

```js
{
  hashValue: string,      // synthetic, prefixed 'demo-' — cannot collide with real Schwab hashes
  accountNumber: string,  // display label for the account picker
}
```

Instances:
| hashValue | accountNumber | Content |
|-----------|--------------|---------|
| `demo-spreads-0001` | `DEMO — Options Spreads` | 6 option legs: AAPL put spread, SPY iron condor, TSLA call spread |
| `demo-equity-0002` | `DEMO — Equities & ETFs` | 2 open covered calls + 4 equity holdings for screener |

---

### DemoPosition (option) (client-side constant in `demo_data.js`)

Matches `PositionView.model_dump(mode='json')` from `src/data/models.py`.
All fields present; no nulls.

```js
{
  symbol: string,              // OCC option symbol e.g. "AAPL 250718P00195000"
  underlying_symbol: string,   // e.g. "AAPL"
  option_type: "call" | "put",
  strike: number,
  expiry_date: string,         // ISO date string "YYYY-MM-DD"
  quantity: number,            // negative = short, positive = long
  cost: number,                // per-share cost basis (negative for short)
  current_mark: number,        // current mid-market price (negative for short)
  unrealised_pnl: number,      // total P&L in USD
  days_to_expiry: number,
  delta: number,
  gamma: number,
  theta: number,
  vega: number,
  implied_volatility: number,
  delta_source: "calculated",
  gamma_source: "calculated",
  theta_source: "calculated",
  vega_source: "calculated",
  iv_source: "calculated",
}
```

---

### DemoScreenerResult (client-side constant in `demo_data.js`)

Matches `ScreenerResultView.model_dump(mode='json')` from `src/data/models.py`.

```js
{
  ticker: string,
  shares: number,
  contracts: number,
  stock_price: number,
  iv_rank: number | null,
  recommended_strike: number | null,
  recommended_expiry: string | null,    // ISO date string
  bid_premium: number | null,
  annualised_yield: number | null,
  call_delta: number | null,
  days_to_earnings: number | null,
  composite_score: number,
  recommendation_status: "recommended" | "suppressed" | "insufficient_data",
  sort_order: number,
  candidates: [],
}
```

---

## URL Interception Map

`demoResponse(url)` in `demo_data.js` handles these patterns (matched by `url.startsWith()`):

| URL Pattern | Account required? | Returns |
|------------|------------------|---------|
| `/api/accounts` | No | Array of 2 `DemoAccount` objects |
| `/api/positions/refresh` | Yes (via `?account_hash=…`) | `DEMO_POSITIONS_SPREADS` or `DEMO_POSITIONS_EQUITY` |
| `/api/screener/refresh` | Yes (via `?account_hash=…`) | `[]` for spreads account; `DEMO_SCREENER_RESULTS` for equity account |

Any other URL called via `fetchWithAuth` in demo mode returns `{ detail: "Demo mode: endpoint not available" }` with status 200 (so the UI degrades gracefully rather than triggering `eraseAll`).

---

## State Transitions

```
[Login Page]
  │
  ├─ "Connect Schwab" → OAuth flow → real session (no demo keys set)
  │
  └─ "Try Demo" → GET /auth/demo-login
                    → sets sessionStorage['demo_mode'] = 'true'
                    → window.location.replace('/')
                    → [Dashboard — DEMO MODE]
                         │
                         ├─ Account Picker: "DEMO — Options Spreads" / "DEMO — Equities & ETFs"
                         │     └─ sets sessionStorage['schwab_selected_account'] = demo hash
                         │
                         └─ Logout / tab close
                               → sessionStorage cleared (tab close automatic;
                                 logout calls eraseAll() which calls sessionStorage.clear())
                               → [Login Page] — no demo artefacts remain
```

---

## Collision Prevention

Real Schwab account hashes are opaque alphanumeric strings assigned by Schwab. Demo hashes
use the `demo-` prefix, which is not a valid Schwab hash format. This guarantees:

1. A demo hash cannot be accepted by any Schwab API endpoint
2. A real hash cannot accidentally match a demo hash in `demoResponse()`
3. The `isDemoMode()` check (not hash inspection) is the authoritative gate — no logic
   depends on the hash prefix alone
