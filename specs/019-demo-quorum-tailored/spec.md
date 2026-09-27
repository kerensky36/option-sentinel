# Feature Specification: Tailored Demo Quorum

**Feature Branch**: `claude/quorum-members-option-greeks-hqkzrd` (spec directory `019-demo-quorum-tailored`)

**Created**: 2026-09-27

**Status**: Draft

**Amends**: `specs/017-macro-quorum-agents/spec.md` FR-018 (demo mode quorum). Builds on spec 018 (fundamentals-first seats).

**Input**: User description: "In demo mode, make the canned quorum result tailored to the clicked position — rationales quote its actual delta, IV/RV and days to expiry, and the verdict varies by position. Still no model call."

## Clarifications

### Session 2026-09-27

- Q: Should demo mode call the real quorum? → A: No. It stays entirely in the browser: no server request, no model call, no news fetch (017 FR-018 unchanged in that respect).
- Q: How realistic should the demo votes be? → A: Deterministic rules over the position's own numbers, one rule per lens, so different positions get different votes and every rationale quotes real figures from that position. The rules are illustrative, not a model.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Demo quorum reflects the clicked position (Priority: P1) 🎯 MVP

A visitor in demo mode clicks Quorum on different demo positions. Each result quotes that position's own figures (net delta, IV relative to realised volatility, days to expiry, strike distance, share of maximum profit captured), and the verdict differs between positions whose numbers differ.

**Why this priority**: The current canned result is identical for every position and quotes figures that don't match it, which undermines the demo.

**Independent Test**: In demo mode, click Quorum on the AAPL put spread and on the SPY iron condor; verify each card quotes that position's numbers and the two verdicts or tallies differ.

**Acceptance Scenarios**:

1. **Given** demo mode, **When** the visitor clicks Quorum on any demo position, **Then** no request leaves the browser and a complete result renders (verdict, tally, five cards with the spec 018 lenses, research brief, headlines, "Data as of").
2. **Given** a demo position, **When** the result renders, **Then** each of the four fundamentals cards quotes at least one figure computed from that position, and the figure matches the position's data.
3. **Given** two demo positions with materially different numbers, **When** the visitor runs the quorum on each, **Then** the tallies differ.
4. **Given** the five demo votes, **When** the verdict is shown, **Then** it follows the same 3-of-5 rule as the live quorum (017 FR-007).
5. **Given** a figure that is unavailable for the position (e.g. no realised volatility), **When** the relevant card renders, **Then** it says the figure is unavailable and votes HOLD with low confidence rather than inventing a number.

### Edge Cases

- Debit positions (net premium paid): "share of maximum profit captured" is not applicable; the time-decay card reasons from days to expiry instead.
- Positions without a short leg: the strike card reasons from the nearest leg.
- Missing underlying price: moneyness is unavailable; the strike card holds with low confidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-201** *(amends 017 FR-018)*: In demo mode, the Quorum button MUST return a result computed in the browser from the clicked position's own legs, without contacting the server.
- **FR-202**: The result MUST use the spec 018 lenses and seat ids in order, and each of the four fundamentals seats MUST vote by a fixed, deterministic rule over the position's figures (defined in plan.md) and quote the figure(s) it used, formatted from the same values.
- **FR-203**: The Macro & News Overlay seat MUST vote with the most common fundamentals vote (HOLD on a tie) and say that the demo news does not override the numbers; demo headlines remain clearly labelled as demo.
- **FR-204**: The verdict and tally MUST follow the 017 FR-007 rule (≥ 3 of 5 wins; otherwise NO_CONSENSUS).
- **FR-205**: A figure that cannot be computed MUST be stated as unavailable, and the seat that needs it votes HOLD with confidence ≤ 0.3.
- **FR-206**: The result MUST echo the request's "as of" time and underlying and label the model as "demo (no model call)".

### Key Entities

- **Demo Quorum Result**: Same shape as the live QuorumResult (spec 018 data-model), produced client-side.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-201**: Across the demo positions, at least two distinct tallies are produced (verified by automated test).
- **SC-202**: 100% of fundamentals-card rationales in demo mode contain a figure that matches the clicked position (verified by automated test).
- **SC-203**: No network request is made when clicking Quorum in demo mode (017 SC unchanged; verified by browser check).

## Assumptions

- Demo data uses its own conventions (signed cost, per-contract quantities of ±1 or ±2); the rules only need to be internally consistent with that data.
- Probability of finishing in the money is approximated by |delta| in demo mode and labelled "≈".
- No server, data-use, or privacy change: demo mode sends nothing anywhere.
