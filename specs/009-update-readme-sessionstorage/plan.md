# Implementation Plan: README Storage Documentation Update

**Branch**: `009-update-readme-sessionstorage` | **Date**: 2026-05-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/009-update-readme-sessionstorage/spec.md`

## Summary

README.md contains stale storage documentation inherited from the IndexedDB era. The implementation
has since migrated position data and screener results to `sessionStorage`, and the constitution
(v3.2.0) was amended to mandate sessionStorage for all client-side trader data. This plan covers
the documentation edits required to bring README.md into alignment with the actual implementation
and the constitution — no source code or test changes are required.

## Technical Context

**Language/Version**: N/A (documentation-only change)
**Primary Dependencies**: N/A
**Storage**: N/A (the feature *documents* the storage model; it does not change it)
**Testing**: N/A — no executable code is modified
**Target Platform**: README.md (rendered on GitHub)
**Project Type**: Documentation update
**Performance Goals**: N/A
**Constraints**: README must remain accurate to `position_cache.js`, `screener_cache.js`, `thesis_store.js`, `auth.js`
**Scale/Scope**: Single file edit (`README.md`), 7 distinct locations

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Privacy-First Data Handling | ✅ Pass | This update *enforces* Principle I by correcting documentation to match the sessionStorage-only guarantee ratified in v3.2.0. |
| II. Security-First | ✅ Pass | No code changes; no security surface modified. |
| III. Spec-Before-Code | ✅ Pass | Spec committed before any README edit. |
| IV. Test-First | ✅ N/A | Documentation changes have no executable behaviour to test. |
| V. Simplicity Boundary | ✅ Pass | One file, minimum necessary edits. |
| VI. Visual & Responsive UI | ✅ N/A | Not applicable to documentation. |

No gate violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/009-update-readme-sessionstorage/
├── plan.md        ← this file
├── research.md    ← stale vs. correct storage mapping (Phase 0 output)
└── tasks.md       ← Phase 2 output (/speckit-tasks command)
```

### Files Modified

```text
README.md          ← sole file edited by this feature
```

No `data-model.md`, `contracts/`, or `quickstart.md` — this feature has no entities,
no interface contracts, and no setup steps.
