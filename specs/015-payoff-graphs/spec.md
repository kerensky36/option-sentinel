# Feature Specification: Option Position Payoff Graphs

**Feature Branch**: `015-payoff-graphs`
**Created**: 2026-05-23
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Click a Spread Position to See Its Payoff Graph (Priority: P1)

A trader reviewing their positions on the Red Pill (positions) page clicks on any multi-leg option position — such as a bull call spread or put spread — and immediately sees a payoff diagram overlaid or displayed inline. The graph shows the combined profit/loss curve across a range of underlying prices, with the max gain and max loss clearly annotated, and each leg's individual strike price marked on the x-axis.

**Why this priority**: This is the core value of the feature. Without it nothing else matters. Traders need to visually confirm their risk/reward profile at a glance without doing mental arithmetic.

**Independent Test**: Navigate to the positions page with at least one spread position loaded, click it, and verify the payoff graph appears with correct max gain, max loss, and leg strike annotations.

**Acceptance Scenarios**:

1. **Given** the user is on the positions page with a bull call spread loaded, **When** they click the spread row, **Then** a payoff graph appears showing the net P&L curve from well below the lower strike to well above the upper strike.
2. **Given** a payoff graph is displayed, **When** the user reads the graph, **Then** they can clearly see the annotated max gain value (at the upper strike), the annotated max loss value (below the lower strike), and vertical lines or markers at each leg's strike price.
3. **Given** a payoff graph is open, **When** the user clicks elsewhere or clicks the same row again, **Then** the graph closes/collapses cleanly.

---

### User Story 2 — Single-Leg Options Also Show a Payoff Graph (Priority: P2)

A trader with a single covered call or naked put position clicks on that row and sees a simplified payoff diagram showing the option's profit/loss profile — the breakeven point, the max gain (for sold options: the premium received), and unlimited or capped loss depending on option type.

**Why this priority**: Multi-leg spreads are the most pressing case, but the same graph logic naturally extends to single legs. Leaving single-leg positions without graphs after multi-leg support is built would feel incomplete and inconsistent.

**Independent Test**: Load a single covered call position, click its row, and verify the payoff graph shows the correct breakeven, premium gain cap, and loss profile.

**Acceptance Scenarios**:

1. **Given** a single short call position, **When** the user clicks it, **Then** the payoff graph shows a line that is flat at the premium received below the strike, then slopes down above the strike, with breakeven and strike annotated.
2. **Given** a single long put position, **When** the user clicks it, **Then** the payoff graph shows loss capped at the premium paid for prices above the strike, and gain that increases as price falls below the strike, with the max profit annotated.

---

### User Story 3 — Grouped Spread Positions Graph Together (Priority: P3)

When spread legs are displayed as a grouped unit (e.g. the AAPL bull call spread is collapsed into one row), clicking the group shows the combined payoff curve for all legs together. Individual leg strikes are all visible on the graph.

**Why this priority**: If the positions UI already groups multi-leg spreads into logical units, the graph must respect that grouping — otherwise the user sees a confusing partial picture.

**Independent Test**: Load a spread position that is rendered as a group, click the group row, and verify the payoff curve reflects the combined net P&L of all legs.

**Acceptance Scenarios**:

1. **Given** a grouped spread row (e.g. two legs shown as one unit), **When** the user clicks it, **Then** the combined payoff graph appears with all constituent strikes marked.
2. **Given** the combined graph is open, **When** the user inspects the max gain annotation, **Then** the value matches the theoretical max profit of the spread (width of strikes minus net premium paid, or net premium received).

---

### Edge Cases

- What happens when a position has no valid strike data (e.g. data not yet loaded)? Graph should not appear; row click behaviour is unchanged.
- What if a spread has more than two legs (e.g. iron condor with four legs)? All four strikes must be marked on the graph, and the combined P&L curve must be shown.
- What if the underlying price is missing? The graph renders the theoretical curve without a "current price" marker; no error is shown.
- What if two legs have the same strike? The graph must still render correctly without duplicate markers overlapping unreadably.
- Dismissing the graph via keyboard (Escape key) must work in addition to clicking.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The positions page MUST allow users to click any option position row (single-leg or multi-leg) to toggle a payoff graph for that position.
- **FR-002**: The payoff graph MUST display a profit/loss curve plotted against a range of underlying prices spanning from well below the lowest strike to well above the highest strike (at minimum ±30% of the mid-strike price).
- **FR-003**: The graph MUST annotate the maximum gain value and the maximum loss value directly on the chart so they are readable without hovering.
- **FR-004**: The graph MUST mark each leg's strike price on the x-axis with a vertical indicator and a label showing the strike value.
- **FR-005**: The graph MUST visually distinguish each leg of a multi-leg trade (e.g. different line styles or markers per leg) so the user can identify individual strikes.
- **FR-006**: The graph MUST display the combined net P&L curve (sum of all legs, accounting for quantity and long/short direction) as the primary line.
- **FR-007**: The graph MUST match the app's existing dark theme — dark background, muted grid lines, minimal chrome — consistent with the rest of the interface.
- **FR-008**: Clicking a row a second time (or pressing Escape) MUST dismiss the graph.
- **FR-009**: Only one graph MAY be open at a time; opening a graph for a new position MUST close any previously open graph.
- **FR-010**: The graph MUST be computed purely from data already present on the page (strike, expiry, quantity, option type, cost/premium) — no additional server calls are required.
- **FR-011**: The graph MUST render correctly for grouped spread rows (where multiple legs are represented by a single clickable row).
- **FR-012**: If a current underlying price is available for the position, MUST display a vertical "current price" marker on the graph.

### Key Entities

- **Position**: An option leg — has strike, expiry, option type (call/put), quantity (positive = long, negative = short), and cost basis (premium paid or received).
- **Payoff Curve**: The computed net P&L for a set of positions at a given underlying price at expiration.
- **Leg Marker**: A vertical annotation at a strike price identifying which leg it corresponds to.
- **Max Gain / Max Loss**: Theoretical maximum profit and maximum loss of the combined position, computed analytically from the legs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can open the payoff graph for any spread position in under one second of clicking the row.
- **SC-002**: The annotated max gain and max loss values on the graph are within rounding error (≤ $0.01 per share) of the analytically correct values for any spread tested.
- **SC-003**: All leg strike prices are visible and labelled on the x-axis without overlap for spreads of up to 4 legs.
- **SC-004**: The graph renders without any visible flash or layout shift when opened; it appears inline or as an overlay that does not disrupt the rest of the table.
- **SC-005**: The graph is visually indistinguishable in style from the rest of the app — a first-time visitor would not identify it as a third-party component.
- **SC-006**: 100% of position types present in the app (covered calls, put spreads, call spreads, iron condors) display a correct payoff graph.

## Assumptions

- The "Red Pill page" refers to the Positions / Thesis Monitor dashboard (the primary positions view).
- Position data (strike, option type, quantity, premium) is already loaded in the page at the time of click — no lazy-fetch is needed.
- The payoff diagram represents the position at expiration (not an intermediate time value); intra-expiry theta/IV curves are out of scope for this feature.
- The existing positions UI already groups spread legs into logical units for display; the graph respects and operates on that grouping.
- The app uses a dark colour palette; the graph must use the same palette rather than a default light theme.
- Demo mode positions must also display payoff graphs using the same computed logic as real positions.
- Mobile/touch support is a nice-to-have but not a hard requirement for this feature — the primary use case is desktop.
