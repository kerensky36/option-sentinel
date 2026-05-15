<!--
SYNC IMPACT REPORT
==================
Version change: 3.0.0 → 3.1.0
Bump type: MINOR — Principle II (Security-First) materially expanded with
  explicit threat-model-driven controls. No principles added or removed.
  No scope changes.

Modified principles:
  II. Security-First
    Rationale: The v3.0.0 Security-First principle listed 8 high-level
    controls. This amendment expands each control to be explicit and
    testable against a blackhat threat model: credential theft via XSS,
    IDOR attacks, OAuth flow manipulation, token interception, clickjacking,
    supply chain compromise, and information disclosure via error responses.
    New controls added: Content Security Policy, security response headers
    (X-Frame-Options, HSTS, X-Content-Type-Options, Referrer-Policy),
    no-token-in-URL rule, OAuth PKCE integrity mandate, security event
    audit logging, and zero-tolerance for sensitive data in any output.

Added sections:
  None (controls expanded within existing Principle II)

Removed sections:
  None

Templates reviewed:
  ✅ .specify/templates/plan-template.md — no changes needed
  ✅ .specify/templates/spec-template.md — no changes needed
  ✅ .specify/templates/tasks-template.md — no changes needed

Follow-up TODOs (implementation required — not yet in code):
  - Implement CSP middleware in src/api/main.py (strict-dynamic or nonce-based)
  - Implement security response headers middleware in src/api/main.py
    (X-Frame-Options: DENY, HSTS, X-Content-Type-Options: nosniff,
     Referrer-Policy: strict-origin-when-cross-origin)
  - Implement rate limiting middleware (e.g., slowapi or Cloud Run IAP)
  - Verify CORS is locked to app's own origin (not wildcard)
  - Add pip-audit to CI pipeline
  - Add security event audit logging for: invalid token, invalid account_hash,
    OAuth state mismatch, repeated 401s from same IP
  - Add production error handler that returns generic 500 (no stack traces)
  - Verify Jinja2 auto-escaping is enabled (it is by default; add explicit test)
  - Verify no token or account hash values appear in any server log line
-->

# Option Sentinel Constitution

## Core Principles

### I. Privacy-First Data Handling

Each user's financial data — including Schwab access tokens, account hashes,
positions, and P&L — is strictly private to that user. The server MUST be
provably stateless: no user data persists on the server between requests, and
no user's data is accessible from any other user's session. No external logging
services, cloud storage writes, or third-party analytics are permitted. Ephemeral
processing in a server container is acceptable provided nothing is written to
disk, a database, or any external service after the request completes. The Schwab
access token MUST be stored in browser sessionStorage only — never on the server,
in a cookie, or in any persistent browser store (localStorage, IndexedDB).
Compliance is verifiable by confirming no persistent storage layer exists in the
server and that token values never appear in server logs or error responses.

### II. Security-First

The app handles live brokerage credentials and real financial positions for
multiple independent users. A breach or cross-user data leak carries direct
financial harm and legal liability. Security is a non-negotiable gate on every
feature. The threat model assumes adversaries will attempt credential theft,
session hijacking, data enumeration, and supply chain attacks. All controls below
are MANDATORY unless explicitly marked otherwise.

#### Credential Theft & XSS Defence

- **Content Security Policy (CSP)**: Every HTML response MUST include a `Content-Security-Policy`
  header. The policy MUST forbid inline scripts (no `unsafe-inline`), restrict
  `script-src` to the app's own origin and approved CDNs, and forbid `object-src`
  and `base-uri`. CSP is the primary defence against XSS attacks that steal tokens
  from sessionStorage.
- **Output sanitisation**: All data rendered in HTML templates MUST be auto-escaped
  by the templating engine (Jinja2 auto-escape MUST be confirmed enabled). No
  raw user-controlled or API-returned strings may be injected into HTML or JS.
- **No token in URL**: Bearer tokens and account hash values MUST NEVER appear in
  URL paths, query parameters, fragments, or referrer headers. They MUST only
  transit via `Authorization: Bearer` headers or inline `<script>` blocks during
  the OAuth callback (which writes to sessionStorage and immediately redirects).

#### Cross-User Data Isolation (IDOR Prevention)

- **Account hash validation**: Every client-supplied `account_hash` MUST be
  validated server-side against the accounts returned by the Bearer token in the
  same request. A user MUST NOT be able to access another user's account by
  guessing or supplying a foreign hash. Validation MUST happen before any Schwab
  API call is made.
- **Zero shared server state**: No in-process caches, module-level variables, or
  request-scoped objects may retain data beyond the lifetime of a single HTTP
  request. Each request MUST be fully isolated. Compliance is verifiable by code
  review confirming no mutable global state holds user-derived data.
- **No server-side token storage**: The server MUST NOT store, cache, or log the
  user's Bearer token at any point. It is consumed within the request and
  discarded.

#### Transport & Network Security

- **HTTPS only**: All production traffic MUST be served over HTTPS/TLS 1.2+.
  HTTP connections MUST be rejected or permanently redirected (301). The app MUST
  emit `Strict-Transport-Security` (HSTS) headers with a minimum `max-age` of
  one year.
- **CORS policy**: Cross-Origin Resource Sharing MUST be configured to allow only
  the app's own origin. Wildcard (`*`) origins are forbidden. The CORS policy
  MUST be tested and verified on every deploy.
- **Security response headers**: Every response MUST include:
  - `X-Frame-Options: DENY` — prevents clickjacking
  - `X-Content-Type-Options: nosniff` — prevents MIME-type sniffing attacks
  - `Referrer-Policy: strict-origin-when-cross-origin` — prevents token leakage
    via referrer
  - `Cache-Control: no-store` on all API responses — prevents sensitive data
    appearing in browser or proxy caches

#### OAuth Flow Integrity

- **PKCE enforcement**: The OAuth 2.0 PKCE flow MUST be used for all Schwab
  authorisations. The `code_verifier` and `state` MUST be generated with
  cryptographically secure randomness (minimum 256 bits of entropy).
- **State parameter**: The `state` value MUST be validated on callback, single-use
  (deleted on first use), and TTL-enforced (maximum 10 minutes). Replayed or
  expired states MUST be rejected with a redirect to login.
- **No code reuse**: The authorisation code MUST be exchanged exactly once. Any
  second exchange attempt for the same code MUST be rejected.

#### Rate Limiting & Abuse Prevention

- **API rate limiting**: All API endpoints MUST be protected by rate limiting.
  Limits MUST be applied per IP (or per authenticated user where identifiable).
  Repeated failures (e.g., consecutive 401s, invalid account_hash submissions)
  MUST trigger progressively stricter limits.
- **Login flow protection**: The OAuth initiation endpoint (`/auth/start`) MUST
  be rate-limited to prevent abuse of the Schwab authorisation URL.

#### Logging & Audit

- **Zero sensitive output**: Bearer tokens, account hash values, and position data
  MUST NOT appear in any server log, structured log field, error message, metric
  label, or external output — in any environment including development.
- **Security event logging**: The following events MUST be logged (without
  sensitive values): invalid/missing Bearer token, invalid `account_hash` supplied,
  OAuth state mismatch, OAuth state expiry, Schwab API 4xx/5xx responses.
  Log entries MUST include timestamp, event type, and anonymised request context
  (e.g., hashed IP, endpoint path) — never token or account values.
- **Error responses**: Production error responses MUST return generic messages
  (e.g., `{"detail": "Internal server error"}`). Stack traces, file paths, and
  internal identifiers MUST NOT be included in any client-facing error response.

#### Dependency & Supply Chain Security

- **Pinned dependencies**: All third-party packages MUST be pinned to exact
  versions in `requirements.txt`. Unpinned ranges (`>=`, `~=`) are not permitted
  in production builds.
- **Dependency audit**: `pip-audit` (or equivalent CVE scanner) MUST run on every
  release build and on every CI pull request. Builds with known critical or high
  CVEs MUST be blocked until the dependency is updated or an exception is
  documented in the Complexity Tracking table.
- **Minimal surface**: No development-only dependencies may be included in the
  production container image or `requirements.txt`.

### III. Spec-Before-Code

The spec defines behavior before implementation begins. Spec file changes MUST be
committed before corresponding `src/`, `frontend/`, or `tests/` changes in every
session. No implementation task begins without a traceable requirement in the
active feature spec.

### IV. Test-First (NON-NEGOTIABLE)

Acceptance scenarios in `spec.md` drive tests. Tests MUST be written and confirmed
failing before implementation begins. The Red-Green-Refactor cycle is strictly
enforced. Skipping this step for any user story is not permitted. Every security
control introduced under Principle II MUST have a corresponding failing test
before the implementation is written and merged.

### V. Simplicity Boundary

Option Sentinel serves multiple independent traders, each authenticating with
their own Schwab OAuth token and accessing their own accounts. Automated trading,
shared data storage between users, native mobile apps, and external data sync
are explicitly out of scope. Every abstraction added beyond the stated requirements
MUST be justified in the plan.md Complexity Tracking table.

### VI. Visual & Responsive UI

The dashboard MUST be visual-first and data-dense without being text-heavy.
Positions and P&L MUST be communicated through layout, colour, and visual
hierarchy rather than prose. The web dashboard MUST render correctly on mobile
viewports — a trader checking positions on a phone MUST see a fully functional,
legible interface. No native mobile app is required; a responsive web layout
is sufficient.

## Technology Constraints

- **Language**: Python 3.11+
- **Brokerage**: Charles Schwab OAuth2 API (position retrieval only; no trade execution)
- **Users**: Multiple independent users supported simultaneously. Each user
  authenticates via their own Schwab OAuth token (Bearer header). The server is
  stateless per-request — no user state is retained between requests.
- **Storage**: No server-side storage. All server state is ephemeral — held in
  memory for the duration of a single request only. The Schwab access token is
  stored in browser sessionStorage client-side and never persisted server-side.
  No database, filesystem writes, or mounted volumes are permitted in production.
- **Security controls**: All controls in Principle II are mandatory in production.
  CSP, security headers, HTTPS/HSTS, CORS, rate limiting, pip-audit, and zero
  sensitive output in logs are non-negotiable deployment requirements.
- **Frontend**: Cloud-hosted web dashboard. No multi-tenant data storage. No native
  mobile app. Responsive layout required for mobile viewports.
- **Dependencies**: All declared in `requirements.txt`; exact versions pinned;
  audited via pip-audit on every release.

## Development Workflow

Follow the Speckit sequence: specify → clarify → plan → tasks → implement.
Spec commits MUST precede app commits in every session (Principle III).
Each user story MUST be implemented, tested, and validated independently before
the next story begins. Every implementation task MUST trace to a requirement in
the active feature spec. Security controls (Principle II) MUST be verified by
failing tests before implementation, consistent with Principle IV. Any new
endpoint, UI surface, or data flow MUST be reviewed against the full threat model
in Principle II before implementation begins.

## Governance

This constitution supersedes all other project practices. Conflicts resolve in
favor of the constitution. Amendments require: updating this file, incrementing
the version following semantic versioning (MAJOR: governance/principle removals,
redefinitions, or scope changes; MINOR: new principle or section added, or
existing principle materially expanded; PATCH: clarifications and wording),
and propagating changes to affected templates and prior plan.md files. All PRs
MUST verify principle compliance before merge. Complexity violations MUST be
documented in plan.md's Complexity Tracking table before implementation proceeds.
Security control gaps identified during review MUST be logged as follow-up TODOs
in the Sync Impact Report of the relevant amendment.

**Version**: 3.1.0 | **Ratified**: 2026-04-28 | **Last Amended**: 2026-05-14
