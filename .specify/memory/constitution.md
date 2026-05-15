<!--
SYNC IMPACT REPORT
==================
Version change: 2.1.0 → 3.0.0
Bump type: MAJOR — core scope redefined (single-trader → multi-user);
  new Security principle added; principles renumbered.

Modified principles:
  I. Privacy-First Data Handling
    Rationale: Extended to explicitly require per-user data isolation in a
    multi-user deployment. Each user's Schwab token, positions, and account
    data MUST be isolated from every other user. The server MUST be provably
    stateless between requests so no user's data can bleed into another's.
  V. Simplicity Boundary (was IV)
    Rationale: Removed "single trader" and "single brokerage account"
    constraints. The app now serves multiple independent users. Out-of-scope
    items (automated trading, native mobile apps, multi-tenant data storage)
    are retained unchanged.

Added principles:
  II. Security-First
    Rationale: The app handles live brokerage credentials and real financial
    positions for multiple users. A breach or cross-user data leak carries
    direct financial harm and legal liability. Security is elevated to the
    second core principle — a non-negotiable gate on every feature.

Removed principles:
  None

Renumbered principles:
  Old II → New III  (Spec-Before-Code)
  Old III → New IV  (Test-First)
  Old IV → New V    (Simplicity Boundary, also modified above)
  Old V → New VI    (Visual & Responsive UI)

Technology Constraints modified:
  Multi-user: Explicit statement that the app supports multiple independent
    users simultaneously via the stateless token-per-request architecture.
  Security controls: Rate limiting, HTTPS, CORS, input validation, and
    dependency hygiene added as mandatory technology constraints.

Templates reviewed:
  ✅ .specify/templates/plan-template.md — no changes needed (Constitution
     Check section is generic; principle numbers not referenced directly)
  ✅ .specify/templates/spec-template.md — no changes needed
  ✅ .specify/templates/tasks-template.md — no changes needed

Follow-up TODOs:
  - Add rate limiting middleware to the FastAPI app (not yet implemented).
  - Add CORS policy configuration to src/api/main.py.
  - Add a dependency audit step (pip-audit or equivalent) to CI.
  - Review all prior plan.md Complexity Tracking tables — the "single trader"
    justifications in 004 and 005 plans are now superseded by this amendment.
  - The Complexity Tracking violation row in specs/006-account-picker/plan.md
    (already marked RESOLVED) remains accurate.
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
multiple independent users. Any security failure carries direct financial harm
and legal liability. The following controls are NON-NEGOTIABLE:

- **Input validation**: Every client-supplied value (account hash, query params,
  request bodies) MUST be validated server-side before use. A client-supplied
  `account_hash` MUST be verified against the accounts returned by the user's own
  Bearer token — an attacker MUST NOT be able to access another user's account
  by guessing or supplying a foreign hash.
- **No cross-user data leakage**: The server MUST enforce that each request's data
  is derived solely from the Bearer token presented in that request. No shared
  in-process caches, global variables, or mutable module-level state may retain
  data between requests from different users.
- **Token hygiene**: Bearer tokens and account hash values MUST NOT appear in server
  logs, error responses, metrics, or any external output. Log sanitisation MUST be
  verified in code review.
- **Output sanitisation**: All data rendered in HTML templates MUST be
  auto-escaped. No raw user-controlled strings may be injected into HTML, JS,
  or API responses.
- **Transport security**: All production traffic MUST be served over HTTPS. HTTP
  connections MUST be rejected or redirected. CORS policy MUST be explicitly
  configured to allow only the app's own origin.
- **Rate limiting**: API endpoints MUST be rate-limited to prevent credential
  stuffing, enumeration, and denial-of-service attacks.
- **Dependency hygiene**: All third-party dependencies MUST be pinned and audited
  for known vulnerabilities (e.g., via `pip-audit`) on each release. No dependency
  with a known critical CVE may ship to production.
- **Error handling**: Error responses MUST NOT expose internal implementation
  details, stack traces, or sensitive values to the client.

Compliance is verifiable through code review (no shared state, no token logging),
automated dependency audit, HTTPS enforcement checks, and penetration-style input
validation tests.

### III. Spec-Before-Code

The spec defines behavior before implementation begins. Spec file changes MUST be
committed before corresponding `src/`, `frontend/`, or `tests/` changes in every
session. No implementation task begins without a traceable requirement in the
active feature spec.

### IV. Test-First (NON-NEGOTIABLE)

Acceptance scenarios in `spec.md` drive tests. Tests MUST be written and confirmed
failing before implementation begins. The Red-Green-Refactor cycle is strictly
enforced. Skipping this step for any user story is not permitted. Security
controls introduced under Principle II MUST have corresponding contract or unit
tests verifying the control before the implementation is merged.

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
- **Users**: Multiple independent users are supported simultaneously. Each user
  authenticates via their own Schwab OAuth token presented as a Bearer header.
  The server is stateless per-request — no user state is retained between requests.
- **Storage**: No server-side storage. All server state is ephemeral — held in
  memory for the duration of a single request only. The Schwab access token is
  stored in browser sessionStorage client-side and never persisted server-side.
  No database, filesystem writes, or mounted volumes are permitted in production.
- **Security controls**: Rate limiting MUST be applied to all API endpoints.
  HTTPS MUST be enforced in production. CORS MUST be configured to the app's own
  origin only. Dependency audit (pip-audit or equivalent) MUST run on each release.
- **Frontend**: Cloud-hosted web dashboard. No multi-tenant data storage. No native
  mobile app. Responsive layout required for mobile viewports.
- **Dependencies**: All declared in `requirements.txt`; pinned and audited.

## Development Workflow

Follow the Speckit sequence: specify → clarify → plan → tasks → implement.
Spec commits MUST precede app commits in every session (Principle III).
Each user story MUST be implemented, tested, and validated independently before
the next story begins. Every implementation task MUST trace to a requirement in
the active feature spec. Security controls (Principle II) MUST be verified by
failing tests before implementation, consistent with Principle IV.

## Governance

This constitution supersedes all other project practices. Conflicts resolve in
favor of the constitution. Amendments require: updating this file, incrementing
the version following semantic versioning (MAJOR: governance/principle removals,
redefinitions, or scope changes; MINOR: new principle or section added; PATCH:
clarifications and wording), and propagating changes to affected templates and
prior plan.md files. All PRs MUST verify principle compliance before merge.
Complexity violations MUST be documented in plan.md's Complexity Tracking table
before implementation proceeds. Security control gaps identified during review
MUST be logged as follow-up TODOs in the Sync Impact Report of the relevant
amendment.

**Version**: 3.0.0 | **Ratified**: 2026-04-28 | **Last Amended**: 2026-05-14
