# Tasks: README Storage Documentation Update

**Input**: Design documents from `specs/009-update-readme-sessionstorage/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

**Organization**: Single user story — all tasks edit `README.md` only. No source code or test changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel
- **[Story]**: User story label

---

## Phase 1: User Story 1 — Accurate Storage Documentation (Priority: P1) 🎯

**Goal**: Every storage-related claim in README.md matches the actual JS implementation and the constitution (v3.2.0).

**Independent Test**: Open README.md and confirm the word "IndexedDB" does not appear anywhere; confirm the "Where each piece of data lives" table has a "Screener cache" row with `sessionStorage`; confirm the "Erase All Data" snippet has no `indexedDB.deleteDatabase(...)` line.

### Implementation

- [x] T001 [US1] Update the stack badge URL in README.md (line ~6) — replace `IndexedDB` with `sessionStorage` in the badge text so the shield reads `FastAPI + Vanilla JS + sessionStorage`
- [x] T002 [US1] Update login flow Step 6 in README.md — replace the IndexedDB description with sessionStorage; remove the "available instantly on page reload" claim (sessionStorage does not survive reload); clarify that the cache is cleared automatically when the tab or browser is closed
- [x] T003 [US1] Update the "Where each piece of data lives" table in README.md:
  - Change "Cached positions" row: Location → `Browser sessionStorage`, Cleared when → "Tab/browser closed, or Erase All"
  - Add new "Screener cache" row: Location → `Browser sessionStorage`, Cleared when → "Tab/browser closed, or Erase All"
  - Remove "Spread definitions" and "Exit goals" rows (no longer present in JS source)
- [x] T004 [US1] Update the "Erase All Data" JavaScript code snippet in README.md — remove the `indexedDB.deleteDatabase('option-sentinel')` line; keep `sessionStorage.clear()`, `localStorage.clear()`, and `window.location.replace('/auth/login')`
- [x] T005 [US1] Update the Tech stack table in README.md — change the "Client storage" row from `sessionStorage + IndexedDB + localStorage` to `sessionStorage + localStorage`
- [x] T006 [US1] Update the Architecture diagram in README.md — replace `IndexedDB.put(positions)` browser-side annotation with `sessionStorage.setItem(positions)`
- [x] T007 [US1] Final check: search README.md for any remaining occurrence of "IndexedDB" or "indexedDB" and remove or correct each one

**Checkpoint**: README.md contains zero references to IndexedDB; all storage claims match JS source; Screener cache row is present; Erase All snippet is accurate.

---

## Dependencies & Execution Order

- **T001–T006**: All edit different sections of the same file. Work sequentially top-to-bottom through the file to avoid conflicting edits.
- **T007**: Must run last — it's the verification sweep after all other edits.

### Parallel Opportunities

None — all tasks edit the same file. Execute sequentially.

---

## Implementation Strategy

### MVP (only story — complete all tasks)

1. Complete T001–T006 in order (top-to-bottom through README.md)
2. Run T007 verification sweep
3. **STOP and VALIDATE**: `grep -i "indexeddb" README.md` should return no results
4. Commit

---

## Notes

- All edits are in `README.md` at the repository root
- No source code, no tests, no new files
- Thesis group / localStorage rows are correct and must be preserved
- sessionStorage data (token, positions, screener cache) clears on tab close — localStorage data (thesis groups) does not
