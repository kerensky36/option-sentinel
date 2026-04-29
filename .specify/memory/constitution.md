<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Modified principles: V. Simplicity Boundary — removed "mobile apps" from out-of-scope list
  (native mobile app remains out of scope; responsive web dashboard is now in scope)
Added sections: VI. Visual & Responsive UI
Removed sections: N/A
Templates reviewed:
  ✅ .specify/templates/plan-template.md — no changes needed
  ✅ .specify/templates/spec-template.md — no changes needed
  ✅ .specify/templates/tasks-template.md — no changes needed
  ✅ .speckit/spec.md — Assumptions updated: "Mobile app support is explicitly out of scope"
  clarified to "Native mobile app is out of scope; the web dashboard MUST be mobile-responsive"
Follow-up TODOs: None
-->

# Option Sentinel Constitution

## Core Principles

### I. Local-First Privacy

All position data MUST remain on the trader's machine. The only permitted outbound
destination is the Charles Schwab OAuth2 API. No cloud sync, no external logging
services, and no third-party analytics are permitted. Compliance is verifiable by
network inspection (SC-006).

### II. Spec-Before-Code

The spec defines behavior before implementation begins. Spec file changes MUST be
committed before corresponding `src/`, `frontend/`, or `tests/` changes in every
session. No implementation task begins without a traceable requirement in
`.speckit/spec.md`.

### III. Test-First (NON-NEGOTIABLE)

Acceptance scenarios in `spec.md` drive tests. Tests MUST be written and confirmed
failing before implementation begins. The Red-Green-Refactor cycle is strictly
enforced. Skipping this step for any user story is not permitted.

### IV. Alert Reliability

Every triggered alert MUST result in delivery or a logged retry entry. Alert logic
MUST be idempotent — no double-firing within the same trigger event. Failed
deliveries MUST be retried up to 3 times before being marked permanently failed
(FR-021, FR-022, SC-007).

### V. Simplicity Boundary

Option Sentinel serves a single trader, a single brokerage account, on a local
machine. Multi-user support, cloud sync, native mobile apps, and automated trading
are explicitly out of scope. Every abstraction added beyond the stated requirements
MUST be justified in the plan.md Complexity Tracking table.

### VI. Visual & Responsive UI

The dashboard MUST be visual-first and data-dense without being text-heavy.
Positions, P&L, and alert states MUST be communicated through layout, colour,
and visual hierarchy rather than prose. The web dashboard MUST render correctly
on mobile viewports — a trader checking positions on a phone MUST see a fully
functional, legible interface. No native mobile app is required; a responsive
web layout is sufficient.

## Technology Constraints

- **Language**: Python 3.11+
- **Brokerage**: Charles Schwab OAuth2 API (position retrieval only; no trade execution)
- **Storage**: SQLite by default; switchable to Postgres via a configuration change
  and schema migration only — no application logic changes permitted for this switch
- **Notifications**: SMTP-compatible email; credentials stored locally and MUST NOT
  be transmitted to any external service; Twilio SMS is a stretch goal, not required
- **Frontend**: Local web dashboard only; no remote hosting; no native mobile app;
  responsive layout required for mobile viewports
- **Dependencies**: All declared in `requirements.txt`

## Development Workflow

Follow the Speckit sequence: specify → clarify → plan → tasks → implement.
Spec commits MUST precede app commits in every session (Principle II).
Each user story MUST be implemented, tested, and validated independently before
the next story begins. Every implementation task MUST trace to a requirement in
`.speckit/spec.md`.

## Governance

This constitution supersedes all other project practices. Conflicts resolve in
favor of the constitution. Amendments require: updating this file, incrementing
the version following semantic versioning (MAJOR: governance/principle removals
or redefinitions; MINOR: new principle or section added; PATCH: clarifications
and wording), and propagating changes to affected templates. All PRs MUST verify
principle compliance before merge. Complexity violations MUST be documented in
plan.md's Complexity Tracking table before implementation proceeds.

**Version**: 1.1.0 | **Ratified**: 2026-04-28 | **Last Amended**: 2026-04-29
