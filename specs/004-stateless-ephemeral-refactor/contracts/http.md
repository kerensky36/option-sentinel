# HTTP API Contracts: Stateless Ephemeral Refactor

**Feature**: 004-stateless-ephemeral-refactor
**Date**: 2026-05-03
**Base URL**: `/`
**Auth**: All routes except `/auth/*` and `/health` require a valid session cookie. Requests without one redirect to `/auth/login`.

---

## Auth Routes

### GET /auth/login

Renders the login page with a "Connect Schwab Account" button.

**Response**: `200 OK` — HTML login page
**Session required**: No
**Redirect if authenticated**: Yes → `/`

---

### GET /auth/connect

Initiates the Schwab OAuth 2.0 flow. Generates a PKCE code verifier, stores it in the session, and redirects the user to Schwab's authorise URL.

**Response**: `302 Redirect` → Schwab authorise URL
**Session required**: No
**Side effects**: Writes `oauth_state` and `code_verifier` to session

---

### GET /auth/callback

Receives the OAuth authorisation code from Schwab, exchanges it for access + refresh tokens, stores tokens in the session, and redirects to the dashboard.

**Query parameters**:
| Param | Type | Required | Notes |
|---|---|---|---|
| `code` | string | Yes | Auth code from Schwab |
| `state` | string | Yes | CSRF state token |

**Response**:
- `302 Redirect` → `/` on success
- `302 Redirect` → `/auth/login?error=auth_failed` on failure

**Session written**: `{"token": <schwab token dict>}`

---

### POST /auth/logout

Clears the session cookie and redirects to the login page.

**Response**: `302 Redirect` → `/auth/login`
**Session required**: Yes (no-op if not authenticated)

---

## Dashboard Routes

### GET /

Renders the dashboard shell. Position data is NOT included in the initial render — the page loads empty and JS/HTMX triggers a refresh. Thesis data is applied client-side from localStorage.

**Response**: `200 OK` — HTML dashboard shell
**Session required**: Yes

---

### GET /screener

Renders the screener page shell. Results are loaded on demand via the refresh button.

**Response**: `200 OK` — HTML screener shell
**Session required**: Yes

---

## Data Endpoints (HTMX partials)

### GET /api/positions/refresh

Fetches all open options positions and Greeks from Schwab, computes derived fields, and returns an HTML partial for HTMX to swap into the positions table.

**Response**: `200 OK` — HTML partial (`partials/positions_table.html`)
**Session required**: Yes

**Rendered fields per row**:
- symbol, underlying, option type, strike, expiry, quantity
- current mark, unrealised P&L, days to expiry
- delta (source), gamma (source), theta (source), vega (source), IV (source)
- thesis group name (populated client-side via JS from localStorage after swap)

**Error responses**:
- `401` → session expired, redirect to login
- `503` → Schwab API unavailable, return error partial with retry button

---

### GET /api/screener/refresh

Fetches long stock positions from the screener Schwab account, computes covered call rankings, and returns an HTML partial.

**Response**: `200 OK` — HTML partial (`partials/screener_table.html`)
**Session required**: Yes

**Rendered fields per row**:
- ticker, shares, stock price, IV rank
- recommended strike, recommended expiry
- bid premium, annualised yield, call delta
- days to earnings, composite score, recommendation status

**Error responses**:
- `401` → session expired, redirect to login
- `503` → Schwab API unavailable, return error partial

---

## Health Check

### GET /health

Returns server health. No DB check (DB is removed). Used by Cloud Run as the liveness probe.

**Response**:
```json
{
  "status": "ok"
}
```

**Session required**: No

---

## Removed Endpoints

The following endpoints are deleted with this feature:

| Endpoint | Reason |
|---|---|
| `GET /events` (SSE) | Replaced by pull-on-demand |
| `POST /admin/*` | DB admin routes removed |
| `POST /thesis/*` | Thesis data moves to localStorage |
| `POST /positions/*` | DB write routes removed |
| `GET/POST /binary/*` | BinaryEventFlag removed |
