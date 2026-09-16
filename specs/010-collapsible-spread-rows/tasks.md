# Tasks: Collapsible Spread Rows

**Input**: Design documents from `specs/010-collapsible-spread-rows/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅
**Clarification applied**: Toggle is icon-only — only the ▶/▼ chevron button is clickable (FR-003, Session 2026-05-16).

**File changed**: `frontend/static/js/positions_ui.js` (+ `dist/` copy)
**No backend changes. No new files.**

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (no shared-file dependency with concurrent tasks)
- **[Story]**: User story label

---

## Phase 2: Foundational — Pure Helper Functions

**Purpose**: Two standalone pure functions that both user stories depend on. Must be complete before any rendering changes.

**⚠️ CRITICAL**: Phases 3 and 4 cannot begin until both T001 and T002 are complete.

- [x] T001 [P] Add `buildSpreadGroups(positions, assignments, thesisGroups)` pure function in `frontend/static/js/positions_ui.js` — iterates positions, maps each to its thesis group via assignments, groups positions by `thesis_group_id`, retains only groups with 2+ matching positions (single leg is not a spread), returns `{ groups: [{thesisGroupId, thesisGroupName, legs, isExpanded: false}], standalone: Position[] }` where `standalone` contains all positions not belonging to a qualifying group
- [x] T002 [P] Add `aggregateLegs(legs)` pure function in `frontend/static/js/positions_ui.js` — accepts a `legs` array and returns an `AggregatedRow` object per research.md Decision 3: `pnl = sum(unrealised_pnl)`, `delta/gamma/theta/vega = sum of non-null values (null if all null)`, `hasBsGreek = { delta: bool, gamma: bool, theta: bool, vega: bool }` where each is true if any contributing leg has `{greek}_source === 'calculated'`, `underlying = shared value or null`, `expiry = shared value or null`, `dte = shared value or null`

**Checkpoint**: Both pure functions exist and are independently callable. No rendering changes yet.

---

## Phase 3: User Story 1 — Grouped and Collapsed by Default (Priority: P1) 🎯

**Goal**: Positions table renders spread groups as single collapsed rows with a chevron toggle; standalone positions render unchanged.

**Independent Test**: quickstart.md SC1 (collapsed by default), SC2 (expand via chevron), SC3 (collapse via chevron), SC4 (non-spread unaffected), SC9 (single-leg no toggle), SC10 (reset on refresh).

### Implementation

- [x] T003 [US1] Add `import { getThesisGroups } from './thesis_store.js'` at the top of `frontend/static/js/positions_ui.js` — `getThesisGroups` is not currently imported; `getAssignments` is already imported and stays
- [x] T004 [US1] Refactor `renderPositions()` in `frontend/static/js/positions_ui.js` — call `buildSpreadGroups(positions, getAssignments(), getThesisGroups())` before building table rows; replace the single `positions.map(...)` with two render passes: one for `groups` (summary row + hidden leg rows) and one for `standalone` (individual rows, unchanged logic)
- [x] T005 [US1] Render spread summary rows in `frontend/static/js/positions_ui.js` — each summary `<tr>` gets `data-spread-id="{thesisGroupId}"`; the Symbol cell contains a `<button data-spread-toggle="{thesisGroupId}" class="...">▶</button>` followed by the thesis group name escaped via an inline replace chain (mirroring the `escapeHtml` pattern in thesis_ui.js: `str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')`); non-aggregated columns (Type, Strike, Qty, Mark, IV) render the literal string `—`; apply a distinct row style (e.g., `bg-gray-800/60 font-medium`) to visually separate summary rows from leg rows
- [x] T006 [US1] Render leg rows in `frontend/static/js/positions_ui.js` — each leg `<tr>` gets `data-spread-leg="{thesisGroupId}"` and the `hidden` CSS class so it is invisible on initial render; indent the Symbol cell with `pl-5` padding to signal parent-child relationship; all other leg columns render exactly as they do today for individual rows (no change to column logic)
- [x] T007 [US1] Add chevron-scoped click handler in `renderPositions()` in `frontend/static/js/positions_ui.js` — after setting `container.innerHTML`, attach a single delegated `click` listener on the table `<tbody>`; on click, check `event.target.closest('[data-spread-toggle]')`; if found, read `thesisGroupId` from that attribute; toggle the `hidden` class on all `tr[data-spread-leg="{thesisGroupId}"]` rows; swap the button text between `▶` and `▼`; call `event.stopPropagation()` to prevent the click from bubbling to the row — clicking anywhere else on the summary row does nothing (FR-003, clarification 2026-05-16)

**Checkpoint**: Table renders spread groups as collapsed summary rows. Chevron-only toggle expands/collapses legs. Clicking row body does nothing. Standalone positions unchanged. Run quickstart.md SC1–SC4, SC9, SC10.

---

## Phase 4: User Story 2 — Aggregated Metrics on Summary Row (Priority: P1)

**Goal**: Collapsed summary row shows real aggregated values for P&L and Greeks; "—" for non-additive columns; shared values for Underlying/Expiry/DTE where applicable.

**Independent Test**: quickstart.md SC5 (P&L sum), SC6 (Greeks sum), SC7 (non-additive "—"), SC8 (shared columns), SC11 (mobile viewport).

### Implementation

- [x] T008 [US2] Wire `aggregateLegs(group.legs)` result into spread summary row rendering in `frontend/static/js/positions_ui.js` — populate P&L cell using `formatPnl(agg.pnl)` (green/red with sign); populate Delta, Gamma, Theta, Vega cells using `fmt(value, 4)` with `sourceBadge('calculated')` appended when `agg.hasBsGreek[greek]` is true; show `—` (em-dash) when aggregated value is null (all legs were null for that Greek)
- [x] T009 [US2] Populate shared-value columns on the summary row in `frontend/static/js/positions_ui.js` — Underlying: `agg.underlying ?? '—'`; Expiry: `agg.expiry ?? '—'`; DTE: `agg.dte !== null ? agg.dte + 'd' : '—'`; render all values in the same column order as individual rows to maintain table alignment

**Checkpoint**: Run quickstart.md SC5–SC8. P&L and Greeks match manual sums. Non-additive columns show "—". Run all 11 quickstart scenarios for full pass.

---

## Phase 5: Polish & Distribution Sync

**Purpose**: Keep dist/ in sync and confirm full verification pass.

- [x] T010 Copy the updated `frontend/static/js/positions_ui.js` to `dist/static/js/positions_ui.js` to keep the production distribution in sync (no build pipeline — manual copy required per research.md Decision 5)
- [ ] T011 Run all 11 scenarios from `specs/010-collapsible-spread-rows/quickstart.md` against `http://localhost:8000` and confirm each passes; record any failures with scenario number

**Checkpoint**: All 11 quickstart scenarios pass. Feature is complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately. T001 and T002 are logically parallel but edit the same file; write sequentially.
- **US1 (Phase 3)**: Requires T001 and T002. T003 → T004 → T005 → T006 → T007 (sequential, same file).
- **US2 (Phase 4)**: Requires T004 (renderPositions refactored). T008 and T009 are logically parallel but edit the same function; write sequentially.
- **Polish (Phase 5)**: T010 requires all Phase 3 + 4 tasks. T011 requires T010.

### Execution Graph

```
T001 ──┐
       ├──► T003 ──► T004 ──► T005 ──► T006 ──► T007 ──┐
T002 ──┘                               T008 ──┐         ├──► T010 ──► T011
                                       T009 ──┘         │
                                                         │
                                       (T008/T009 after T004)
```

---

## Implementation Strategy

### MVP (all tasks — US1 and US2 are inseparable)

1. Write T001 + T002 (pure helpers — no visible change to UI)
2. T003–T007 (US1: grouping, rendering, chevron-only toggle)
3. Verify SC1–SC4 + SC9 + SC10 pass
4. T008–T009 (US2: aggregated values in summary row)
5. Verify all 11 quickstart scenarios pass
6. T010 dist sync → T011 final verification

---

## Notes

- **Chevron is the only click target** — `event.target.closest('[data-spread-toggle]')` in T007; clicking the `<tr>` body does nothing (FR-003 clarified 2026-05-16)
- All edits are in `frontend/static/js/positions_ui.js` — work sequentially to avoid in-file conflicts
- `getThesisGroups` must be imported (T003); `getAssignments` is already imported
- Thesis group name MUST be HTML-escaped before insertion (XSS prevention, Principle II)
- `dist/static/js/positions_ui.js` must match `frontend/static/js/positions_ui.js` exactly after T010
- No backend changes, no new test files, no new dependencies beyond the existing `thesis_store.js` import
