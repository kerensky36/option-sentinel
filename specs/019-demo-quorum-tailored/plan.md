# Implementation Plan: Tailored Demo Quorum

**Branch**: `claude/quorum-members-option-greeks-hqkzrd` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

## Summary

Move the demo quorum into a new pure ES module, `frontend/static/js/demo_quorum.js`. It exports `buildDemoQuorum(request)`, which takes the same v2 request body the live quorum gets (`{as_of, legs[]}`, built by `quorum_ui.buildQuorumRequest`). It computes the position's figures, applies one rule per lens, tallies with the 3-of-5 rule, and returns a QuorumResult-shaped object. `demo_data.js` calls it for `/api/quorum/vote`. Breakevens reuse `payoff_math.analyzePayoff`.

## Technical Context

**Language**: JavaScript ES modules (browser), no dependencies.
**Testing**: pytest runs a small Node harness (`node` subprocess) that imports `demo_quorum.js` and prints JSON; assertions live in `tests/unit/test_demo_quorum.py`. The test is skipped with a clear reason when `node` is not installed.
**Constraints**: No network; pure functions; deterministic output apart from timestamps.

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I — Privacy | ✅ | Demo only; nothing leaves the browser; no data-use change. |
| II — Security | ✅ | No new endpoint or data flow. All rendered text still goes through `quorum_ui.esc`. |
| III — Spec-before-code | ✅ | This spec, plan and tasks are committed before code. |
| IV — Test-first | ✅ | Harness tests written and seen failing first. |
| V — Simplicity | ✅ | One small pure module; reuses `payoff_math.js`. |
| VI — Visual | ✅ | No layout change. |

## Figures (per request; demo data conventions)

| Figure | Computation |
|---|---|
| `netDelta` | Σ delta × quantity × 100 (share-equivalent) |
| `ivRv` | first leg with both IV and realised vol: IV ÷ RV |
| `dte` | min days_to_expiry |
| `credit` | −Σ cost × \|quantity\| (per share; > 0 means net credit) |
| `pnl` | Σ unrealised_pnl |
| `pctCaptured` | credit > 0: pnl ÷ (credit × 100) × 100; else unavailable |
| `thetaDay` | Σ theta × quantity × 100 |
| `keyLeg` | short leg closest to the money (else leg closest to the money) |
| `moneyness` | keyLeg: call (S−K)/S×100, put (K−S)/S×100 (positive = in the money) |
| `probItm` | Black-Scholes N(d2) (call) / N(−d2) (put) with the leg's IV, T = max(dte, 1)/365, r = 0.045 |
| `breakevens` | `analyzePayoff` from `payoff_math.js` |

## Seat rules (first match wins)

- **Greeks & Exposure**: has a short leg and dte ≤ 7 → ROLL out (0.7); \|netDelta\| ≥ 40 → CLOSE (0.6); else HOLD (0.55).
- **Volatility & Pricing**: ivRv unavailable → HOLD (0.3). Credit: ivRv ≥ 1.2 → HOLD (0.6); ivRv ≤ 0.9 → CLOSE (0.55); else HOLD (0.5). Debit: ivRv ≥ 1.2 → CLOSE (0.55); else HOLD (0.5).
- **Time Decay & P&L**: credit: pctCaptured ≥ 50 → CLOSE (0.7); pctCaptured ≥ 25 and dte ≤ 21 → ROLL out (0.6); else HOLD (0.55). Debit: dte ≤ 14 → CLOSE (0.6); else HOLD (0.5).
- **Strike & Assignment**: moneyness unavailable → HOLD (0.3); key leg is short and moneyness ≥ 0 → ROLL down_and_out (put) / up_and_out (call) (0.7); short and moneyness > −3 and dte ≤ 21 → ROLL out (0.6); else HOLD (0.55).
- **Macro & News Overlay**: most common of the four votes (HOLD on a tie), confidence 0.5, with the rationale "demo news does not override the numbers".

## Source changes

```text
frontend/static/js/demo_quorum.js   NEW  buildDemoQuorum(request) — pure
frontend/static/js/demo_data.js     MODIFY  /api/quorum/vote → buildDemoQuorum(JSON body); drop _demoQuorum
tests/unit/test_demo_quorum.py      NEW  node-harness tests
tests/unit/demo_quorum_harness.mjs  NEW  imports demo_quorum.js + demo positions, prints JSON
```
