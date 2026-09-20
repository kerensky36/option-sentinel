# Feature Specification: T+0 Payoff Overlay

**Feature Branch**: `016-t0-payoff-overlay`
**Created**: 2026-09-19
**Status**: Draft
**Input**: User description: "Extend the existing payoff graph (specs/015) to overlay the position's current value against its expiration value. Add a \"view as of\" control with a few fixed points — Today, +1 week, +2 weeks, Expiration — that recompute the same curve at each date using Black-Scholes pricing from each leg's implied volatility, falling back to the existing intrinsic-only math at the expiration point. Add a current-underlying-price vertical marker showing P&L at that price for whichever date is selected — this requires adding underlying_price to the position data sent to the browser (computed server-side for Greeks today but never exposed to the frontend; spec 015 required this marker under FR-012 but it was never implemented for exactly this reason). Compute the Black-Scholes pricing in a new pure JS module mirrored by a Python test file, following the same pattern payoff_math.js/test_payoff_math.py already established, rather than adding a server endpoint. Legs must share a common expiration date for v1 — mixed-expiry structures are out of scope but the \"view as of\" date should not be architecturally tied to any single leg's expiry, since that's what would let calendars/diagonals work later without a redesign."

## Clarifications

### Session 2026-09-19

- Q: Does the Expiration curve stay on screen as a fixed reference while stepping through checkpoints, or does each checkpoint fully replace the displayed curve? → A: The Expiration curve is always drawn as a fixed reference; the second curve changes shape per checkpoint (Today/+1wk/+2wk) and collapses onto the reference line when "Expiration" itself is selected. The price marker always labels both curves.
- Q: Does the checkpoint selection persist across positions, or reset per position? → A: Checkpoint always resets to "Today" whenever a graph is opened, regardless of what was last selected on a previously opened position's graph.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Today's Value Alongside the Expiration Outcome (Priority: P1)

A trader opens the payoff graph for a spread position (as already supported by specs/015) and sees two curves instead of one: the existing expiration-only curve, and a new curve showing what the position is worth today, given the time remaining and each leg's current implied volatility. This turns unspent time value — which today is invisible outside a Greeks table — into something visible directly on the graph.

**Why this priority**: This is the entire point of the feature. Without it, the graph still only answers "what happens if I hold to the literal last second," which is rarely the question being asked when checking a live position.

**Independent Test**: Open the payoff graph for a spread with more than zero days to expiry and a valid implied volatility on every leg; verify two distinct, labeled curves appear and that they diverge away from the max-gain/max-loss plateaus.

**Acceptance Scenarios**:

1. **Given** a spread position with more than zero days to expiry and a valid implied volatility on every leg, **When** the user opens the payoff graph, **Then** both a "Today" curve and the existing "Expiration" curve are visible and visually distinguished from one another.
2. **Given** the same position, **When** the user reads both curves at an underlying price between the strikes, **Then** the Today curve's value differs from the Expiration curve's value there (reflecting remaining time value).
3. **Given** a position where at least one leg has no usable implied volatility, **When** the graph renders, **Then** only the existing Expiration curve is shown, with no error and no broken Today curve.

---

### User Story 2 - Read Today's P&L at the Current Price (Priority: P2)

A trader wants a single glance to answer "what would I lock in if I closed this right now, versus what I get if I hold to expiration." A vertical marker at the current underlying price, labeled with both curves' values at that price, answers this without any mental math.

**Why this priority**: This is the actual decision-support moment traders return to a position for. It depends on User Story 1 existing but is the piece that makes the overlay actionable rather than just informative.

**Independent Test**: Open the graph for a position where the current underlying price is available; verify a vertical marker appears at that price with both curves' P&L values labeled.

**Acceptance Scenarios**:

1. **Given** the current underlying price is available for a position, **When** the graph opens, **Then** a vertical marker appears at that price, labeled with the Today curve's P&L and the Expiration curve's P&L at that price.
2. **Given** the current underlying price is not available (e.g., not yet loaded), **When** the graph opens, **Then** no marker is shown and no error occurs — curves still render normally.

---

### User Story 3 - Step Through a Few Fixed Points in Time (Priority: P3)

A trader actively managing a position (deciding whether to roll, close early, or hold) wants to see the curve at a couple of points between today and expiration, not just the two endpoints. A small, fixed set of checkpoints — Today, +1 week, +2 weeks, Expiration — lets them see the position's shape "unroll" toward its final payoff without needing a continuous slider.

**Why this priority**: Valuable for active management, but the feature already delivers its core value via Stories 1 and 2 without it. This is the refinement that makes the overlay useful for a decision made days from now, not just right now.

**Independent Test**: Open a graph, select each available checkpoint in turn, and verify the curve redraws to a shape consistent with the elapsed time at each one.

**Acceptance Scenarios**:

1. **Given** a position with more than 14 days to expiry, **When** the user selects the "+1 week" or "+2 weeks" checkpoint, **Then** the curve redraws using the time-decayed value at that checkpoint, and its shape falls between the Today curve and the Expiration curve.
2. **Given** a position with fewer days to expiry than a checkpoint represents (e.g., 5 days to expiry and "+2 weeks" selected), **When** the user views the checkpoint control, **Then** that checkpoint is unavailable rather than producing a nonsensical result.
3. **Given** the user selects the "Expiration" checkpoint, **When** the curve renders, **Then** it is identical to the existing expiration-only curve from specs/015, including all existing max-gain/max-loss/strike annotations.

---

### Edge Cases

- A position whose legs do not share a single common expiration date (e.g., a calendar or diagonal spread): the "view as of"/Today overlay does not apply; the existing expiration-only graph behavior from specs/015 is preserved unchanged for these positions.
- A leg with a missing or zero implied volatility: the Today/checkpoint curves are not shown for that position; the existing Expiration curve still renders (see User Story 1, Scenario 3).
- Zero days to expiry (today is expiration day): the overlay is ineligible, exactly like the missing-implied-volatility case (FR-001, FR-008) — only the Expiration curve renders, with no Today curve and no checkpoint control.
- Current underlying price unavailable: curves render without the price marker; no error (see User Story 2, Scenario 2) — matches the graceful-degradation behavior already established in specs/015.
- A checkpoint that lands on or after the position's own expiration date is unavailable rather than selectable (see User Story 3, Scenario 2).
- Dismissing the graph (click again or Escape) behaves exactly as specs/015 already defines, regardless of which checkpoint was selected.
- Opening a different position's graph while one is already open (which closes the first, per specs/015) always opens the new graph on the "Today" checkpoint, never carrying over the previous graph's checkpoint selection.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The payoff graph MUST render a second P&L curve representing the position's computed value today, alongside the existing expiration curve, whenever every leg has a valid implied volatility and more than zero days to expiry.
- **FR-002**: For eligible positions (FR-001), the graph MUST always display the Expiration curve as a fixed reference line, alongside a second curve reflecting whichever "view as of" checkpoint is currently selected; the two MUST be visually distinguishable (e.g. distinct color or line style) with a label identifying which is which.
- **FR-003**: The graph MUST provide a control for selecting one of a fixed set of "view as of" checkpoints — Today, +1 week, +2 weeks, Expiration — and MUST redraw the checkpoint-controlled curve for whichever checkpoint is selected, while the Expiration reference curve remains unchanged.
- **FR-004**: A checkpoint MUST be unavailable for selection if it falls on or after the position's expiration date.
- **FR-005**: When the "Expiration" checkpoint is selected, the checkpoint-controlled curve MUST coincide exactly with the Expiration reference curve, preserving its existing max-gain/max-loss and strike annotations from specs/015.
- **FR-006**: The graph MUST display a vertical marker at the position's current underlying price, when available, labeled with the P&L of both the Expiration reference curve and the checkpoint-controlled curve at that price.
- **FR-007**: If the current underlying price is unavailable for a position, the graph MUST render without the marker and without error.
- **FR-008**: If any leg in a position lacks a usable implied volatility, the graph MUST fall back to showing only the Expiration curve, without error.
- **FR-009**: The feature MUST apply uniformly to both single-leg and multi-leg (grouped) positions, consistent with how the existing expiration graph is already scoped.
- **FR-010**: All curves and checkpoint switches MUST be computed from data already available on the page — no additional network request is triggered when a user changes the selected checkpoint.
- **FR-011**: The Today/checkpoint overlay MUST only apply to positions where all legs share a single common expiration date; positions with mixed expiries continue to show only the existing expiration-only graph.
- **FR-012**: Switching between checkpoints MUST feel instantaneous, with no visible loading state, consistent with the existing graph's near-instant open behavior.
- **FR-013**: The selected checkpoint MUST reset to "Today" whenever a payoff graph is opened, regardless of what checkpoint was last selected on a previously opened position's graph.

### Key Entities

- **Position Leg** *(existing, extended)*: An option leg already carries strike, expiry, type, quantity, and cost; this feature additionally relies on its already-computed implied volatility and days-to-expiry.
- **Underlying Price**: The current price of the position's underlying instrument. Not previously available to the graph; required both for the current-price marker and, indirectly, for computing today's value.
- **View-As-Of Checkpoint**: One of a fixed set of points in time (Today / +1 week / +2 weeks / Expiration) at which the payoff curve is evaluated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader can see both today's value and the expiration value for any eligible position within the same single click already used to open the graph today — no additional navigation or page is required.
- **SC-002**: Switching between "view as of" checkpoints updates the visible curve with no perceptible delay.
- **SC-003**: For any eligible spread tested, the Today curve's value at the current underlying price is within $0.01 per share of the value an independent Black-Scholes calculation produces for the same inputs.
- **SC-004**: Every eligible position type (single leg, and multi-leg groups sharing one expiration date) displays a working Today/checkpoint overlay; ineligible cases (mixed expiries, missing volatility, missing price) degrade to existing behavior without errors.
- **SC-005**: A trader can state "what I'd lock in right now" and "what I get if I hold" for any eligible position by reading the graph alone, without consulting any other part of the page.

## Assumptions

- The "current underlying price" is the same live price already fetched and used elsewhere in the app for the position's Greeks (as of the last refresh) — not a continuously streaming quote.
- Time-value pricing uses the same fixed risk-free rate already configured for the app's existing Black-Scholes fallback; no new user-facing configuration is introduced.
- "View as of" checkpoints are calendar-day offsets (7 and 14 days) from today, not trading-day offsets.
- Demo-mode positions carry the same underlying-price data as real positions, so the feature behaves identically in demo mode, consistent with how specs/015 already treats demo mode.
- Mixed-expiry (calendar/diagonal) structures are explicitly out of scope for this feature, but the "view as of" checkpoint is intentionally kept independent of any single leg's own expiration date, so this exclusion can be lifted later without redesigning the checkpoint mechanism.
- This feature builds on and does not modify the existing expiration-only behavior defined in specs/015 except where explicitly stated (e.g., adding underlying price to the data already sent to the browser).
