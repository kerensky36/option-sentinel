# Research: Stateless Ephemeral Refactor

**Feature**: 004-stateless-ephemeral-refactor  
**Phase**: 0 — Technology decisions  
**Date**: 2026-05-03 (updated 2026-05-13 for multi-user-oauth.md extension)

---

## Decision 1: Schwab OAuth web flow strategy

**Decision**: Use `schwab-py`'s `client_from_access_functions()` with bearer-token-in-sessionStorage.

**Rationale**: `schwab-py >= 1.5` exposes `schwab.auth.client_from_access_functions(api_key, app_secret, token_read_func, token_write_func, asyncio=True)`. The `token_read_func` must return the full outer wrapper: `{"creation_timestamp": int, "token": {...}}`. The inner `token` dict requires at minimum `access_token` (and optionally `token_type`). The auth path uses raw `httpx` calls directly to Schwab's token endpoint (PKCE + client credentials) — no schwab-py in the auth path per `multi-user-oauth.md` NFR-2.

**Token format details** (traced from schwab-py 1.5 source):
- `token_read_func()` return value is passed to `TokenMetadata.from_loaded_token()` which asserts `creation_timestamp` at the top level
- Inner dict is passed as `token=` to authlib's `AsyncOAuth2Client`
- `access_token` is required (KeyError if absent)
- `token_type` optional (defaults to `bearer`)
- If `expires_at` / `expires_in` are **omitted**, `is_expired()` returns `None` — auto-refresh is **never triggered** (safe for our use case where the browser handles refresh via `POST /auth/refresh`)
- If `expires_at` is present and `expires_at - 300 < time.time()`, auto-refresh fires — avoid by omitting or setting far in the future

**Minimal safe inner dict for `build_schwab_client(access_token)`**:
```python
{
    "access_token": raw_access_token,
    "token_type": "Bearer",
}
```

**Alternatives considered**:
- `authlib` + direct Schwab client construction — avoids schwab-py but duplicates the full options/positions API surface
- File-based token (`client_from_token_file`) — reintroduces persistence, incompatible with Cloud Run
- Raw `httpx` calls for all Schwab API endpoints — correct approach but requires reimplementing the full screener and positions logic; disproportionate effort given schwab-py already wraps this

---

## Decision 2: PKCE state storage — in-memory dict (replaces signed cookie)

**Decision**: In-memory Python dict keyed by random `state` string, TTL 10 minutes, evicted on access.

**Rationale**: Replaces the `itsdangerous` signed cookie approach from the original Phase 1 design. The CSRF protection is equivalent: the `state` param is a CSRF token; an attacker cannot inject a matching state into a victim's browser. The in-memory approach drops the `OAUTH_STATE_SECRET` dependency and the `itsdangerous` library.

**Security analysis**:
- Cookie approach: state in HttpOnly SameSite=Lax cookie; forgery requires `OAUTH_STATE_SECRET`
- In-memory approach: state in server dict; an attacker cannot force the victim's callback to present a specific state. CSRF surface identical in practice.
- **Critical constraint**: Only safe on `max-instances=1` Cloud Run. On multi-instance autoscaling, a `/start` hitting instance A and `/callback` hitting instance B would find the PKCE dict empty. The Cloud Run deployment MUST specify `--max-instances=1`.

**Eviction strategy**: Check timestamp on lookup (`time.time() - entry["created_at"] > 600`). Expired entries also swept on each `/auth/start` call. No background thread needed.

**Alternatives considered**:
- `itsdangerous` signed cookie — more portable (survives restarts, scales) but adds a library dependency and requires `OAUTH_STATE_SECRET` env var
- Redis/Firestore for PKCE state — correct for multi-instance but adds infrastructure complexity contradicting Simplicity Boundary

---

## Decision 3: Stateless data layer — in-memory Pydantic models

**Decision**: Pydantic dataclasses (`PositionView`, `ScreenerResultView`) that live only for the duration of a request.

**Rationale**: Positions, Greeks, and screener results are fetched live and rendered or serialised to JSON. Pydantic gives validation, serialisation, and type safety with zero persistence overhead. Already a FastAPI transitive dependency.

**Alternatives considered**:
- Plain dicts — no type safety, harder to maintain
- SQLAlchemy models as in-memory only — awkward without a session; adds cold-start weight

---

## Decision 4: Thesis / spread / exit-goal persistence — browser localStorage

**Decision**: All user metadata stored exclusively in browser `localStorage` as JSON. Server has no API for this data.

**Rationale**: Small volume (tens of objects); no server round-trip needed for rendering; survives page reloads within the same browser; cleared by "Erase All".

**Alternatives considered**:
- Server-side JSON file — reintroduces persistence
- IndexedDB — more complex API; localStorage sufficient for this volume
- Session cookie — 4 KB limit infeasible

---

## Decision 5: Remove alert infrastructure entirely

**Decision**: Delete `src/notifications/`, `src/rules/`, `Alert` model, `BinaryEventFlag`, and all alert-related routes and scheduler jobs.

**Rationale**: Deferred indefinitely per user. Dead code increases cold-start time and maintenance burden.

---

## Decision 6: Remove SSE in favour of pull-on-demand

**Decision**: Delete `src/api/routes/sse.py`. UI uses `fetchWithAuth()` on button click.

**Rationale**: SSE requires persistent server connections, preventing scale-to-zero. Pull-on-demand is stateless and matches the architecture.

---

## Decision 7: Dependencies to remove

| Package | Reason removed |
|---------|---------------|
| `sqlalchemy[asyncio]` | No DB |
| `aiosqlite` | No SQLite |
| `alembic` | No migrations |
| `apscheduler` | No background jobs |
| `aiosmtplib` | No email alerts |
| `cryptography` | Token encryption was for DB-stored tokens only |
| `holidays` | Used only in poll scheduler market-hours check |
| `itsdangerous` | PKCE state now in-memory dict; no longer needed |

Packages retained:

| Package | Reason kept |
|---------|------------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `jinja2` | HTML templating |
| `python-multipart` | Form data parsing |
| `schwab-py` | Schwab API client (screener + positions routes) |
| `httpx` | HTTP client — raw Schwab token endpoint calls in auth path |
| `scipy`, `numpy` | Black-Scholes Greek calculation |
| `python-dotenv` | Env var loading |
| `pytest`, `pytest-asyncio` | Testing |

---

## Decision 8: Cloud Run deployment configuration

**Decision**: Dockerfile with `--min-instances=0 --max-instances=1`, no volume mounts.

**Rationale**: Scale-to-zero eliminates idle cost. `max-instances=1` is required by the in-memory PKCE state dict (see Decision 2) — a multi-instance deployment would break the OAuth flow. Cold start target of 3 seconds is achievable with the slimmed dependency set.

**Constraint**: `max-instances=1` must be enforced via Cloud Run deployment flags. If horizontal scaling is needed in future, replace the in-memory PKCE dict with Cloud Firestore or use Redis.

---

## Decision 9: Frontend token expiry handling — redirect to login (no silent refresh)

**Decision**: `fetchWithAuth(url, options)` JS function: if response is 401, call `eraseAll()` immediately (clears sessionStorage, localStorage, IndexedDB) and redirect to login. No refresh attempt. No retry.

**Rationale**: Explicit user preference (2026-05-13). The 30-minute Schwab access token lifetime is long enough for a typical trading session. Forcing a clean re-login on expiry is simpler, more predictable, and eliminates the two-tab refresh-race problem entirely. The `POST /auth/refresh` route is not implemented.

**Implications**:
- `schwab_refresh_token` is no longer stored in `sessionStorage` (the callback delivers it but it is discarded; only `schwab_access_token` is stored)
- `fetchWithAuth()` is ~15 lines with no coordination complexity
- `POST /auth/refresh` endpoint removed from `src/auth/router.py`
- Users whose token expires mid-session see a redirect to login — expected UX, not an error

**Alternatives considered**:
- Silent refresh + localStorage lock — prevents mid-session interruption but complex, multi-tab race possible, adds `POST /auth/refresh` endpoint; rejected per user preference
- BroadcastChannel refresh coordination — production-grade but over-engineered; moot since refresh removed

---

## Decision 10: Dynamic account resolution (replaces hardcoded env vars)

**Decision**: Call `client.get_account_numbers()` per screener/positions request to resolve the account hash. No `SCHWAB_ACCOUNT_ID` or `SCHWAB_CC_ACCOUNT_ID` env vars required at runtime.

**Rationale**: Required for multi-user support — hardcoded account numbers cannot work when any Schwab user authenticates. `get_account_numbers()` is a lightweight Schwab API call that returns all linked accounts; the first account is used for both positions and screener. The `account_resolver.py` module already implements this with a process-lifetime cache keyed by account number.

**Note**: The process-lifetime cache in `account_resolver.py` is safe for single-instance because each user's access token resolves to their own accounts — the cache is keyed by account number (globally unique), not by user. In practice, each unique access token will see different accounts, so the cache will grow slightly per unique user per process restart. Acceptable for a personal tool.

**Alternatives considered**:
- Keep `SCHWAB_ACCOUNT_ID` env var — prevents multi-user; requires ops config per deployer
- Per-request `get_account_numbers()` with no cache — correct but adds one extra API call on every refresh; acceptable latency but unnecessary when the same token is reused within a session
