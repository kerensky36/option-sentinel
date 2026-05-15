# Tasks: ThinkorSwim-Style UI Redesign

**Input**: Design documents from `specs/008-tos-ui-redesign/`
**Branch**: `008-tos-ui-redesign`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: User Story 1 — Dense Information Layout on Desktop (P1)
- **[US2]**: User Story 2 — Consistent Typography Across All Pages (P1)
- **[US3]**: User Story 3 — Responsive Layout on Tablet and Mobile (P2)

---

## Phase 1: Foundational — Fix the Type Scale (Blocking Prerequisite)

**Purpose**: Establish the three-tier type scale in Tailwind config and CSS-block rules.
All inline-override removal tasks in subsequent phases depend on these changes being in place first.

**⚠️ CRITICAL**: Complete T001 before beginning T003–T010. T002 is parallel to T001 (different file).

- [x] T001 Fix Tailwind fontSize config block and CSS-block font-size values in `frontend/templates/base.html` — in the `<script nonce>` Tailwind config, replace the entire `fontSize` object with: `'xs':['9px',{lineHeight:'1.4'}]`, `'sm':['11px',{lineHeight:'1.4'}]`, `'base':['12px',{lineHeight:'1.5'}]`, `'lg':['13px',{lineHeight:'1.4'}]`, `'xl':['14px',{lineHeight:'1.4'}]`, `'2xl':['16px',{lineHeight:'1.3'}]`, `'3xl':['18px',{lineHeight:'1.3'}]`; in the `<style>` block update: `body { font-size: 11px }`, `table { font-size: 11px }`, `table th { font-size: 9px !important }`, `input[type="number"], input[type="text"], select { font-size: 11px }`, `.nav-section-label { font-size: 9px }`, `.nav-item { font-size: 11px }`

- [x] T002 [P] Fix Tailwind fontSize config block and body font-size in `frontend/templates/login.html` — replace the `fontSize` object in the `<script nonce>` Tailwind config with the identical values as T001; in the `<style>` block change `body { font-size: 20px }` to `body { font-size: 11px }`

**Checkpoint**: Open any page in browser DevTools Console and run `tailwind.config.theme.extend.fontSize` — confirm xs=9px, sm=11px. Run `document.querySelectorAll('[style*="font-size"]').length` — count will still be non-zero (inline overrides not yet removed); that is expected at this stage.

---

## Phase 2: User Story 1 — Dense Information Layout on Desktop (Priority: P1) 🎯

**Goal**: Remove all `style="font-size:..."` inline overrides from `base.html`'s HTML section
(nav bar, buttons, mobile nav strip, sidebar), completing the dense desktop layout.

**Independent Test**: Open the Dashboard on desktop. Run `document.querySelectorAll('[style*="font-size"]').length` in DevTools Console — result must be zero for elements in the base nav/sidebar.

- [x] T003 [US1] Remove all `style="font-size:..."` inline overrides from the HTML body of `frontend/templates/base.html` — (1) on the account-row `<div>`: remove `style="font-size:18px"` entirely; (2) on `<select id="account-picker">`: remove `style="font-size:15px;"` (the input CSS rule covers it); (3) on `<button id="erase-all-btn">`: remove `style="font-size:15px"` and add `text-xs` to the existing class string; (4) on the Disconnect `<button>`: remove `style="font-size:15px"` and add `text-xs` to class; (5) on both mobile nav `<a>` links: remove `style="font-size:15px; ..."` keeping only the non-font-size inline styles (color, border-bottom, margin, border-radius remain); (6) on the sidebar footer `<div class="nav-section-label">`: remove `style="padding-bottom:10px; font-size:15px; color:#252532"` and replace with `style="padding-bottom:10px; color:#252532"` (the .nav-section-label CSS rule covers font-size)

**Checkpoint**: `pytest tests/ -q` still passes. Open Dashboard in browser — nav labels, buttons, and mobile strip should be visually compact at ~9–11px.

---

## Phase 3: User Story 2 — Consistent Typography Across All Pages (Priority: P1)

**Goal**: Remove every remaining `style="font-size:..."` inline override from all templates,
partials, and JS render functions. After this phase, zero inline font-size overrides exist
in the entire codebase.

**Independent Test**: On any page, run `document.querySelectorAll('[style*="font-size"]').length` in DevTools — result must be `0`.

- [x] T004 [P] [US2] Remove all `style="font-size:..."` inline overrides from `frontend/templates/login.html` HTML section — (1) subtitle span: remove `style="font-size:15px; letter-spacing:0.18em;"`, keep `style="letter-spacing:0.18em"`, add `text-xs` to class; (2) error div: remove `style="font-size:18px; border-radius:1px"`, add `text-sm` to class, keep `style="border-radius:1px"`; (3) h1: remove `style="font-size:20px; letter-spacing:0.12em;"`, add `text-lg` to class, keep `style="letter-spacing:0.12em"`; (4) body copy `<p>`: remove `style="font-size:18px; line-height:1.7;"`, add `text-sm` to class, keep `style="line-height:1.7"`; (5) checklist `<ul>`: remove `style="font-size:15px; list-style:none; padding:0;"`, add `text-xs` to class, keep `style="list-style:none; padding:0"`; (6) Connect button `<a>`: remove `style="font-size:18px; letter-spacing:0.14em; border-radius:1px; text-decoration:none;"`, add `text-sm` to class, keep remaining non-font style attrs; (7) Dev Login `<a>`: remove `style="font-size:15px; ..."`, add `text-xs`, keep remaining; (8) footer `<p>`: remove `style="font-size:15px; letter-spacing:0.08em;"`, add `text-xs`, keep `style="letter-spacing:0.08em"`

- [x] T005 [P] [US2] Remove all `style="font-size:..."` inline overrides from `frontend/templates/dashboard.html` — toolbar title span → add `text-xs`; timestamp span → add `text-xs`; Refresh button → add `text-xs`; loading placeholder span → add `text-sm`; Thesis Groups summary → add `text-xs`; three form `<label>` elements → add `text-xs` each; three form `<input>`/`<select>` elements → remove `style="font-size:18px"` (CSS input rule covers them); `+ Add` button → add `text-xs`

- [x] T006 [P] [US2] Remove all `style="font-size:..."` inline overrides from `frontend/templates/screener.html` — toolbar title span → add `text-xs`; Refresh button → add `text-xs`; details summary → add `text-xs`; three scoring card title divs → add `text-sm` to each; three scoring card body divs → add `text-xs` to each; footer section container → add `text-xs`; three footer label `<span>` elements → add `text-xs` each; screener placeholder span → add `text-sm`

- [x] T007 [P] [US2] Remove all `style="font-size:..."` inline overrides from `frontend/templates/partials/thesis_cards.html` — alignment badge `<span>` elements (aligned/partially_aligned/misaligned/unrated): remove `style="border-radius:1px"` (global rule covers it), verify `text-xs` is already in class; template badge `<span>`: same treatment; stats row labels (`Positions`, `Avg Score`, `P&L`): verify `text-xs` class present, no inline font; stats row values and chevron: verify `text-sm` or `text-xs` class present; loading div: verify `text-xs` class present

- [x] T008 [P] [US2] Remove all `style="font-size:..."` inline overrides from `frontend/templates/partials/screener_table.html` — status badge `<span>` elements (ranked/earnings_risk/call_written/no_liquid_options): remove `style="border-radius:1px"`, verify `text-xs` in class; error state div: verify `text-xs`/`text-sm` classes; empty-state div: verify `text-xs` class; last-refreshed div: verify `text-xs` class

- [x] T009 [P] [US2] Remove all `style="font-size:..."` inline overrides from `frontend/templates/partials/positions_table.html` — empty-state div: replace `style="font-size:18px"` (or equivalent) with `text-sm` class

- [x] T010 [P] [US2] Remove all `style="font-size:..."` inline style strings from JS template literals in `frontend/static/js/positions_ui.js` — (1) BS source badge span: replace `style="font-size:9px"` with `text-xs` in class; (2) empty-state div: replace `style="font-size:12px"` with `text-sm` in class; (3) thesis badge span: replace `style="font-size:10px"` with `text-xs` in class; (4) symbol `<td>`: remove `style="font-size:11px"` (inherits body 11px); (5) option-type `<td>`: replace `style="font-size:10px"` with `text-xs` in class; (6) thead `<tr>`: replace `style="font-size:10px; letter-spacing:0.10em;"` by adding `text-xs tracking-wider` to class and removing style attr; (7) error div: replace `style="font-size:12px"` with `text-sm` in class; (8) retry button: replace `style="font-size:10px"` with `text-xs` in class

- [x] T011 [P] [US2] Remove all `style="font-size:..."` inline style strings from JS template literals in `frontend/static/js/screener_ui.js` — the three status badge spans in `statusBadge()` (recommended/suppressed/insufficient_data): for each, remove any `style="font-size:9px; border-radius:1px"` and verify `text-xs` is in the class attribute

- [x] T012 [P] [US2] Remove all `style="font-size:..."` inline style strings from JS template literals in `frontend/static/js/thesis_ui.js` — (1) empty-state `<p>`: verify `text-sm` class present, no inline font; (2) thesis name `<span>`: verify `text-sm` class present; (3) template type `<span>`: keep `style="letter-spacing:0.08em;"` only, add `text-xs` to class; (4) description `<span>`: verify `text-sm` class present; (5) delete `<button>`: verify `text-xs` class present

**Checkpoint**: On any page, `document.querySelectorAll('[style*="font-size"]').length` returns `0`.

---

## Phase 4: User Story 3 — Responsive Layout on Tablet and Mobile (Priority: P2)

**Goal**: Confirm the new type scale renders correctly on mobile viewports with no regressions.
No code changes are expected here — this phase is a structured manual verification.

**Independent Test**: Open DevTools → device toolbar → 375px width. All criteria in quickstart.md pass.

- [x] T013 [US3] Verify mobile layout at 375px and 768px per `specs/008-tos-ui-redesign/quickstart.md` — open DevTools on Login, Dashboard, and Screener pages at 375px; confirm: (a) no `font-size` inline style attrs in DOM (run the console check), (b) login page has no horizontal scroll and all elements are reachable, (c) mobile nav strip is visible on Dashboard and Screener, (d) no text element reads below 9px in Computed styles. If any check fails, trace the element and fix the relevant task (T003–T012) before marking T013 complete.

---

## Phase 5: Polish & Validation

- [x] T014 Run full regression suite `pytest tests/ -q` — confirm all backend tests still pass (this is a frontend-only change; no regressions are expected)

---

## Dependencies & Execution Order

```
T001 ──┬──► T003 ──► T013
       │
T002 ──┤    T004 [P]
       │    T005 [P]
       │    T006 [P]
T001 ──┴──► T007 [P]  ──► T013 ──► T014
            T008 [P]
            T009 [P]
            T010 [P]
            T011 [P]
            T012 [P]
```

- T001 and T002 are parallel (different files); both must complete before US2 tasks
- T003 depends on T001 (same file, different sections)
- T004–T012 depend on T001+T002 complete (reference the corrected Tailwind scale)
- T004–T012 are mutually parallel (each touches a different file)
- T013 depends on T003–T012 complete (manual verification after all changes)
- T014 can run any time after T001 (backend tests unaffected; running last confirms nothing regressed)

## Parallel Execution Examples

**Round 1** (foundational, parallel): T001 + T002

**Round 2** (US1 + US2 inline removals, all parallel after Round 1): T003 + T004 + T005 + T006 + T007 + T008 + T009 + T010 + T011 + T012

**Round 3** (verification): T013

**Round 4**: T014

---

## Implementation Strategy

### MVP (entire feature is the MVP — US1 + US2 are both P1)

1. T001 + T002: Fix font scale config (biggest visual impact, ~10 line changes each)
2. T003: Remove base.html nav inline overrides
3. T004–T012: Remove remaining inline overrides from all templates, partials, and JS
4. T013: Mobile verification pass
5. T014: Backend regression

Total: 14 tasks, ~2 hours, 10 files changed.
