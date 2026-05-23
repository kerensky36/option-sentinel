# Tasks: Option Position Payoff Graphs (015)

**Input**: Design documents from `specs/015-payoff-graphs/`
**Branch**: `015-payoff-graphs`

---

## Phase 1: Setup

**Purpose**: Confirm project structure is ready; no new dependencies required.

- [X] T001 Confirm `frontend/static/js/payoff_math.js` and `frontend/static/js/payoff_graph.js` do not yet exist (run `ls frontend/static/js/payoff*.js` — should fail)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Python TDD anchor for payoff math + core math module. MUST complete before any user story begins.

**⚠️ CRITICAL**: Constitution §IV requires tests written and confirmed failing before implementation.

- [X] T002 Write failing Python unit tests for payoff math in `tests/unit/test_payoff_math.py` covering: `leg_payoff_per_share` for short put (qty=-1, cost=-3.85, K=195), long call (qty=+1, cost=+2.50, K=220), short call (qty=-1, cost=-3.20, K=220), long put (qty=+1, cost=+1.95, K=185); `combined_payoff` for a 2-leg bull put spread (short put K=195 + long put K=185); `analyze_payoff` max gain ≈ 1.90/share, max loss ≈ -8.10/share for the same spread. Run `pytest tests/unit/test_payoff_math.py` and confirm ALL tests fail (ImportError or AssertionError is expected).
- [X] T003 Implement `frontend/static/js/payoff_math.js` — pure ES module, zero imports, three exports: `legPayoffPerShare(leg, price)` using formula `sign(qty) * intrinsic - cost` (see research.md D-002), `combinedPayoff(legs, price)` summing all legs, `analyzePayoff(legs)` returning `{maxGain, maxLoss, breakevens, strikePrices, curve}` by scanning 200 price points over range `[minStrike*0.65, maxStrike*1.35]`. Verify Python tests now pass: `pytest tests/unit/test_payoff_math.py -v`.

**Checkpoint**: `test_payoff_math.py` all green. Core math is validated before any UI work begins.

---

## Phase 3: User Story 1 — Spread Group Click → Payoff Graph (Priority: P1) 🎯 MVP

**Goal**: Clicking a spread group summary row shows an inline SVG payoff diagram with max gain/loss annotations, per-leg strike markers, and zero line. Escape key or second click dismisses it.

**Independent Test**: Open demo mode (Options Spreads account), click the "AAPL · 2025-07-18" spread row — payoff graph appears. Click again — it disappears. (Quickstart Scenarios 1–3.)

- [X] T004 [US1] Implement `buildPayoffSvg(legs, opts)` in `frontend/static/js/payoff_graph.js` — imports from `./payoff_math.js`; calls `analyzePayoff(legs)`; returns SVG string with viewBox `0 0 800 180`; renders: transparent background, zero line (dashed `#4b5563`), payoff polyline (`#e5e7eb`), per-leg vertical strike lines (dashed `#6b7280`) with price labels, max gain annotation (text + tick in `#4ade80`), max loss annotation (`#f87171`), x-axis with 5 price labels, y-axis with 4 P&L labels, title text top-left in `#9ca3af` 10px `JetBrains Mono`. No `<script>` elements, no event handlers in SVG markup.
- [X] T005 [US1] Implement `initPayoffGraphToggle(container, positionData)` in `frontend/static/js/payoff_graph.js` — where `positionData = { groups: Array, standalone: Array }` (raw group/position objects from positions_ui.js); adds a delegated `click` listener on `container.querySelector('tbody')`; for clicks on `[data-spread-id]` rows that are NOT on `[data-spread-toggle]` targets: (a) if `openGraphId` is set, remove that graph row from the DOM; (b) if clicking the same row again, clear `openGraphId` and return (toggle off); (c) otherwise normalise `group.legs` to PayoffLeg format (`{ strike: parseFloat(p.strike), optionType: p.option_type, quantity: p.quantity, cost: parseFloat(p.cost) }`), call `buildPayoffSvg`, insert a `<tr class="payoff-graph-row" id="payoff-{groupId}"><td colspan="15" class="px-4 py-3 bg-gray-900/60">{svg}</td></tr>` immediately after the spread summary row, set `openGraphId`. Store the `Escape` handler reference in module scope so it can be removed on re-init.
- [X] T006 [US1] Add Escape key handler in `frontend/static/js/payoff_graph.js` — inside `initPayoffGraphToggle`, after registering the click listener, attach a `keydown` handler on `document` that calls the close logic when `e.key === 'Escape'` and `openGraphId` is set. Remove the previous Escape handler if `initPayoffGraphToggle` is called again (re-render path). Export `closeOpenGraph()` for use by external callers (e.g. when positions table is refreshed).
- [X] T007 [US1] Modify `frontend/static/js/positions_ui.js`: (a) add `import { initPayoffGraphToggle } from './payoff_graph.js';` at top of file; (b) in `renderPositions`, after `container.innerHTML = ...`, call `initPayoffGraphToggle(container, { groups, standalone });`. Note: `groups` and `standalone` are already defined in `renderPositions` scope from the `buildSpreadGroups` call.
- [X] T008 [US1] Run `pytest tests/ -q` and confirm all existing tests still pass (no regressions from positions_ui.js changes). Browser-test Quickstart Scenarios 1–4 in demo mode.

**Checkpoint**: Spread group rows show payoff graphs on click. Single-graph constraint works. Escape key works.

---

## Phase 4: User Story 2 — Standalone Single-Leg Row Click (Priority: P2)

**Goal**: Clicking a standalone option row (covered call, naked put, etc.) shows the same payoff graph experience as a spread group. The graph shows the single-leg payoff profile with strike marker, breakeven, and max gain/loss annotations.

**Independent Test**: Open demo mode (Equities & ETFs account), click the AAPL covered call row — a payoff graph appears showing the short call profile. (Quickstart Scenario 6.)

- [X] T009 [US2] Modify `renderLegRow` in `frontend/static/js/positions_ui.js` to add four data attributes to the standalone `<tr>`: `data-position-id="${escapeHtml(p.symbol)}"`, `data-pos-underlying="${escapeHtml(p.underlying_symbol)}"`, `data-pos-expiry="${escapeHtml(p.expiry_date)}"`, `data-pos-strike="${escapeHtml(String(p.strike))}"`. These are consumed by `initPayoffGraphToggle` without any DOM text parsing.
- [X] T010 [US2] Extend `initPayoffGraphToggle` in `frontend/static/js/payoff_graph.js` to handle `[data-position-id]` standalone row clicks: for clicks on a row with `data-position-id` (and NOT on any toggling child): find the matching position from `positionData.standalone` by comparing `p.symbol` to the `data-position-id` attribute value; normalise to a single-element legs array; call `buildPayoffSvg`; insert graph `<tr>` after the standalone row with `id="payoff-{encodeURIComponent(symbol)}"`. The same `openGraphId` state and single-graph constraint applies.
- [X] T011 [US2] Browser-test Quickstart Scenarios 6–7 in demo mode (Equities & ETFs account for single-leg, chevron-vs-row-click independence). Confirm chevron toggle still works independently (Scenario 7).

**Checkpoint**: Both spread rows and standalone option rows show payoff graphs. Chevron expand still works.

---

## Phase 5: User Story 3 — Grouped Spread Combined Payoff (Priority: P3)

**Goal**: For groups with more than two legs (e.g. a 4-leg iron condor), the payoff graph correctly shows all four strike markers and the combined P&L curve. De-duplicated strike labels do not visually overlap.

**Independent Test**: Add a 4-leg iron condor group to demo spreads data, click its group row, verify four distinct strike lines appear and max gain/max loss match analytical values.

- [X] T012 [US3] Add a 4-leg iron condor to `DEMO_POSITIONS_SPREADS` in `frontend/static/js/demo_data.js`: short SPY put K=540 (qty=-1, cost=-2.20), long SPY put K=530 (qty=+1, cost=+1.40), short SPY call K=575 (qty=-1, cost=-2.50), long SPY call K=585 (qty=+1, cost=+1.60), all with expiry `2025-08-15`. Update `DEMO_POSITIONS_SPREADS` count and update `_DEMO_POSITIONS_SPREADS` in `tests/contract/test_demo_mode_contract.py` to mirror (add same 4 entries; update `test_count` to 10 from 6).
- [X] T013 [US3] In `frontend/static/js/payoff_graph.js` (`buildPayoffSvg`): verify that strike line rendering handles N legs (loop over `analysis.strikePrices` array, not just two strikes). Add label stagger: if two strike prices are within 3% of the x-axis range, offset their labels vertically (one at y+12, next at y+24) so they do not overlap.
- [X] T014 [US3] Run `pytest tests/ -q` to confirm contract tests pass with the new iron condor entries. Browser-test Quickstart Scenario 5 with the newly added iron condor: confirm 4 strike lines appear, max gain ≈ +1.70/share (net premium: 2.20+2.50-1.40-1.60 = 1.70), max loss ≈ -8.30/share (spread width 10 - 1.70 = 8.30).

**Checkpoint**: All three user stories independently functional. Iron condor payoff renders correctly.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T015 Run full Quickstart verification: open demo mode and step through all 10 scenarios in `specs/015-payoff-graphs/quickstart.md`. Document any failures.
- [X] T016 [P] Visual polish pass on `frontend/static/js/payoff_graph.js`: confirm font-family renders as `JetBrains Mono` (add `monospace` fallback); confirm SVG `width: 100%` CSS is applied to the container cell so the graph fills the table row on both wide and narrow viewports; confirm no white/light backgrounds visible on dark theme.
- [X] T017 [P] Run `pytest tests/ -q` — full suite must pass. Confirm 10+ tests from `test_payoff_math.py`, no regressions elsewhere.
- [X] T018 Verify the positions table refresh (clicking Refresh while a graph is open) closes the open graph cleanly: `closeOpenGraph()` must be called at the start of `renderPositions` in `frontend/static/js/positions_ui.js` before resetting `innerHTML`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1. BLOCKS all user stories. T003 depends on T002 (tests must fail first).
- **Phase 3 (US1)**: Depends on Phase 2 completion (payoff_math.js must exist)
- **Phase 4 (US2)**: Depends on Phase 3 (extends payoff_graph.js initialised in US1)
- **Phase 5 (US3)**: Depends on Phase 3 (extends buildPayoffSvg from US1)
- **Phase 6 (Polish)**: Depends on all desired user stories complete

### User Story Dependencies

- **US1**: Depends on Foundational (payoff_math.js). No dependency on US2/US3.
- **US2**: Depends on US1 (extends `initPayoffGraphToggle` already created). Can start once T005 is complete.
- **US3**: Depends on US1 (extends `buildPayoffSvg` already created). Can start once T004 is complete.

### Within Each Story

- Tests (T002) MUST be written and CONFIRMED FAILING before T003 implementation
- `payoff_math.js` (T003) must exist before `payoff_graph.js` work begins (T004)
- T004 (`buildPayoffSvg`) must exist before T005 (`initPayoffGraphToggle`) can call it
- T005/T006 must exist before T007 (positions_ui.js import wiring)

### Parallel Opportunities

- T004 and T009 are separate tasks but both modify `payoff_graph.js` — run sequentially
- T015, T016, T017 can be run in parallel in Phase 6

---

## Parallel Example: Phase 3 + Phase 5

```
After Phase 2 completes:
  Dev path A: T004 → T005 → T006 → T007 → T008 (US1 complete)
  Dev path B: T012 (demo data for iron condor) — can start in parallel with T004
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1 (trivial)
2. Complete Phase 2 (TDD + payoff_math.js)
3. Complete Phase 3 (US1: spread group graphs)
4. **STOP and VALIDATE**: Browser-test Scenarios 1–4 from quickstart.md
5. Deploy to production if MVP is satisfactory

### Full Delivery

1. MVP (above) → US2 (standalone rows) → US3 (iron condor 4-leg) → Polish

---

## Notes

- All JS files are in `frontend/static/js/` — no build step, ES modules loaded directly by browser
- No new Python dependencies; no backend changes
- `payoff_math.js` has zero imports — safe to test in isolation
- The Python unit tests in `test_payoff_math.py` validate the same arithmetic the JS implements — they act as a specification and regression guard
- `colspan="15"` matches the current 15-column positions table (Symbol, Underlying, Type, Strike, Expiry, Qty, Mark, P&L, DTE, Delta, Gamma, Theta, Vega, IV, Thesis)
- If the columns change, the colspan value must be updated in `payoff_graph.js`
