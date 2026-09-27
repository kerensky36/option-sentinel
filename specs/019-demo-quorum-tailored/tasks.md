# Tasks: Tailored Demo Quorum

**Input**: `specs/019-demo-quorum-tailored/` (spec.md, plan.md)
**Tests**: Required (Constitution IV); run and see them fail before implementing.

## Phase 1: User Story 1 — Demo quorum reflects the clicked position (P1) 🎯 MVP

### Tests (write first, confirm failing)

- [X] T001 [US1] Create `tests/unit/demo_quorum_harness.mjs`. It imports `buildDemoQuorum` from `frontend/static/js/demo_quorum.js` and a JSON case file path from argv, and prints `JSON.stringify(buildDemoQuorum(request))` for each case.
- [X] T002 [US1] Create `tests/unit/test_demo_quorum.py`. It runs the harness with `node` and skips with the reason "node not installed" if `shutil.which("node")` is None. Cases:
  - result shape: five spec 018 seat ids and lenses in order; tally has CLOSE/HOLD/ROLL; `as_of` and `underlying_symbol` echoed; model is "demo (no model call)" (FR-202, FR-206)
  - verdict matches the 3-of-5 rule for the produced votes (FR-204)
  - each rule branch in plan.md with hand-built requests:
    - short put with dte 5 → Greeks ROLL
    - credit 60% captured → Time Decay CLOSE
    - short call ITM → Strike ROLL up_and_out
    - IV/RV missing → Volatility HOLD with confidence ≤ 0.3 and "unavailable" in the rationale (FR-205)
    - debit position → no "% of max profit" figure
  - rationales quote the position's figures:
    - net delta text equals the formatted `Σ delta×q×100`
    - the dte number appears
    - the IV/RV ratio text appears (SC-202)
  - the overlay seat takes the most common fundamentals vote, HOLD on a tie (FR-203)
  - across `DEMO_POSITIONS_SPREADS` grouped by underlying, at least two distinct tallies (SC-201)

### Implementation

- [X] T003 [US1] Create `frontend/static/js/demo_quorum.js` per plan.md figures and seat rules. Import `analyzePayoff` from `./payoff_math.js`. Pure; no DOM, no network. Makes T002 pass.
- [X] T004 [US1] In `frontend/static/js/demo_data.js`, route `/api/quorum/vote` to `buildDemoQuorum(JSON.parse(options.body))` and remove `_demoQuorum`.

## Phase 2: Polish

- [X] T005 Run the full `pytest -q` and `node --check` on changed JS. In headless Chromium in demo mode, open Quorum on two positions and confirm the results differ, quote their own figures, and make no request to `/api/quorum/vote` (SC-203).
