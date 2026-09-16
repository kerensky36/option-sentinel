# Feature Specification: Auto-Group Spreads by Underlying

**Feature Branch**: `011-spread-group-underlying`
**Created**: 2026-05-16
**Status**: Draft
**Input**: User description: "Group all option spreads by underlying and ask me if there other spread dimensions to group by. This should be done regardless of whether they are part of a thesis or not"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Positions auto-grouped by underlying without thesis setup (Priority: P1)

A trader opens the positions dashboard and sees their QQQ credit spread (two legs) automatically collapsed into a single "QQQ" summary row — without having assigned the legs to any thesis group. The table is clean and scannable from day one, requiring zero manual configuration.

**Why this priority**: This is the entire value of the feature. The previous grouping only worked if the trader had already set up thesis groups, which is an extra step most users skip. Auto-grouping by underlying removes that friction entirely.

**Independent Test**: Load the positions table with two or more option positions sharing the same underlying symbol and no thesis group assignments. Confirm they appear as a single collapsed summary row labelled with the underlying symbol.

**Acceptance Scenarios**:

1. **Given** two or more open option positions share the same underlying symbol, **When** the positions table renders, **Then** those positions appear as a single collapsed summary row regardless of thesis group assignment.
2. **Given** a collapsed underlying group row is visible, **When** the trader clicks the ▶ chevron, **Then** the individual leg rows appear and the chevron rotates to ▼.
3. **Given** an expanded group, **When** the trader clicks the ▼ chevron, **Then** the leg rows collapse and the chevron returns to ▶.
4. **Given** a position exists on an underlying with no other positions on that same underlying, **When** the positions table renders, **Then** that position renders as a regular individual row (single-leg underlyings are not grouped).
5. **Given** positions are refreshed or the account is switched, **When** the table re-renders, **Then** all groups reset to collapsed.

---

### User Story 2 — Aggregated metrics on the group summary row (Priority: P1)

When a group is collapsed, the trader sees meaningful aggregated values for the whole underlying position — P&L, Delta, Gamma, Theta, and Vega summed across all legs — so they can assess net exposure at a glance.

**Why this priority**: Equally critical as grouping itself. A summary row with blank metrics forces the trader to expand every group, defeating the purpose.

**Independent Test**: Collapse a group with two or more legs. Verify P&L, Delta, Gamma, Theta, and Vega each show the summed value. Verify Mark, Qty, Type, Strike, and IV show "—".

**Acceptance Scenarios**:

1. **Given** a collapsed group summary row, **When** the trader reads the P&L column, **Then** it shows the sum of all leg P&L values with correct sign and colour.
2. **Given** a collapsed group summary row, **When** the trader reads Delta, Gamma, Theta, and Vega, **Then** each shows the arithmetic sum across all legs.
3. **Given** a collapsed group summary row, **When** the trader reads Mark, Qty, Type, Strike, and IV, **Then** each shows "—".
4. **Given** a collapsed group summary row, **When** the trader reads the Underlying column, **Then** it shows the underlying symbol (always shared within a group by definition).
5. **Given** a collapsed group summary row, **When** the trader reads Expiry and DTE, **Then** each shows the shared value if all legs have the same expiry, otherwise "—".

---

### User Story 3 — Positions sub-grouped by underlying + expiry (Priority: P2)

A trader holding a QQQ Jun spread and a separate QQQ Jul spread sees two collapsed rows — "QQQ · 2026-06-20" and "QQQ · 2026-07-18" — rather than one mixed "QQQ" row. This keeps calendar spreads and unrelated same-underlying positions cleanly separated.

**Why this priority**: Without expiry sub-grouping, a trader running a Jun and a Jul spread on the same underlying would see their legs mixed into one row, making net Greeks misleading and individual spread assessment impossible.

**Independent Test**: Load positions with two QQQ options sharing one expiry and two QQQ options sharing a different expiry. Confirm two separate collapsed rows appear, each labelled with the underlying and its expiry date.

**Acceptance Scenarios**:

1. **Given** four positions — two QQQ Jun legs and two QQQ Jul legs — **When** the table renders, **Then** two separate collapsed summary rows appear: one for QQQ Jun, one for QQQ Jul.
2. **Given** a group summary row, **When** the trader reads the label, **Then** it shows the underlying symbol and the shared expiry date.
3. **Given** positions on the same underlying AND the same expiry (2+ legs), **When** the table renders, **Then** they form a single collapsed group.
4. **Given** a single position on QQQ Jun with no other QQQ Jun positions, **When** the table renders, **Then** that position renders as a regular individual row (not grouped).

---

### Edge Cases

- **Single position on an underlying**: Renders as a regular individual row with no grouping or collapse toggle.
- **All legs null for a Greek**: The summary row shows "—" for that Greek instead of 0.
- **Mixed BS-sourced Greeks**: If any leg contributing to a summed Greek was estimated via Black-Scholes, the BS badge appears on that Greek's sum.
- **Positions previously assigned to a thesis group**: Thesis assignment has no effect on grouping — underlying-based grouping takes precedence.
- **Group with one remaining leg** (other legs closed): The sole remaining leg renders as a regular individual row.
- **Refresh while group is expanded**: All groups reset to collapsed on every re-render.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The positions table MUST automatically group all open positions sharing the same underlying symbol into a single collapsible summary row, with no thesis group assignment required.
- **FR-002**: A group MUST only form when two or more positions share the same underlying symbol. A single position on an underlying MUST render as a regular individual row.
- **FR-003**: Group summary rows MUST be collapsed by default on every render (initial load, refresh, account switch).
- **FR-004**: Each group summary row MUST display the underlying symbol and expiry date as its label (e.g., "QQQ · 2026-06-20") and show aggregated metrics: P&L (sum), Delta (sum), Gamma (sum), Theta (sum), Vega (sum).
- **FR-005**: The following columns on the group summary row MUST show "—": Mark, Qty, Type, Strike, IV.
- **FR-006**: Expiry and DTE on the group summary row MUST always show the shared value (all legs in a group share the same expiry by definition of the grouping key).
- **FR-007**: Each group summary row MUST have a ▶/▼ chevron as the sole click target for expand/collapse. Clicking anywhere else on the summary row MUST do nothing.
- **FR-008**: When any leg contributing to a summed Greek was sourced from Black-Scholes, the BS badge MUST appear next to that Greek's aggregated value on the summary row.
- **FR-009**: Thesis group assignment MUST have no effect on whether a position is grouped — grouping is driven solely by underlying symbol.
- **FR-010**: The grouping key MUST be the combination of underlying symbol and expiry date. Two positions on the same underlying but different expiries MUST form separate groups.

### Key Entities

- **UnderlyingGroup**: A runtime-only grouping of 2+ positions that share the same underlying symbol AND expiry date. Has a label (e.g., "QQQ · 2026-06-20"), a list of legs, an expanded/collapsed state, and an aggregated metrics row.
- **AggregatedSummary**: Derived from an UnderlyingGroup for display — sums P&L and Greeks across legs; shows "—" for non-additive columns.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader with positions on 3 different underlyings (2+ legs each) sees 3 rows by default — not 6 or more — without configuring anything.
- **SC-002**: Every collapsed group summary row displays a non-blank value in the P&L, Delta, Gamma, Theta, and Vega columns (assuming at least one leg has a value for each).
- **SC-003**: Expand and collapse each complete instantly (imperceptible delay to the user).
- **SC-004**: Zero regressions on underlyings with a single position — those continue to render as individual rows unchanged.
- **SC-005**: Traders with no thesis groups configured see the same grouping behaviour as traders with thesis groups configured.

## Assumptions

- Grouping is determined at render time from live position data — no configuration or manual assignment required.
- Thesis group assignments, if present, are ignored for the purpose of grouping. They may still display as a badge within expanded leg rows for reference.
- Collapse/expand state is in-memory only and resets on every re-render. Persisting expand state is out of scope.
- All positions in a group share the same underlying symbol by definition (that is the grouping key), so the Underlying column on the summary row always shows a value.
- The chevron toggle is the only interactive element on a group summary row (consistent with prior spec FR-003 from feature 010).
