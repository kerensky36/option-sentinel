# Implementation Plan: T+0 Payoff Overlay

**Branch**: `016-t0-payoff-overlay` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

## Summary

Add a second curve to the existing payoff graph (specs/015): the position's theoretical value today (or at a selectable near-term checkpoint), computed via Black-Scholes from each leg's already-known implied volatility and days-to-expiry, drawn alongside the existing expiration curve as a fixed reference. A small checkpoint control (Today / +1 week / +2 weeks / Expiration) redraws the second curve; a vertical marker at the current underlying price labels both curves. Requires one small backend addition — `underlying_price`, already fetched per-symbol for Greeks but never returned to the browser — and one new client-side pure-math module mirroring the project's existing `payoff_math.js`/`test_payoff_math.py` pattern rather than a server endpoint.

## Technical Context

**Language/Version**: JavaScript ES Modules (browser-native); Python 3.11 for tests and the two backend field additions
**Primary Dependencies**: None new — reuses `payoff_math.js`'s existing exports; existing Tailwind CSS
**Storage**: None new — `underlying_price` rides inside the position payload already cached in sessionStorage; no new keys, no new persistence
**Testing**: pytest (Python reference tests for the new JS math, mirroring `test_payoff_math.py`); browser manual verification via quickstart.md
**Target Platform**: Chrome/Firefox/Safari — same as the rest of the app
**Project Type**: Frontend feature, plus a 2-file / ~6-line backend field addition (no new endpoint)
**Performance Goals**: Checkpoint switch has no perceptible delay (SC-002) — all four checkpoints' numeric curves are precomputed once when a graph's data is prepared, matching the existing precompute-at-init discipline from specs/015 (commit `4ceb595`)
**Constraints**: No external chart or math libraries; no new server endpoint; CSP-safe (no new script injection surface); must not change any existing specs/015 behavior when "Expiration" is selected
**Scale/Scope**: Client-side computation only, operating on data already in memory; one new backend field

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Privacy-First | ✅ PASS | `underlying_price` is public market data, not account-identifying. It flows through the same per-request stateless pipeline as every other position field, into the same sessionStorage-cached payload — no new storage layer, no new persistence. |
| II — Security-First | ✅ PASS | No new endpoint, no new user-controlled input. `underlying_price` is a plain float already fetched from Schwab's own option-chain response; it is rendered through the same escaped/numeric-formatting SVG path already used for every other value on the graph. |
| III — Spec-Before-Code | ✅ PASS | spec.md and this plan are committed before any `src/`, `frontend/`, or `tests/` change. |
| IV — Test-First | ✅ PASS | `tests/unit/test_bs_pricing.py` will be written and confirmed failing before `payoff_theoretical.js` is implemented, mirroring the existing `test_payoff_math.py` pattern (specs/015, D-007). |
| V — Simplicity | ✅ PASS | One new small pure module; no new abstractions beyond a fixed 4-entry checkpoint array. Mixed-expiry exclusion (FR-011) requires zero guard code — see Research D-004. No server endpoint added, despite that being the more conventional web-app shape, because it isn't needed here. |
| VI — Visual | ✅ PASS | Same dark palette, monospace font, and SVG-in-`<tr>` mechanism as specs/015. Checkpoint control reuses the existing button styling already established for the leg-expand chevron. |

## Project Structure

### Documentation (this feature)

```text
specs/016-t0-payoff-overlay/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── contracts/
│   └── payoff-theoretical-contract.md  # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not created by this command)
```

### Source Code Changes

```text
src/data/models.py                 MODIFY — add `underlying_price: Decimal | None = None` to PositionView
src/services/schwab_client.py      MODIFY — populate underlying_price from the value _fetch_greeks
                                             already retrieves per symbol (no new Schwab API call)

frontend/static/js/
├── payoff_math.js                 UNCHANGED — existing expiration-only module and its contract
│                                             stay exactly as specs/015 left them
├── payoff_theoretical.js          NEW — Black-Scholes pricing mirror of bs_calculator.py::_bs_price,
│                                        plus checkpoint-curve computation; imports from payoff_math.js
├── payoff_graph.js                MODIFY — render the checkpoint-controlled second curve, the
│                                            checkpoint control, and the dual-readout price marker
├── positions_ui.js                MODIFY — thread underlying_price through the existing
│                                            group/standalone data already passed to
│                                            initPayoffGraphToggle (sharedOrNull pattern)
└── demo_data.js                   MODIFY — add a plausible underlying_price to each demo position

tests/unit/
└── test_bs_pricing.py             NEW — Python reference tests for payoff_theoretical.js,
                                          using bs_calculator.py's existing pricing formula as the oracle
```

No changes to: `screener_ui.js`, `auth.js`, `thesis`-related files (already removed), any backend route signature, any existing sessionStorage key name.

**Structure Decision**: Extends the existing frontend-feature structure from specs/015 unchanged; adds one new pure JS module rather than modifying the tested `payoff_math.js` contract, and one small backend field addition rather than a new endpoint (see Research D-001).

## Complexity Tracking

No constitution violations. No abstractions beyond what the spec requires.

| Item | Decision |
|------|----------|
| New JS module instead of extending payoff_math.js | Keeps specs/015's existing, already-tested contract (`legPayoffPerShare`, `combinedPayoff`, `analyzePayoff`) untouched — new math imports from it rather than growing it |
| No server endpoint for theoretical pricing | Matches the project's established pattern (specs/015, D-007): pure client-side math validated by a Python reference test, not a round trip |
| Backend field addition instead of a fuller "quote service" | The value already exists in the per-symbol Greeks response; adding a field is smaller and lower-risk than introducing a new data-fetch path |
