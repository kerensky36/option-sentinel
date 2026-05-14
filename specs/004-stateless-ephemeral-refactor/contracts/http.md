# HTTP API Contracts: Stateless Ephemeral Refactor

**Feature**: 004-stateless-ephemeral-refactor  
**Updated**: 2026-05-13 (multi-user-oauth.md extension)  
**Base URL**: `/`  
**Auth**: All routes except `/auth/*` and `/health` require `Authorization: Bearer <access_token>`.
Requests without a valid Bearer header return `401 {"detail": "Missing or invalid token"}`.
The server MUST NOT log the Authorization header value anywhere.

---

## Auth Routes

### GET /auth/login

Renders the login page with a "Connect Schwab Account" button.

**Response**: `200 OK` — HTML login page  
**Auth required**: No  
**Query params**:
| Param | Type | Notes |
|-------|------|-------|
| `error` | string (optional) | Displays error banner: `missing_params`, `invalid_state`, `state_expired`, `token_exchange_failed` |

---

### GET /auth/start

Initiates the Schwab OAuth 2.0 PKCE flow.

- Generates a cryptographically random `code_verifier` (URL-safe, 64 chars base64url → 86 chars)
- Computes `code_challenge = BASE64URL(SHA256(code_verifier))`
- Generates a random `state` string (URL-safe, 32 chars)
- Stores `{code_verifier, created_at}` in server in-memory dict keyed by `state` (TTL: 10 min)
- Evicts expired entries on each call
- Redirects browser to `SCHWAB_AUTH_URL` with query params:
  `client_id`, `redirect_uri`, `response_type=code`, `state`, `code_challenge`, `code_challenge_method=S256`

**Response**: `302 Redirect` → Schwab authorise URL  
**Auth required**: No  
**Side effects**: Writes `{state: {code_verifier, created_at}}` to in-memory PKCE store

---

### GET /auth/callback

Receives the OAuth authorisation code from Schwab, exchanges it for tokens, delivers them
to the browser via an inline `<script>` that writes to `sessionStorage`.

**Query parameters**:
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `code` | string | Yes | Auth code from Schwab |
| `state` | string | Yes | Must match an entry in the in-memory PKCE store |

**Success response**: `200 OK` — HTML page containing:
```html
<script>
  sessionStorage.setItem('schwab_access_token', '<access_token>');
  window.location.replace('/');
</script>
```

**Error responses**:
- `302 Redirect` → `/auth/login?error=missing_params` if `code` or `state` absent
- `302 Redirect` → `/auth/login?error=invalid_state` if `state` not in PKCE store
- `302 Redirect` → `/auth/login?error=state_expired` if PKCE entry older than 10 min
- `302 Redirect` → `/auth/login?error=token_exchange_failed` if Schwab token exchange fails

**Security**: Token values are written to browser sessionStorage client-side and never stored
or logged server-side. The PKCE store entry is deleted (`.pop()`) on first use — single use.

---

~~### POST /auth/refresh~~ **REMOVED** (2026-05-13)

Silent token refresh is not implemented. Any 401 received by `fetchWithAuth()` triggers
`eraseAll()` → redirect to login. The user must re-authenticate. This endpoint MUST NOT
be implemented.

---

### GET /auth/dev-login *(local dev only)*

Injects `schwab_token.json` access and refresh tokens into browser sessionStorage.
Returns `404` if `schwab_token.json` does not exist.

**Response**: `200 OK` — HTML with inline script:
```html
<script>
  sessionStorage.setItem('schwab_access_token', '<access_token>');
  window.location.replace('/');
</script>
```

**Auth required**: No  
**Production**: Returns `404` (file never exists on Cloud Run)

---

### POST /auth/logout

Renders a page that clears all browser storage and redirects to login. Server has no session
state to clear — this is a client-side-only operation triggered by the rendered script.

**Response**: `200 OK` — HTML with inline script:
```javascript
sessionStorage.clear();
localStorage.clear();
await indexedDB.deleteDatabase('option-sentinel');
window.location.replace('/auth/login');
```

**Auth required**: No

---

## Dashboard Routes

### GET /

Renders the dashboard shell. Position data is NOT included — JS loads it via Refresh button.
Thesis data is applied client-side from localStorage.

**Response**: `200 OK` — HTML dashboard shell  
**Auth guard**: Client-side; `auth.js` checks sessionStorage and redirects to `/auth/login` if no token

---

### GET /screener

Renders the screener page shell. Results loaded on demand.

**Response**: `200 OK` — HTML screener shell  
**Auth guard**: Client-side (same as above)

---

## Data Endpoints (JSON API)

### GET /api/positions/refresh

Fetches all open options positions and Greeks from Schwab; returns JSON array.

**Request headers**:
```
Authorization: Bearer <raw_access_token>
```

**Response** `200 OK` (JSON array of `PositionView`):
```json
[
  {
    "symbol": "QQQ   260618P00650000",
    "underlying_symbol": "QQQ",
    "option_type": "put",
    "strike": "650.0",
    "expiry_date": "2026-06-18",
    "quantity": -1,
    "cost": "3.20",
    "current_mark": "2.15",
    "unrealised_pnl": "105.0",
    "days_to_expiry": 36,
    "delta": -0.21,
    "gamma": 0.003,
    "theta": -0.05,
    "vega": 0.18,
    "implied_volatility": 0.22,
    "delta_source": "api",
    "gamma_source": "calculated",
    "theta_source": "calculated",
    "vega_source": "calculated",
    "iv_source": "api"
  }
]
```

**Error responses**:
- `401` — Missing or invalid Bearer token → `{"detail": "Missing or invalid token"}`
- `502` — Schwab API error

**Server behaviour**: Calls `client.get_account_numbers()` to resolve account hash dynamically.
Never logs the Authorization header value.

---

### GET /api/screener/refresh

Fetches long stock positions and computes covered call rankings; returns JSON array.

**Request headers**:
```
Authorization: Bearer <raw_access_token>
```

**Response** `200 OK` (JSON array of `ScreenerResultView`):
```json
[
  {
    "ticker": "AAPL",
    "shares": 200,
    "stock_price": 195.40,
    "iv_rank": 42.0,
    "recommended_strike": 200.0,
    "recommended_expiry": "2026-06-20",
    "bid_premium": 2.35,
    "annualised_yield": 22.1,
    "call_delta": 0.24,
    "days_to_earnings": null,
    "composite_score": 71.3,
    "recommendation_status": "recommended",
    "sort_order": 0
  }
]
```

**Error responses**:
- `401` — Missing or invalid Bearer token
- `502` — Schwab API error

**Server behaviour**: Uses `client.get_account_numbers()` to resolve the equity account dynamically;
no `SCHWAB_CC_ACCOUNT_ID` env var required.

---

## Health Check

### GET /health

Returns server health. No auth, no DB check. Used as Cloud Run liveness probe.

**Response** `200 OK`:
```json
{ "status": "ok" }
```

---

## Required Environment Variables

The app fails fast at startup if any of these are missing:

| Variable | Description |
|----------|-------------|
| `SCHWAB_CLIENT_ID` | Schwab app key (= `SCHWAB_APP_KEY` in older `.env` files) |
| `SCHWAB_CLIENT_SECRET` | Schwab app secret (= `SCHWAB_APP_SECRET`) |
| `SCHWAB_REDIRECT_URI` | OAuth callback URL — must match Schwab app registration |
| `SCHWAB_AUTH_URL` | Schwab OAuth authorise endpoint (e.g. `https://api.schwabapi.com/v1/oauth/authorize`) |
| `SCHWAB_TOKEN_URL` | Schwab token endpoint (e.g. `https://api.schwabapi.com/v1/oauth/token`) |

Optional:
| Variable | Description |
|----------|-------------|
| `RISK_FREE_RATE` | Black-Scholes risk-free rate (default: `0.045`) |

---

## Removed Endpoints

| Endpoint | Reason |
|----------|--------|
| `GET /auth/connect` | Replaced by `GET /auth/start` |
| `GET /events` (SSE) | Replaced by pull-on-demand |
| `POST /admin/*` | DB admin routes removed |
| `POST /thesis/*` | Thesis data moves to localStorage |
| `POST /positions/*` | DB write routes removed |
| `GET/POST /binary/*` | BinaryEventFlag removed |
