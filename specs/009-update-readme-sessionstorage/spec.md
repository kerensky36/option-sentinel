# Feature Specification: README Storage Documentation Update

**Feature Branch**: `009-update-readme-sessionstorage`
**Created**: 2026-05-15
**Status**: Draft
**Input**: User description: "update the readme.MD to reflect the way data is stored in sessionStorage and cleared on browser or tab close. the info on that page is now stale."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Developer reads accurate storage documentation (Priority: P1)

A developer (or the project owner) opens the README to understand how the app stores data in the browser. They need the documented storage locations and lifecycle to match the actual implementation so they can reason about privacy guarantees and debugging behaviour.

**Why this priority**: The README is the primary entry point for understanding the app's privacy model. Stale storage documentation erodes trust and causes confusion when the documented cleanup steps no longer work.

**Independent Test**: Open README.md and verify every storage-related claim (storage type, cleared-when conditions, code snippets, and tech stack entries) matches the actual JS implementation in `position_cache.js`, `screener_cache.js`, `thesis_store.js`, and `auth.js`.

**Acceptance Scenarios**:

1. **Given** a reader opens the "Where each piece of data lives" table, **When** they read the row for "Cached positions", **Then** the Location column says `sessionStorage` and the "Cleared when" column says "Tab/browser closed, or Erase All".
2. **Given** a reader opens the "Where each piece of data lives" table, **When** they scan all rows, **Then** no row references `IndexedDB` and a row for "Screener cache" exists with `sessionStorage` as the location.
3. **Given** a reader reads the login flow step 6, **When** they look at the cache description, **Then** it says `sessionStorage` (not `IndexedDB`) and describes tab-close clearing.
4. **Given** a reader reads the "Erase All Data" code snippet, **When** they examine the JavaScript, **Then** the `indexedDB.deleteDatabase(...)` line is removed, and only `sessionStorage.clear()`, `localStorage.clear()`, and the redirect remain.
5. **Given** a reader reads the Tech stack table, **When** they look at the Client storage row, **Then** `IndexedDB` is not listed.
6. **Given** a reader reads the stack badge at the top of the README, **When** they see the storage badge text, **Then** it does not reference `IndexedDB`.
7. **Given** a reader reads the Architecture diagram, **When** they see the browser-side comments, **Then** no `IndexedDB.put(positions)` reference appears.

---

### Edge Cases

- Thesis groups and thesis assignments still use `localStorage` (they persist across tab closes). The documentation must preserve this distinction — not all data clears on tab close.
- The "Erase All" behaviour for localStorage (thesis data) is unchanged; only the IndexedDB step is removed from the code snippet.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: README MUST accurately describe `sessionStorage` as the storage location for the Schwab token, cached positions, and screener cache results.
- **FR-002**: README MUST accurately describe `localStorage` as the storage location for thesis groups and thesis assignments.
- **FR-003**: README MUST state that `sessionStorage` data (token, positions cache, screener cache) is automatically cleared when the tab or browser is closed.
- **FR-004**: README MUST state that `localStorage` data (thesis groups, assignments) persists across tab closes and is only cleared by "Erase All" or a manual browser data clear.
- **FR-005**: README MUST remove all references to `IndexedDB` from prose, tables, code snippets, the architecture diagram, and the tech stack section.
- **FR-006**: README MUST update the "Erase All Data" JavaScript code snippet to remove the `indexedDB.deleteDatabase(...)` line.
- **FR-007**: README MUST add a row for "Screener cache" to the "Where each piece of data lives" table with location `sessionStorage` and cleared-when "Tab/browser closed, or Erase All".
- **FR-008**: README MUST update the stack badge at the top of the file to remove `IndexedDB` from the storage description.
- **FR-009**: README MUST update the architecture diagram browser-side annotations to remove `IndexedDB.put(positions)` and replace with a `sessionStorage`-accurate description.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every storage type mentioned in README.md matches the actual storage API calls in the JS source files — zero discrepancies.
- **SC-002**: The word "IndexedDB" does not appear anywhere in README.md after the update.
- **SC-003**: The "Erase All Data" code snippet in README.md executes correctly against the real app (no calls to APIs that no longer exist).
- **SC-004**: A reader can determine in under 30 seconds which data survives a tab close (thesis groups in localStorage) vs. which does not (everything in sessionStorage).

## Assumptions

- The implementation is already complete; this spec covers documentation-only changes to README.md.
- `thesis_store.js` uses `localStorage` and this has not changed — thesis data still persists across tab closes.
- The screener cache (`screener_cache.js`) uses `sessionStorage` and was not documented in the previous README; it needs to be added.
- Spread definitions and exit goals referenced in the old table are no longer relevant data types; they have been superseded by the current storage model.
- The README's "Project governance" constitution version reference does not need updating as part of this feature.
