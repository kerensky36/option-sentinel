# Implementation Plan: Auto-Group Spreads by Underlying + Expiry

**Branch**: `011-spread-group-underlying` | **Date**: 2026-05-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/011-spread-group-underlying/spec.md`

## Summary

The positions table currently only groups option legs that have been manually assigned to a thesis group. This feature replaces that mechanism with automatic grouping by `(underlying_symbol, expiry_date)` — no configuration required. Two or more legs sharing the same underlying and expiry collapse into a single summary row labelled `"QQQ · 2026-06-20"`. All aggregation and expand/collapse behaviour carries over from feature 010. Only `positions_ui.js` changes; no backend or storage changes.

## Technical Context

**Language/Version**: Vanilla JS ES modules (no build pipeline, no framework)
**Primary Dependencies**: `position_cache.js`, `auth.js`, `account_picker.js` — `thesis_store.js` retained for thesis badges on leg rows but `getThesisGroups` import removed
**Storage**: No new storage. Expand/collapse state is in-memory (DOM only).
**Testing**: No frontend JS test framework exists. `buildSpreadGroups` is a pure function — verifiable via quickstart.md visual scenarios. See Complexity Tracking.
**Target Platform**: Web browser — desktop + mobile (Tailwind responsive classes required)
**Project Type**: Frontend UI feature — no backend changes
**Performance Goals**: Expand/collapse responds under 100ms (pure DOM toggle)
**Constraints**: No npm, no build step, no third-party JS libraries. ES modules only.
**Scale/Scope**: One file changed: `frontend/static/js/positions_ui.js` and its compiled copy `dist/static/js/positions_ui.js`.

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Privacy-First | ✅ Pass | No server changes. Grouping computed entirely from sessionStorage data already in the browser. No new data flows. |
| II. Security-First | ✅ Pass | Group labels rendered via `escapeHtml` (existing pattern). No new endpoints, no token handling. |
| III. Spec-Before-Code | ✅ Pass | Spec committed before any implementation. |
| IV. Test-First | ⚠️ Gap | No JS test framework exists. `buildSpreadGroups` written as a pure function to enable future unit testing. Visual verification documented in quickstart.md. See Complexity Tracking. |
| V. Simplicity Boundary | ✅ Pass | Single JS file change. `getThesisGroups` import removed (dead code eliminated). |
| VI. Visual & Responsive UI | ✅ Pass | Summary row and expanded leg rows use existing Tailwind classes. Mobile viewports unaffected. |

## Project Structure

### Documentation (this feature)

```text
specs/011-spread-group-underlying/
├── plan.md          ← this file
├── research.md      ← Phase 0 output
├── data-model.md    ← Phase 1 output
├── quickstart.md    ← Phase 1 output (visual verification — 8 scenarios)
└── tasks.md         ← Phase 2 output (/speckit-tasks command)
```

### Source Code (files changed)

```text
frontend/static/js/positions_ui.js   ← sole file modified
dist/static/js/positions_ui.js       ← compiled copy — kept in sync
```

No backend changes. No new files in `src/`. No new test files (see Complexity Tracking).

## Implementation Notes

### `buildSpreadGroups` rewrite

Old signature: `buildSpreadGroups(positions, assignments, thesisGroups)`
New signature: `buildSpreadGroups(positions)`

New logic:
1. Iterate positions; for each, compute `groupKey = encodeURIComponent(underlying_symbol + '|' + expiry_date)`.
2. Accumulate legs into `groupMap[groupKey]`.
3. Filter to groups with `legs.length >= 2`.
4. Standalone = positions not in any qualifying group.

### `renderPositions` changes

- Remove `getThesisGroups()` from import and call site.
- Pass only `positions` to `buildSpreadGroups`.
- Keep `getAssignments()` for thesis badges on expanded leg rows (unchanged).

### `renderSpreadRows` changes

- `data-spread-id` and `data-spread-toggle` attributes use `group.groupId` (the encoded key).
- `data-spread-leg` on leg rows uses `group.groupId`.
- Summary row label: `escapeHtml(group.groupName)` → e.g., `"QQQ · 2026-06-20"`.
- Expiry cell: `group.expiry` (always defined — no `?? '—'` needed).
- Underlying cell in summary row: `group.underlying` (always defined).

### `aggregateLegs` — no changes required

The existing function already handles all aggregation correctly. `sharedOrNull` on `expiry_date` will always resolve within a group (all legs share the same expiry by the grouping key invariant).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| IV. Test-First gap — no JS unit tests | No JS test framework exists. Adding one (Jest, Vitest) exceeds this feature's scope. | Installing a JS test framework requires build tooling that violates Principle V for this single feature. Pure function design enables testing when a framework is added. |
