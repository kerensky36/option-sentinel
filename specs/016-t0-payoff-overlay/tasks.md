# Tasks: T+0 Payoff Overlay (016)

**Input**: Design documents from `specs/016-t0-payoff-overlay/`
**Branch**: `016-t0-payoff-overlay`

---

## Phase 1: Setup

**Purpose**: Confirm the new module doesn't already exist; no new dependencies required.

- [X] T001 Confirm `frontend/static/js/payoff_theoretical.js` and `tests/unit/test_bs_pricing.py` do not yet exist (`ls frontend/static/js/payoff_theoretical.js tests/unit/test_bs_pricing.py` — should fail)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: TDD anchor and core math module — used by all three user stories (Today curve, price marker, and checkpoint switching all depend on it).

**⚠️ CRITICAL**: Constitution §IV requires tests written and confirmed failing before implementation.

- [X] T002 Write failing Python unit tests in `tests/unit/test_bs_pricing.py`, mirroring `test_payoff_math.py`'s structure. Port `bs_calculator.py::_bs_price` into a Python reference function and assert: (1) `bs_price(S=190, K=195, T=57/365, r=0.045, sigma=0.30, "put")` ≈ 10.9995; (2) `bs_price(S=288, K=280, T=57/365, r=0.045, sigma=0.48, "call")` ≈ 26.7313; (3) as `T → 0` (e.g. `T=0.5/365`), the put price approaches its intrinsic value (5.00 for the case above); (4) `available_checkpoints(days_to_expiry=30)` returns all 4 ids, `(10)` excludes `plus2wk`, `(5)` excludes both `plus1wk`/`plus2wk`, `(0)` returns only `expiration`; (5) `is_eligible_for_overlay` is `False` when any leg's `implied_volatility` is `None` or `<= 0`, or when `days_to_expiry <= 0`; (6) the "expiration" checkpoint's combined payoff at any price exactly equals `combined_payoff()` (from the existing `test_payoff_math.py` reference functions) for the same legs and price. Run `pytest tests/unit/test_bs_pricing.py` and confirm ALL tests fail (ImportError or AssertionError expected).
- [X] T003 Implement `frontend/static/js/payoff_theoretical.js` — pure ES module; imports `legPayoffPerShare`/`combinedPayoff` from `./payoff_math.js` (no other imports). Exports: `bsPrice(S, K, T, r, sigma, optionType)` (rational normal-CDF approximation, see contracts/payoff-theoretical-contract.md); `CHECKPOINTS` constant (`today`/`plus1wk`/`plus2wk`/`expiration` with `offsetDays` 0/7/14/null); `availableCheckpoints(daysToExpiry)` (filters to `offsetDays === null || offsetDays < daysToExpiry`); `isEligibleForOverlay(legs)` (false if any leg lacks `impliedVolatility > 0`, or `daysToExpiry <= 0`); `theoreticalPayoffPerShare(leg, price, daysToExpiry)` and `combinedTheoreticalPayoff(legs, price, daysToExpiry)` (parallel to the intrinsic-value formulas, substituting `bsPrice` for intrinsic — research.md D-006); `computeCheckpointCurve(legs, checkpoint, priceGrid)` (routes `offsetDays === null` through the existing `combinedPayoff`, everything else through `combinedTheoreticalPayoff` at `daysToExpiry = legs[0].daysToExpiry - checkpoint.offsetDays`). Verify Python tests now pass: `pytest tests/unit/test_bs_pricing.py -v`.

**Checkpoint**: `test_bs_pricing.py` all green. `payoff_math.js` untouched — no regression risk to specs/015.

---

## Phase 3: User Story 1 — Today Curve Alongside Expiration Curve (Priority: P1) 🎯 MVP

**Goal**: The payoff graph shows two curves — the existing expiration curve (unchanged) as a fixed reference, and a new "Today" curve computed via Black-Scholes from each leg's implied volatility and days-to-expiry. Positions with unusable IV data fall back to the existing single-curve behavior with no error.

**Independent Test**: Open demo mode (Options Spreads account), click the "AAPL · 2025-07-18" spread row — both curves appear and visibly diverge between the strikes. (Quickstart Scenario 1.)

- [X] T004 [US1] In `frontend/static/js/payoff_graph.js`, extend the leg-normalisation step (currently `_toLeg`) to also carry `impliedVolatility: pos.implied_volatility` and `daysToExpiry: pos.days_to_expiry` from each `PositionView`-shaped object, alongside the existing `strike`/`optionType`/`quantity`/`cost`.
- [X] T005 [US1] Add `buildOverlaySvg(legs, opts)` in `frontend/static/js/payoff_graph.js`, imported alongside the existing `buildPayoffSvg`. It calls `isEligibleForOverlay(legs)` from `payoff_theoretical.js`; if `false`, it returns `buildPayoffSvg(legs, opts)` unchanged (FR-008 fallback — zero behavior change from specs/015). If `true`, it computes `referenceCurve = analyzePayoff(legs).curve` (unchanged existing call) and `todayCurve = computeCheckpointCurve(legs, CHECKPOINTS[0], referenceCurve)`, then extends the existing SVG builder to draw `todayCurve` as a second polyline in a new color (`C.today = '#60a5fa'`, blue-400 — distinct from the existing gray reference curve, green/red gain-loss colors, and gray/dashed strike lines), with a small label pair identifying which line is "Today" and which is "Expiration".
- [X] T006 [US1] In `frontend/static/js/payoff_graph.js`'s `initPayoffGraphToggle`, change the SVG-precompute step (for both `groups` and `standalone` entries) to call `buildOverlaySvg` instead of `buildPayoffSvg` directly. `buildPayoffSvg` itself stays exactly as specs/015 left it — it is now only ever called internally by `buildOverlaySvg`'s ineligible-fallback branch.
- [X] T007 [US1] Run `pytest tests/ -q` (confirm zero regressions) and browser-test Quickstart Scenario 1 (Today/Expiration curves visible and diverge) and Scenario 8 (a leg with missing IV falls back to Expiration-only, no console error).

**Checkpoint**: Today curve renders alongside Expiration curve for eligible positions; ineligible positions are pixel-identical to specs/015's existing behavior.

---

## Phase 4: User Story 2 — Current-Price Marker With Dual Readout (Priority: P2)

**Goal**: A vertical marker at the position's current underlying price, labeled with both the Today curve's and the Expiration curve's P&L at that price. Requires threading `underlying_price` from Schwab through to the browser for the first time.

**Independent Test**: Open the same AAPL spread graph (now with `underlying_price` available) — a marker appears at ~$190 labeled with two distinct P&L values. (Quickstart Scenario 2.)

- [X] T008 [US2] Add `underlying_price: Decimal | None = None` to `PositionView` in `src/data/models.py`.
- [X] T009 [US2] In `src/services/schwab_client.py`'s `fetch_positions_and_greeks`, pass `underlying_price=Decimal(str(greeks_raw["underlying_price"])) if greeks_raw.get("underlying_price") else None` into the existing `PositionView(...)` constructor call. No new Schwab API call — `greeks_raw` already contains this value (research.md D-001).
- [X] T010 [P] [US2] Add a plausible `underlying_price` to every entry in `DEMO_POSITIONS_SPREADS` and `DEMO_POSITIONS_EQUITY` in `frontend/static/js/demo_data.js`: AAPL put spread ≈ 190, SPY put/call spread ≈ 535, TSLA call spread ≈ 288, SPY iron condor ≈ 555, AAPL covered call ≈ 215, NVDA covered call ≈ 130, VOO covered call ≈ 505 (and any remaining equity-account entries — pick a price consistent with that leg's delta sign and strike).
- [X] T011 [P] [US2] Mirror the same `underlying_price` values into `_DEMO_POSITIONS_SPREADS` and `_DEMO_POSITIONS_EQUITY` in `tests/contract/test_demo_mode_contract.py`, keeping the Python mirror in sync with the JS fixtures (same discipline as specs/015's T012).
- [X] T012 [US2] ~~Add `'underlying_price'` to `aggregateLegs()`'s `sharedOrNull(...)` list~~ — **corrected during implementation**: `aggregateLegs()`'s output is local to `renderSpreadRows()`'s table-display closure and never reaches `payoff_graph.js`; added the field there anyway as a harmless, potentially-useful-later addition (`positions_ui.js`), but the load-bearing fix is in `_toLeg()` in `payoff_graph.js`, which now reads `underlying_price` directly off each raw leg object — the same path already used for `implied_volatility`/`days_to_expiry` (T004). Every leg in a group shares one underlying (research.md D-004), so `legs[0].underlyingPrice` is the group's price.
- [X] T013 [US2] In `frontend/static/js/payoff_graph.js`, thread the group's (or standalone position's) `underlying_price` into `buildOverlaySvg`'s options. When non-null, render a vertical marker line at that price plus two text labels: the reference P&L (`combinedPayoff(legs, underlyingPrice)`) and the Today P&L (`combinedTheoreticalPayoff(legs, underlyingPrice, daysToExpiry)`), using the existing `_fmt`/`_esc` helpers already used for the max-gain/max-loss labels (Principle II — output sanitization applies to every rendered value, not just user-controlled strings). When `underlyingPrice` is null, render exactly as before with no marker and no error (FR-007).
- [X] T014 [US2] Run `pytest tests/ -q` and browser-test Quickstart Scenario 2 (marker with dual values) and Scenario 9 (marker absent, no error, when `underlying_price` is null).

**Checkpoint**: Price marker with dual readout works for both grouped and standalone positions; degrades gracefully when the price is unavailable.

---

## Phase 5: User Story 3 — Step Through Fixed Checkpoints (Priority: P3)

**Goal**: A checkpoint control (Today / +1 week / +2 weeks / Expiration) redraws the Today curve and the marker's checkpoint reading, without changing the Expiration reference curve. Unavailable checkpoints are disabled. Selection always resets to "Today" when a graph is (re)opened (FR-013).

**Independent Test**: Open a graph, step through each available checkpoint, confirm the curve moves toward the Expiration shape and collapses onto it exactly when "Expiration" is selected; close and reopen — checkpoint resets to "Today". (Quickstart Scenarios 3–7.)

- [X] T015 [US3] **Simplified during implementation**: rather than a separate precomputed `curvesByCheckpoint` Map, `svgCache` entries now hold `{ svg, legs, opts, anchorId }` — the normalised `legs`/`opts` needed to call `buildOverlaySvg` fresh on each checkpoint click. Benchmarked in Node: a full recompute (`analyzePayoff` + Black-Scholes curve) for the worst-case 4-leg iron condor averages **0.27ms**, far under any perceptible-delay threshold (FR-012) — a separate cache added complexity with no measurable benefit. The default "today" SVG is still precomputed at init time, preserving specs/015's zero-cost graph-open guarantee.
- [X] T016 [US3] In `buildOverlaySvg`, render a row of checkpoint buttons (one per `availableCheckpoints(daysToExpiry)` entry) inside the graph `<tr>`, styled to match the existing chevron-button aesthetic (small, monospace, muted-until-active). The graph row's `dataset.checkpoint` is set to `"today"` every time the row is created in `_showGraph` (FR-013) — never carried over from a previously opened graph's state.
- [X] T017 [US3] Wire a click handler on the checkpoint button row — **note**: delegated from the stable `graphRow`, not from `.payoff-checkpoint-row` directly, because that element's `outerHTML` is replaced on every switch (a listener bound directly to it would be lost after the first click). Verified via Playwright against the real running app: clicking Today → +2 weeks → Expiration → Today again all fired correctly. (in `initPayoffGraphToggle` or a small helper it calls): on click, look up the clicked checkpoint's curve from the cached `curvesByCheckpoint`, rebuild only the Today-curve polyline and the marker's checkpoint-P&L label within the existing SVG (leaving the reference curve, strike lines, and max-gain/max-loss annotations untouched), update `graphRow.dataset.checkpoint`, and update the buttons' active styling. Disabled checkpoints (per `availableCheckpoints`) are not clickable.
- [X] T018 [US3] Add an explicit assertion — covered by T002 case 6 (`test_expiration_checkpoint_matches_intrinsic_formula_exactly`), and additionally confirmed live: screenshot of the AAPL put spread with "Expiration" selected shows the blue checkpoint curve rendering exactly over the white reference curve, with identical labeled values ("Exp -3.10" / "Expiration -3.10"). (in `test_bs_pricing.py` if not already covered by T002's case 6, otherwise verify manually in-browser) that selecting "Expiration" produces a Today-curve that is point-for-point identical to the reference curve — confirms FR-005/research.md D-006 holds in the actual rendering path, not just in the underlying math.
- [X] T019 [US3] Run `pytest tests/ -q` and browser-test Quickstart Scenarios 3 (checkpoint redraw + collapse on Expiration), 4 (reset on reopen), 5 (availability near expiration), 6 (iron condor, four legs), and 7 (single-leg covered call). Done via Playwright against the actual running app (real Chrome): Scenarios 3, 4, 6, 7 confirmed live with zero console errors; Scenario 5 confirmed via the Python contract tests (T002) rather than hunting for a naturally short-DTE fixture.

**Checkpoint**: All three user stories independently functional. Checkpoint switching is instantaneous (lookup, not recompute).

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 Run the full Quickstart verification — done via Playwright against the real running app (demo mode, real Chrome). All 10 scenarios pass; see T007/T014/T019 notes for specifics. Zero console errors observed across every interaction.: step through all 10 scenarios in `specs/016-t0-payoff-overlay/quickstart.md` in demo mode. Document any failures.
- [X] T021 [P] Re-run all 10 scenarios in `specs/015-payoff-graphs/quickstart.md` — done via Playwright: graph open/close on second click, Escape-to-close, single-graph-at-a-time (switching from AAPL to the iron condor closes AAPL first), and chevron-vs-graph-click independence all confirmed unchanged against the live app. to confirm zero regression to the existing expiration-only behavior (explicit constraint from plan.md's Technical Context).
- [X] T022 [P] Run `pytest tests/ -q` — full suite must pass, including the new `test_bs_pricing.py` cases and the updated `test_demo_mode_contract.py` mirror. **210 passed** (up from 189 at the start of this feature: +19 `test_bs_pricing.py` cases, +2 new `test_schwab_client.py` cases added during implementation to cover the `underlying_price` wiring directly — see T008/T009 notes).
- [X] T023 [P] Visual polish pass — two real issues were caught by actually screenshotting the running app (not just Node-level string checks) and fixed: (1) the marker's two P&L labels were hardcoded near the chart top and collided with the legend/max-gain annotation whenever the current price sat near the top of the plotted range — now anchored to each dot's actual y-position with a minimum-gap separation; (2) the "Expiration" legend label (longer than "Today"/"+1 week"/"+2 weeks") was clipped at the right edge — legend text is now right-anchored instead of left-anchored from a fixed point. Re-verified via fresh screenshots after each fix; colors and contrast read clearly against the dark theme throughout.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1. BLOCKS all user stories. T003 depends on T002 (tests must fail first).
- **Phase 3 (US1)**: Depends on Phase 2 (`payoff_theoretical.js` must exist)
- **Phase 4 (US2)**: Depends on Phase 3 (extends `buildOverlaySvg` created in US1)
- **Phase 5 (US3)**: Depends on Phase 3 and Phase 4 (checkpoint switching updates both the curve `buildOverlaySvg` draws and the marker `US2` added)
- **Phase 6 (Polish)**: Depends on all three user stories being complete

### User Story Dependencies

- **US1**: Depends on Foundational (`payoff_theoretical.js`). No dependency on US2/US3.
- **US2**: Depends on US1 (extends `buildOverlaySvg`). Independently testable once T013 is done, even before US3 exists (marker always reflects the "Today" checkpoint by default).
- **US3**: Depends on US1 and US2 (the checkpoint control updates both the curve and the marker introduced by those stories).

### Within Each Story

- Tests (T002) MUST be written and CONFIRMED FAILING before T003 implementation
- `payoff_theoretical.js` (T003) must exist before any US1 task begins
- Backend field addition (T008, T009) must land before the frontend can read `underlying_price` (T012, T013)
- Demo data (T010) and its Python mirror (T011) can be done in parallel with the backend change, since they're independent files
- Precompute (T015) must exist before the click handler (T017) can look values up from it

### Parallel Opportunities

- T010 and T011 are marked [P] — different files, no shared dependency
- T021, T022, T023 can run in parallel in Phase 6

---

## Parallel Example: Phase 4

```
After Phase 3 completes:
  T008 → T009 (backend field, sequential — same PositionView/schwab_client.py change)
  T010 [P] and T011 [P] can run alongside T008/T009 (demo data, different files)
  T012 → T013 (frontend threading, depends on the field existing conceptually but not on T008/T009's runtime — can be written in parallel and verified together)
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1 (trivial)
2. Complete Phase 2 (TDD + `payoff_theoretical.js`)
3. Complete Phase 3 (US1: Today curve overlay)
4. **STOP and VALIDATE**: Browser-test Quickstart Scenarios 1 and 8
5. This alone delivers the feature's core value (per plan.md's Summary) even without the marker or checkpoint control

### Full Delivery

1. MVP (above) → US2 (price marker) → US3 (checkpoint control) → Polish

---

## Notes

- `payoff_math.js` is never modified by this feature — all new math lives in `payoff_theoretical.js`, which imports from it. This is deliberate (plan.md Complexity Tracking) to protect specs/015's existing, tested contract.
- The only backend changes are T008 and T009 — no new endpoint, no new route, no change to any existing response shape beyond one additional optional field.
- `RISK_FREE_RATE = 0.045` is a hardcoded constant inside `payoff_theoretical.js` (research.md D-003) — if `.env`'s `RISK_FREE_RATE` is ever changed, this constant must be updated to match by hand.
- Mixed-expiry (calendar/diagonal) positions need no special handling anywhere in this task list — `buildSpreadGroups()` already makes it structurally impossible for a group to contain mixed expiries (research.md D-004).
- **Follow-up (not in this task list)**: research.md D-004 deliberately omits an explicit "all legs share one expiry" guard inside `payoff_theoretical.js`, relying instead on `buildSpreadGroups()`'s grouping key. If that grouping logic is ever changed to span expiries, `isEligibleForOverlay`/`computeCheckpointCurve` would need an explicit same-expiry assertion added at that time — flagging here so the dependency is visible, not because it's actionable now.
