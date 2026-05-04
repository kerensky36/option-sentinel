# Research: Stateless Ephemeral Refactor

**Feature**: 004-stateless-ephemeral-refactor
**Phase**: 0 — Technology decisions
**Date**: 2026-05-03

---

## Decision 1: Schwab OAuth web flow strategy

**Decision**: Use `schwab-py`'s `client_from_access_functions()` with session-stored tokens.

**Rationale**: `schwab-py >= 1.5` already exposes `schwab.auth.client_from_access_functions(api_key, app_secret, token_read_func, token_write_func, asyncio=True)`. This accepts callable read/write functions instead of file paths, making it trivially compatible with session storage. The OAuth code-exchange step uses the library's lower-level helpers: build the authorise URL, redirect the user to Schwab, receive the code at the callback, call `client_from_received_url()` once to exchange the code for tokens, then serialise those tokens to the session. On subsequent requests, `client_from_access_functions` rebuilds the client from the session, including auto-refresh when the access token expires.

**Alternatives considered**:
- `authlib` + direct Schwab client construction — avoids schwab-py internals but duplicates OAuth logic the library already handles.
- File-based token (`client_from_token_file`) with a Cloud Storage FUSE mount — persistent storage not required and would contradict the stateless goal.
- `schwab-py client_from_manual_flow` — interactive CLI flow, unsuitable for a web server.

---

## Decision 2: Session cookie library

**Decision**: Use Starlette's built-in `SessionMiddleware` (already bundled with FastAPI).

**Rationale**: `SessionMiddleware` from `starlette.middleware.sessions` provides a signed, encrypted cookie backed by `itsdangerous`. Requires only a `SECRET_KEY` env var. The session dict is available on every request via `request.session`. No additional library install needed — starlette is already a FastAPI transitive dependency.

**Alternatives considered**:
- `starlette-sessions` (server-side sessions) — unnecessary complexity; server-side storage reintroduces the persistence problem.
- `fastapi-sessions` — third-party library; adds a dependency for functionality already in Starlette.
- JWT in Authorization header — requires client-side token management; more complex than a cookie for an HTMX-driven UI.

---

## Decision 3: Stateless data layer — in-memory Pydantic models

**Decision**: Replace SQLAlchemy ORM models with lightweight Pydantic dataclasses that live only for the duration of a request.

**Rationale**: Positions, Greeks, and screener results are fetched live from Schwab and rendered to HTML or returned as JSON. They never need to be queried, filtered, or joined after the initial fetch. Pydantic models give validation, serialisation, and type safety with zero persistence overhead.

**Alternatives considered**:
- Plain dicts — no type safety; harder to maintain.
- Dataclasses — viable but Pydantic is already a transitive dependency (FastAPI requires it) and gives free JSON serialisation.
- Keep SQLAlchemy models as in-memory only (no DB) — SQLAlchemy ORM without a session is awkward; removing it reduces cold-start time and dependency weight.

---

## Decision 4: Thesis / spread / exit-goal persistence — browser localStorage

**Decision**: Thesis group definitions, position-to-thesis assignments, spread parameters, and exit goals are stored exclusively in browser `localStorage` as JSON. The server has no API for this data.

**Rationale**: This data is user-authored metadata, not fetched from Schwab. Volume is small (tens of objects). It needs no server round-trip to read — the browser applies it when rendering the positions table. A future export/import feature can be added without server changes.

**Alternatives considered**:
- Server-side JSON file — reintroduces persistence; complicates Cloud Run deployment.
- IndexedDB — more complex API; localStorage is simpler and sufficient for this data volume.
- Session cookie — cookie size limits (4 KB) make this infeasible for even a moderate number of theses.

---

## Decision 5: Remove alert infrastructure entirely

**Decision**: Delete `src/notifications/`, `src/rules/`, `Alert` model, `BinaryEventFlag`, and all alert-related routes and scheduler jobs.

**Rationale**: User explicitly deferred alerts to a future feature with no current timeline. Retaining dead code increases maintenance burden and cold-start time. All alert-related requirements are out of scope for this feature.

**Alternatives considered**:
- Stub/no-op alert functions — preserves the call sites but adds confusion about which features are active.
- Feature flag to disable alerts at runtime — unnecessary complexity; just delete the code.

---

## Decision 6: Remove SSE in favour of pull-on-demand

**Decision**: Delete `src/api/routes/sse.py` and the `EventSourceResponse` pattern. The UI uses HTMX-triggered GET requests on button click to refresh data.

**Rationale**: SSE requires a persistent server connection, preventing scale-to-zero. Pull-on-demand (button click → HTMX GET → partial HTML response) is simpler, fully stateless, and sufficient for a personal tool where the user actively triggers refreshes.

**Alternatives considered**:
- WebSocket — same persistent-connection problem as SSE.
- Polling from the client — constant client-initiated polling is the same CPU problem we're solving, just moved to the client.

---

## Decision 7: Dependencies to remove

The following packages are no longer needed and should be removed from `requirements.txt`:

| Package | Reason removed |
|---|---|
| `sqlalchemy[asyncio]` | No DB |
| `aiosqlite` | No SQLite |
| `alembic` | No migrations |
| `apscheduler` | No background jobs |
| `aiosmtplib` | No email alerts |
| `cryptography` | Token encryption was for DB-stored tokens only |
| `holidays` | Used only in poll scheduler market-hours check |

The following packages are retained:

| Package | Reason kept |
|---|---|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `jinja2` | HTML templating |
| `python-multipart` | Form data parsing |
| `schwab-py` | Schwab API client |
| `httpx` | HTTP client (used by schwab-py) |
| `scipy`, `numpy` | Black-Scholes Greek calculation |
| `python-dotenv` | Env var loading |
| `pytest`, `pytest-asyncio` | Testing |
| `itsdangerous` | Session cookie signing (transitive via starlette; make explicit) |

---

## Decision 8: Cloud Run deployment configuration

**Decision**: Dockerfile with `--min-instances=0 --max-instances=1`, no volume mounts, `SECRET_KEY` and Schwab credentials via Cloud Run environment variables (Secret Manager).

**Rationale**: Scale-to-zero with min=0 eliminates idle compute cost. max=1 guarantees no horizontal scaling that would conflict with in-memory session state (session is in cookie, not server memory, so this is actually not strictly required — but max=1 keeps the deployment simple and matches the single-user design intent). Cold start target of 3 seconds is achievable with the slimmed dependency set.

**Alternatives considered**:
- Min-instances=1 during market hours via Cloud Scheduler warmup ping — valid but adds operational complexity; acceptable cold starts make it unnecessary for a personal tool.
- Cloud Run Jobs for screener — over-engineered; on-demand refresh is sufficient.
