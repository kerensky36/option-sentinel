# Research: Security Hardening (Constitution v3.1.0 Compliance)

**Feature**: 006-account-picker (security hardening phase)
**Date**: 2026-05-14

---

## Decision 1: Content Security Policy — Nonce vs Hash

**Decision**: Use a per-request **nonce** injected via Starlette middleware and passed through Jinja2 template context.

**Rationale**: `base.html` contains two inline `<script>` blocks (Tailwind config and Erase All handler) and the auth callback template has an inline script that writes to sessionStorage. Hashes require computing a SHA-256 of each script body at build time and updating the CSP on every content change — fragile in development. A nonce generated per request is the industry standard and works without content freezing. The middleware generates a 16-byte URL-safe nonce, stores it in `request.state.csp_nonce`, and adds the CSP header after the response. Route handlers that return HTML must include `csp_nonce` in the template context; templates apply `nonce="{{ csp_nonce }}"` to each `<script>` block.

**Nonce policy**:
- `default-src 'self'`
- `script-src 'self' https://cdn.tailwindcss.com 'nonce-{nonce}'` — allows Tailwind CDN and local modules
- `style-src 'self' https://fonts.googleapis.com 'unsafe-inline'` — inline styles are pervasive in templates; removing them requires a full template audit (deferred)
- `font-src 'self' https://fonts.gstatic.com`
- `img-src 'self' data:`
- `connect-src 'self'` — XHR/fetch only to own origin
- `frame-ancestors 'none'` — equivalent to X-Frame-Options: DENY
- `base-uri 'self'`
- `form-action 'self'`

**Alternatives considered**:
- Hash-based CSP: No per-request overhead but breaks on any script edit. Rejected.
- `unsafe-inline`: Nullifies CSP protection entirely. Rejected.
- Move all inline scripts to external files: Correct long-term, but requires template restructuring beyond this feature's scope. Deferred.

---

## Decision 2: Rate Limiting Approach

**Decision**: Use **`slowapi`** (a FastAPI-native rate limiting library) with in-memory storage per Cloud Run instance.

**Rationale**: Cloud Run is currently configured with `--min-instances=0 --max-instances=1`. With a single instance, in-memory rate limiting is effective and needs no external coordination (no Redis required). `slowapi` integrates directly with FastAPI's dependency injection and Starlette middleware. Limits: 60 requests/minute for authenticated API endpoints; 10 requests/minute for OAuth flow endpoints (`/auth/start`, `/auth/callback`).

**Future path**: When `max-instances` is raised above 1, per-instance limits provide per-instance protection (sufficient for basic abuse prevention). For coordinated rate limiting at scale, Cloud Armor (GCP WAF) should be added in front of Cloud Run — no code changes needed.

**Alternatives considered**:
- Cloud Armor only: Requires GCP IAP/WAF configuration outside the codebase. Not self-contained. Deferred as a production enhancement.
- `redis`-backed slowapi: Correct for multi-instance, but adds an external dependency. Not needed at current scale.

---

## Decision 3: CORS Policy

**Decision**: Add FastAPI `CORSMiddleware` with `allow_origins` configured from `ALLOWED_ORIGIN` env var. No wildcard. Default (dev) origin: `http://localhost:8000`.

**Rationale**: The app currently has no CORS policy. Browsers do not enforce SOP for same-origin requests, but API endpoints can be called cross-origin by attacker-controlled pages if CORS is open. Locking CORS to the app's own origin prevents cross-origin requests from harvesting data from logged-in users. The production origin (Firebase Hosting domain) is set via `ALLOWED_ORIGIN` env var in Cloud Run.

**Alternatives considered**:
- Wildcard `*`: Forbidden by constitution. Rejected.
- Hardcoded origin: Would require code changes to update for new domains. Rejected in favour of env var.

---

## Decision 4: Security Response Headers Middleware

**Decision**: Single `SecurityHeadersMiddleware` Starlette class added to `create_app()` that mutates every response to add the required headers.

**Headers applied**:
| Header | Value |
|--------|-------|
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (production only, gated on `HTTPS_ONLY=true` env var) |
| `Cache-Control` | `no-store` (API routes only; static assets excluded) |
| `Content-Security-Policy` | Nonce-based policy (see Decision 1) |

**Alternatives considered**:
- Configuring headers at Cloud Run / Firebase Hosting level: Correct for static assets, but doesn't cover dynamic API responses. Both layers needed; middleware covers the app layer.

---

## Decision 5: Security Event Audit Logging

**Decision**: Use Python `logging` to emit structured log lines to `stderr` for the following events: invalid/missing Bearer token (401), invalid `account_hash` (422), OAuth state mismatch, OAuth state expiry, Schwab API 4xx/5xx responses. Log format includes timestamp, event type, endpoint path, and hashed IP — never token or account values.

**Rationale**: Cloud Run captures `stderr` in Cloud Logging. No third-party logging service is needed; no additional dependencies. Hashing the IP with a pepper prevents exact IP storage while still allowing anomaly correlation.

**Alternatives considered**:
- Structured JSON logging library (structlog): Better for parsing but adds a dependency. Deferred.
- External SIEM integration: Out of scope for this phase.

---

## Decision 6: Generic Production Error Handler

**Decision**: Register a FastAPI exception handler for `Exception` that returns `{"detail": "Internal server error"}` with status 500 in production (`DEBUG=false`). In development (`DEBUG=true`), the default FastAPI error handling (with stack traces) remains active.

**Rationale**: FastAPI's default unhandled exception response can include stack traces, file paths, and internal identifiers. These must not reach clients in production. The handler is gated on an env var to preserve developer experience.

**Alternatives considered**:
- Always generic: Harms developer experience with no upside in dev. Rejected.

---

## Decision 7: pip-audit Integration

**Decision**: Add a `make audit` / `scripts/audit.sh` script running `pip-audit --require-hashes -r requirements.txt` and document it as a required step before every release. Pin all dependencies to exact versions (`==`) in `requirements.txt`.

**Rationale**: `pip-audit` is the Python ecosystem's standard CVE scanner, maintained by PyPA. It checks against the OSV and PyPI Advisory databases. `--require-hashes` ensures no dependency substitution. Running on every PR is the constitution's requirement; the script makes this easy to add to CI.

**Alternatives considered**:
- Dependabot / Renovate: Good for automated PRs but doesn't block releases. Complementary, not a replacement.
- Safety (PyUp): Alternative scanner. pip-audit is PyPA-maintained and open source. Preferred.
