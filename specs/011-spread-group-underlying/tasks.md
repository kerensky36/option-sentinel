# Tasks: Auto-Group Spreads by Underlying + Expiry

**Input**: Design documents from `specs/011-spread-group-underlying/`
**Branch**: `011-spread-group-underlying`
**Sole file changed**: `frontend/static/js/positions_ui.js` (+ `dist/` copy)

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

No new files, no new dependencies, no project structure changes required. Proceed directly to Phase 2.

---

## Phase 2: Foundational — Rewrite `buildSpreadGroups`

**Purpose**: Replace thesis-group-driven grouping with automatic `(underlying_symbol, expiry_date)` grouping. This is a blocking prerequisite for all render changes.

**⚠️ CRITICAL**: All user story phases depend on this.

- [x] T001 Rewrite `buildSpreadGroups` in `frontend/static/js/positions_ui.js` — new signature `buildSpreadGroups(positions)`, no thesis store arguments. For each position compute `groupKey = encodeURIComponent(p.underlying_symbol + '|' + p.expiry_date)`. Accumulate legs into `groupMap[groupKey]` initialised as `{ groupId: groupKey, groupName: p.underlying_symbol + ' · ' + p.expiry_date, underlying: p.underlying_symbol, expiry: p.expiry_date, legs: [], isExpanded: false }`. Filter groups to those with `legs.length >= 2`. Derive `standalone` as positions not in any qualifying group. Return `{ groups, standalone }`.

- [x] T002 Update `renderPositions` in `frontend/static/js/positions_ui.js` — change the `buildSpreadGroups` call from `buildSpreadGroups(positions, assignments, getThesisGroups())` to `buildSpreadGroups(positions)`. Remove the `getThesisGroups` import from the top of the file. Keep the `getAssignments` import (still used for thesis badges on expanded leg rows).

**Checkpoint**: `buildSpreadGroups` now groups by (underlying, expiry). `renderPositions` compiles without the removed import. No visual change yet because `renderSpreadRows` still uses old field names.

---

## Phase 3: User Story 1 — Auto-collapsed group rows (Priority: P1) 🎯 MVP

**Goal**: Positions on the same underlying+expiry render as one collapsed summary row, no thesis setup required.

**Independent Test**: Load positions with 2+ legs on the same underlying and expiry, confirm one collapsed row labelled `"QQQ · 2026-06-20"` appears instead of individual rows. Scenario 1 in quickstart.md.

- [x] T003 [US1] Update `renderSpreadRows` in `frontend/static/js/positions_ui.js` — replace `group.thesisGroupId` references with `group.groupId` in `data-spread-id` and the toggle button's `data-spread-toggle` attribute. Replace `escapeHtml(group.thesisGroupName)` with `escapeHtml(group.groupName)` in the Symbol cell.

- [x] T004 [US1] Update the leg rows in `renderSpreadRows` in `frontend/static/js/positions_ui.js` — replace `data-spread-leg="${group.thesisGroupId}"` with `data-spread-leg="${group.groupId}"` so the toggle listener targets the correct rows.

- [x] T005 [US1] Update the toggle event listener in `renderPositions` in `frontend/static/js/positions_ui.js` — confirm the `querySelectorAll(\`[data-spread-leg="${id}"]\`)` selector still works with the encoded `groupId` value (it queries by attribute, not CSS class — no change needed, but verify by reading the listener block and confirming no selector escaping issue exists with `encodeURIComponent` output).

**Checkpoint**: User Story 1 complete. Positions with 2+ legs on the same underlying+expiry appear as one collapsed group row. Verify Scenarios 1–3 in quickstart.md.

---

## Phase 4: User Story 2 — Aggregated metrics on summary row (Priority: P1)

**Goal**: Collapsed group row shows summed P&L, Delta, Gamma, Theta, Vega; shows "—" for Mark, Qty, Type, Strike, IV; always shows Expiry and Underlying.

**Independent Test**: Collapse a group, verify P&L is summed, Greeks are summed, non-additive columns show "—", Expiry shows the shared date. Scenario 7 in quickstart.md.

- [x] T006 [US2] Update the summary row HTML in `renderSpreadRows` in `frontend/static/js/positions_ui.js` — replace `${agg.underlying ?? '—'}` with `${group.underlying}` in the Underlying cell (always defined by grouping invariant). Replace `${agg.expiry ?? '—'}` with `${group.expiry}` in the Expiry cell (same reason). No change to P&L, Greeks, or "—" columns — `aggregateLegs` already handles those correctly.

**Checkpoint**: User Story 2 complete. Summary row always shows Underlying and Expiry. Verify Scenario 7 in quickstart.md.

---

## Phase 5: User Story 3 — Sub-group by underlying + expiry (Priority: P2)

**Goal**: Two QQQ positions with Jun expiry and two with Jul expiry appear as two separate collapsed rows.

**Independent Test**: Load positions with QQQ Jun × 2 and QQQ Jul × 2 — confirm two separate collapsed rows appear. Scenario 2 in quickstart.md.

*This story is delivered automatically by T001 — the `(underlying, expiry)` grouping key already creates separate groups per expiry. No additional implementation tasks required.*

- [ ] T007 [US3] Verify User Story 3 visually using Scenario 2 in `specs/011-spread-group-underlying/quickstart.md` — confirm two separate group rows appear for QQQ Jun and QQQ Jul. No code change required.

**Checkpoint**: User Story 3 confirmed. All three user stories now functional.

---

## Phase 6: Polish & Sync

**Purpose**: Sync the compiled dist copy and run the full visual verification suite.

- [x] T008 Sync `dist/static/js/positions_ui.js` — copy the updated `frontend/static/js/positions_ui.js` content into `dist/static/js/positions_ui.js` exactly (these two files must remain identical).

- [ ] T009 Run all 8 visual verification scenarios from `specs/011-spread-group-underlying/quickstart.md` in the browser against the local dev server. Record pass/fail for each scenario.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: No prerequisites — start here.
- **Phase 3 (US1)**: Depends on T001 + T002 (Phase 2 complete).
- **Phase 4 (US2)**: Depends on T003 + T004 (Phase 3 complete) — summary row render must exist before Expiry/Underlying fixes apply.
- **Phase 5 (US3)**: Depends on T001 only — grouping key is already correct; verification only.
- **Phase 6 (Polish)**: Depends on all implementation tasks complete (T001–T007).

### Within-Phase Dependencies

- T001 → T002 (call site updated after function signature changes)
- T003 → T004 (leg rows use the same `groupId` established in T003)
- T004 → T005 (toggle listener verified after both DOM attribute changes)
- T003 + T004 → T006 (summary row HTML update builds on existing `renderSpreadRows` structure)

### Parallel Opportunities

T008 and T009 can be done simultaneously if two sessions available (one syncs the file, one tests in browser). All other tasks are in the same file and must be sequential.

---

## Implementation Strategy

### MVP (User Stories 1 + 2 — both P1)

1. Complete Phase 2 (T001, T002) — rewrite grouping logic
2. Complete Phase 3 (T003, T004, T005) — fix group row attributes and labels
3. Complete Phase 4 (T006) — fix always-present Expiry/Underlying on summary row
4. **STOP and VALIDATE**: Run Scenarios 1, 3, 4, 5, 6, 7 from quickstart.md
5. Ship — this is the full value of the feature

### Incremental

1. After Phase 2: Grouping logic correct (invisible until render updated)
2. After Phase 3: Groups appear and expand/collapse correctly — MVP visible
3. After Phase 4: Summary row metrics always correct
4. After Phase 5: Multi-expiry grouping confirmed
5. After Phase 6: Dist synced and all 8 quickstart scenarios verified — ready to deploy

---

## Notes

- All tasks touch `frontend/static/js/positions_ui.js` — no parallel file editing possible
- `aggregateLegs` requires zero changes — it is already correct for this feature
- The toggle event listener requires no changes — it uses `getAttribute`, not CSS selectors, so encoded `groupId` values are safe
- After T008 both JS files must be byte-for-byte identical
