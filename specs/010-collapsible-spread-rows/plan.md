# Implementation Plan: Collapsible Spread Rows

**Branch**: `010-collapsible-spread-rows` | **Date**: 2026-05-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/010-collapsible-spread-rows/spec.md`

## Summary

The positions table currently renders each option leg as a separate row. When a trader has multi-leg
spreads (positions assigned to the same thesis group), the table becomes cluttered with logically
related rows. This feature groups those legs under a single collapsible summary row — collapsed by
default — with aggregated metrics (P&L, Delta, Gamma, Theta, Vega summed; Mark, Qty, Type, Strike,
IV showing "—"). No server changes are required; all logic is client-side in `positions_ui.js` with
data sourced from the existing thesis assignment store.

## Technical Context

**Language/Version**: Vanilla JS ES modules (no build pipeline, no framework)
**Primary Dependencies**: `thesis_store.js` (getThesisGroups, getAssignments), `position_cache.js`
**Storage**: No new storage. Expand/collapse state is in-memory only (resets on re-render).
**Testing**: No frontend JS test framework exists. Aggregation logic extracted as pure functions; verified via quickstart.md visual scenarios. See Complexity Tracking.
**Target Platform**: Web browser — desktop + mobile (Tailwind responsive classes required)
**Project Type**: Frontend UI feature — no backend changes
**Performance Goals**: Expand/collapse responds in under 100ms (pure DOM toggle — no computation on interaction)
**Constraints**: No npm, no build step, no third-party JS libraries. ES module imports only.
**Scale/Scope**: Affects `positions_ui.js` and the compiled `dist/` copy. One file changed.

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Privacy-First | ✅ Pass | No server changes. Spread grouping is computed entirely from data already in the browser (sessionStorage + localStorage). No new data flows. |
| II. Security-First | ✅ Pass | Thesis group names rendered in HTML — must escape via the existing `escapeHtml` pattern. No new endpoints, no token handling. |
| III. Spec-Before-Code | ✅ Pass | Spec committed before any implementation. |
| IV. Test-First | ⚠️ Gap | No JS test framework exists in this project. Aggregation logic (sumGreeks, buildSpreadGroups) will be written as pure functions to facilitate future testability. Visual verification is documented in quickstart.md. See Complexity Tracking. |
| V. Simplicity Boundary | ✅ Pass | Single JS file change. No new abstractions beyond what the feature requires. |
| VI. Visual & Responsive UI | ✅ Pass | Toggle and expanded leg rows must render correctly on mobile viewports. |

## Project Structure

### Documentation (this feature)

```text
specs/010-collapsible-spread-rows/
├── plan.md          ← this file
├── research.md      ← Phase 0 output
├── data-model.md    ← Phase 1 output
├── quickstart.md    ← Phase 1 output (visual verification steps)
└── tasks.md         ← Phase 2 output (/speckit-tasks command)
```

### Source Code (files changed)

```text
frontend/static/js/positions_ui.js   ← sole file modified
dist/static/js/positions_ui.js       ← compiled copy — must be kept in sync
```

No backend changes. No new files in `src/`. No new test files (see Complexity Tracking).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| IV. Test-First gap — no JS unit tests | No JS test framework exists in the project. Adding one (Jest, Vitest) exceeds this feature's scope. | Installing a JS test framework requires build tooling that violates Principle V for this single feature. Aggregation functions are pure and can be unit tested when a framework is added. |
