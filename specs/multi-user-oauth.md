# SPEC: Multi-User Stateless OAuth Authentication

**Status:** Draft  
**Feature:** schwab-oauth-stateless  
**Created:** 2026-05-13

---

## Overview

Rearchitect Option Sentinel from a single-user personal tool to a stateless multi-user
web application. Any Schwab customer visits the site, clicks "Connect Schwab Account",
completes the standard OAuth consent flow, and lands on their portfolio screening view.
No user accounts, no database, no server-side session state. The access and refresh
tokens live exclusively in the user's browser sessionStorage and are sent as a Bearer
header on every API request.

---

## Goals

- Allow any Schwab account holder to authenticate without creating an account on our platform
- Keep the backend fully stateless (zero per-user persistence)
- Remove SQLite and all database dependencies entirely
- Remove schwab-py and its token management from the auth path
- Token refresh happens transparently; the browser updates its own sessionStorage

---

## Out of Scope

- User accounts, registration, or login forms
- Server-side token storage or session management
- Any database (SQLite or otherwise)
- Admin dashboards or user management
- Rate limiting per user (defer to Schwab API limits)

---

## Functional Requirements

### FR-1: OAuth Initiation Route

`GET /auth/start`

- Reads `SCHWAB_CLIENT_ID` and `SCHWAB_REDIRECT_URI` from environment variables
- Generates a cryptographically random PKCE `code_verifier` (43–128 chars, URL-safe)
- Derives `code_challenge` as BASE64URL(SHA256(code_verifier))
- Stores `code_verifier` in a short-lived server-side in-memory dict keyed by a random
  `state` param (TTL: 10 minutes, cleared after use — this is the ONLY transient server
  state and holds no user data)
- Returns an HTTP redirect to Schwab's authorization URL with params:
  `client_id`, `redirect_uri`, `response_type=code`, `scope`, `state`,
  `code_challenge`, `code_challenge_method=S256`

### FR-2: OAuth Callback Route

`GET /auth/callback`

- Receives `code` and `state` query params from Schwab's redirect
- Looks up and deletes `code_verifier` from the in-memory dict using `state`
- Returns 400 if `state` is unknown or expired
- POSTs to Schwab's token endpoint with `code`, `code_verifier`, `client_id`,
  `client_secret` (from env), `redirect_uri`, `grant_type=authorization_code`
- On success, returns JSON to the frontend:
```json
  {
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 1800
  }
```
- Frontend stores both tokens in `sessionStorage` and navigates to `/dashboard`
- Returns 502 with error detail if Schwab token exchange fails

### FR-3: Token Refresh Route

~~`POST /auth/refresh`~~ **REMOVED** (2026-05-13)

Silent token refresh is not implemented. The frontend does not attempt to refresh
expired tokens — instead, any 401 triggers immediate re-authentication (see FR-5).
The `POST /auth/refresh` route MUST NOT be implemented.

### FR-4: Authenticated Screening Routes

All existing screening/portfolio routes:

- Require `Authorization: Bearer <access_token>` header
- Extract the token and pass it directly to Schwab API calls (no lookup, no DB)
- Return 401 with `{"detail": "Missing or invalid token"}` if header is absent or malformed
- Do not validate the token themselves — a rejected call from Schwab API propagates as 401

### FR-5: Frontend Auth Flow

- Landing page shows a single "Connect Schwab Account" button
- Button calls `GET /auth/start` — browser follows the redirect to Schwab
- After Schwab redirects to `/auth/callback`, the access token is stored in
  `sessionStorage` as `schwab_access_token`
- All subsequent API calls include `Authorization: Bearer ${sessionStorage.getItem('schwab_access_token')}`
- **If any API call returns 401, the frontend calls `eraseAll()` immediately** — clears
  `sessionStorage`, `localStorage`, deletes IndexedDB — and redirects the user to the
  login page. No silent refresh. No retry. The user must re-authenticate.
- "Disconnect" button calls `eraseAll()` and returns to landing page

---

## Non-Functional Requirements

### NFR-1: No Database
Zero imports of SQLite, SQLAlchemy, or any ORM. Remove from `requirements.txt`.

### NFR-2: No schwab-py in Auth Path
The OAuth flow uses raw `httpx` calls to Schwab's token endpoint. `schwab-py` may be
retained only if it provides non-auth utilities (quote fetching etc.); its token/auth
helpers must not be used.

### NFR-3: Environment Variables Required
The following env vars must be present at startup or the app must fail fast with a clear
error message:
- `SCHWAB_CLIENT_ID`
- `SCHWAB_CLIENT_SECRET`
- `SCHWAB_REDIRECT_URI`
- `SCHWAB_AUTH_URL` (e.g. `https://api.schwabapi.com/v1/oauth/authorize`)
- `SCHWAB_TOKEN_URL` (e.g. `https://api.schwabapi.com/v1/oauth/token`)

### NFR-4: PKCE State Cleanup
In-memory PKCE state dict must evict entries older than 10 minutes to prevent unbounded
memory growth. A simple background task or eviction on access is acceptable.

### NFR-5: HTTPS Required
`SCHWAB_REDIRECT_URI` must be an HTTPS URL in production. The app itself may assume
HTTPS is terminated upstream (e.g. Fly.io proxy).

---

## Files to Change

| File | Action |
|---|---|
| `requirements.txt` | Remove `sqlite3`; ensure `httpx`, `python-dotenv` present |
| `src/auth/` | Create new module with `router.py` containing FR-1, FR-2, FR-3 routes |
| `src/main.py` | Include auth router; remove DB init; add startup env var validation |
| `src/dependencies.py` | Add `get_current_token` dependency that extracts Bearer token |
| All screening routers | Inject `get_current_token`; pass token to Schwab calls |
| `src/db/` | Delete entirely |
| `src/models/` | Remove any SQLAlchemy models; retain Pydantic response models |
| `frontend/` | Update login page, add sessionStorage token management, add refresh logic |
| `.env.example` | Update with new required vars, remove `DATABASE_URL` |

---

## Acceptance Criteria

- [ ] `GET /auth/start` redirects to Schwab authorization URL with valid PKCE params
- [ ] Completing Schwab consent flow lands on `/dashboard` with `schwab_access_token` in `sessionStorage`
- [ ] A screening API call with a valid Bearer token returns portfolio data
- [ ] A screening API call with no Bearer token returns 401
- [ ] A screening API call with an expired Bearer token returns 401 and the browser redirects to login (no silent refresh)
- [ ] App starts and fails fast with a descriptive error if any required env var is missing
- [ ] No SQLite file is created at any point during app operation
- [ ] Disconnecting clears `sessionStorage`, `localStorage`, and IndexedDB, and returns user to landing page
- [ ] Two concurrent users with different Schwab accounts see only their own portfolio data
