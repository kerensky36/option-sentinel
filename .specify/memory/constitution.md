<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 2.0.0
Modified principles:
  I. Local-First Privacy → I. Privacy-First Data Handling
    Rationale: "trader's machine" is the app user's environment, not necessarily
    a local laptop. Privacy guarantee is about persistence and sharing, not
    physical location. Ephemeral cloud processing is permitted; no data may be
    persisted server-side.
  V. Simplicity Boundary (was V, now IV)
    Removed "on a local machine" — app now runs on Cloud Run.
    Renumbered after Principle IV removal.
  VI. Visual & Responsive UI (was VI, now V)
    Renumbered only — no content change.
    "Alert states" removed from the visual requirement as alerts are deferred.
Removed principles:
  IV. Alert Reliability — removed entirely; alerts deferred indefinitely.
Removed technology constraints:
  Storage: SQLite/Postgres requirement removed; replaced with no-storage mandate.
  Notifications: SMTP/email constraint removed; alerts out of scope.
Modified technology constraints:
  Frontend: "local web dashboard only; no remote hosting" →
    "single-instance cloud-hosted web dashboard"
Templates reviewed:
  ✅ .specify/templates/plan-template.md — no changes needed (Constitution Check
     section is generic; principle numbers not referenced directly)
  ✅ .specify/templates/spec-template.md — no changes needed
  ✅ .specify/templates/tasks-template.md — no changes needed
  ✅ specs/004-stateless-ephemeral-refactor/plan.md — Complexity Tracking
     violations for Principles I, IV, Storage, and Frontend are now resolved;
     the violations table remains as a historical record of the decision rationale
Follow-up TODOs:
  - Remove Complexity Tracking violation rows from 004 plan.md in Phase 8 polish
    (they are now compliant, not violations)
-->

# Option Sentinel Constitution

## Core Principles

### I. Privacy-First Data Handling

Position data MUST NOT be persisted by the server or shared with any third party
beyond the Charles Schwab OAuth2 API. No external logging services, data sync to
cloud storage, or third-party analytics are permitted. Ephemeral processing in a
server container is acceptable provided no data is written to disk, a database,
or any external service. Session tokens MUST be stored in signed, HttpOnly browser
cookies only — not on the server. Compliance is verifiable by confirming no
persistent storage layer exists in the application and by network inspection.

### II. Spec-Before-Code

The spec defines behavior before implementation begins. Spec file changes MUST be
committed before corresponding `src/`, `frontend/`, or `tests/` changes in every
session. No implementation task begins without a traceable requirement in the
active feature spec.

### III. Test-First (NON-NEGOTIABLE)

Acceptance scenarios in `spec.md` drive tests. Tests MUST be written and confirmed
failing before implementation begins. The Red-Green-Refactor cycle is strictly
enforced. Skipping this step for any user story is not permitted.

### IV. Simplicity Boundary

Option Sentinel serves a single trader and a single brokerage account.
Multi-user support, data sync to external services, native mobile apps, and
automated trading are explicitly out of scope. Every abstraction added beyond the
stated requirements MUST be justified in the plan.md Complexity Tracking table.

### V. Visual & Responsive UI

The dashboard MUST be visual-first and data-dense without being text-heavy.
Positions and P&L MUST be communicated through layout, colour, and visual
hierarchy rather than prose. The web dashboard MUST render correctly on mobile
viewports — a trader checking positions on a phone MUST see a fully functional,
legible interface. No native mobile app is required; a responsive web layout
is sufficient.

## Technology Constraints

- **Language**: Python 3.11+
- **Brokerage**: Charles Schwab OAuth2 API (position retrieval only; no trade execution)
- **Storage**: No server-side storage. All server state is ephemeral — held in
  memory for the duration of a request only. Session tokens are stored in signed,
  HttpOnly browser cookies. No database, filesystem writes, or mounted volumes
  are permitted in the production deployment.
- **Frontend**: Single-instance cloud-hosted web dashboard. No multi-tenant
  hosting; no native mobile app. Responsive layout required for mobile viewports.
- **Dependencies**: All declared in `requirements.txt`

## Development Workflow

Follow the Speckit sequence: specify → clarify → plan → tasks → implement.
Spec commits MUST precede app commits in every session (Principle II).
Each user story MUST be implemented, tested, and validated independently before
the next story begins. Every implementation task MUST trace to a requirement in
the active feature spec.

## Governance

This constitution supersedes all other project practices. Conflicts resolve in
favor of the constitution. Amendments require: updating this file, incrementing
the version following semantic versioning (MAJOR: governance/principle removals
or redefinitions; MINOR: new principle or section added; PATCH: clarifications
and wording), and propagating changes to affected templates. All PRs MUST verify
principle compliance before merge. Complexity violations MUST be documented in
plan.md's Complexity Tracking table before implementation proceeds.

**Version**: 2.0.0 | **Ratified**: 2026-04-28 | **Last Amended**: 2026-05-03
