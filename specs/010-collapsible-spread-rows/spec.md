# Feature Specification: Collapsible Spread Rows

**Feature Branch**: `010-collapsible-spread-rows`
**Created**: 2026-05-16
**Status**: Draft
**Input**: User description: "option spreads should always be collapsible and collapsed by default with all of their metrics added together like pnl etc unless it doesnt make sense to add. show a - in that case"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Spread legs grouped and collapsed by default (Priority: P1)

A trader opens the positions dashboard and has a credit spread (two legs assigned to the same spread thesis group). Instead of seeing two separate rows cluttering the table, they see a single compact summary row for the spread with aggregated metrics. They can expand it to see the individual legs when needed.

**Why this priority**: This is the core behaviour. Without it, a trader running 3–4 spreads sees 6–8 rows for what are logically 3–4 positions, making the table hard to scan. Grouping is the entire point of the feature.

**Independent Test**: Assign two option positions to the same credit_spread thesis group. Reload the positions table. Confirm only one summary row appears for the spread (not two individual rows). Confirm the summary row is collapsed by default.

**Acceptance Scenarios**:

1. **Given** two or more positions are assigned to the same thesis group, **When** the positions table renders, **Then** those positions appear as a single collapsed summary row instead of individual rows.
2. **Given** a spread summary row is visible, **When** the user clicks the ▶ chevron icon, **Then** the individual leg rows appear below the summary row and the chevron rotates to ▼.
3. **Given** a spread is expanded, **When** the user clicks the ▼ chevron icon again, **Then** the individual leg rows collapse and the chevron returns to ▶.
4a. **Given** a spread summary row is visible, **When** the user clicks anywhere on the row except the chevron, **Then** nothing happens (the row is not interactive outside the chevron).
4. **Given** positions are not assigned to any thesis group, **When** the positions table renders, **Then** those positions appear as individual rows (unchanged behaviour).
5. **Given** a thesis group has only one position assigned, **When** the positions table renders, **Then** that position renders as a regular individual row (no collapsible behaviour — a single leg is not a spread).

---

### User Story 2 — Aggregated metrics on the collapsed summary row (Priority: P1)

When the spread summary row is collapsed, the trader sees meaningful aggregated values for the whole spread — not blank cells — so they can assess the spread's overall position at a glance.

**Why this priority**: The collapsed row is only useful if it shows real data. Without aggregated metrics, the trader must always expand to get any information, defeating the purpose of grouping.

**Independent Test**: Collapse a 2-leg spread. Verify P&L shows the sum of both legs. Verify Delta, Gamma, Theta, Vega each show the sum. Verify IV shows "—". Verify Mark shows "—".

**Acceptance Scenarios**:

1. **Given** a collapsed spread summary row, **When** the trader reads the P&L column, **Then** it shows the sum of all leg P&L values with the correct sign and colour (green if net positive, red if net negative).
2. **Given** a collapsed spread summary row, **When** the trader reads the Delta column, **Then** it shows the sum of all leg delta values (net delta of the spread).
3. **Given** a collapsed spread summary row, **When** the trader reads Gamma, Theta, and Vega, **Then** each shows the sum of the respective Greek across all legs.
4. **Given** a collapsed spread summary row, **When** the trader reads the IV column, **Then** it shows "—" (IV is not additive and has no meaningful spread-level value).
5. **Given** a collapsed spread summary row, **When** the trader reads the Mark column, **Then** it shows "—" (per-leg mark prices are not additive).
6. **Given** a collapsed spread summary row, **When** the trader reads the Qty column, **Then** it shows "—" (leg quantities have opposite signs for spreads; the net is misleading).
7. **Given** a collapsed spread summary row, **When** the trader reads the Symbol column, **Then** it shows the thesis group name (e.g., "QQQ Credit Spread").
8. **Given** a collapsed spread summary row, **When** the trader reads the Underlying column, **Then** it shows the underlying symbol if all legs share the same underlying, otherwise "—".
9. **Given** a collapsed spread summary row, **When** the trader reads the Type column, **Then** it shows "—" (legs may be different option types).
10. **Given** a collapsed spread summary row, **When** the trader reads the Strike column, **Then** it shows "—" (legs have different strikes).
11. **Given** a collapsed spread summary row, **When** the trader reads the Expiry column, **Then** it shows the expiry date if all legs share the same expiry, otherwise "—".
12. **Given** a collapsed spread summary row, **When** the trader reads the DTE column, **Then** it shows the days-to-expiry value if all legs share the same expiry, otherwise "—".

---

### Edge Cases

- **Single-leg thesis group**: If only one position is assigned to a thesis group, it renders as a regular individual row with the thesis badge (no collapsible behaviour).
- **Missing Greeks**: If one or more legs has a null Greek value, the sum is still computed for non-null legs; if ALL legs are null for a Greek, show "—".
- **Black-Scholes badge on summary row**: When the summed Greek includes any leg sourced from Black-Scholes, the BS badge should appear on the summary row's aggregated Greek value.
- **Expand state on refresh**: When positions are refreshed, all spreads reset to collapsed (collapsed is always the default, not remembered across refreshes).
- **Thesis group re-used with 1 leg**: If a thesis group previously had 2 legs but one is closed (no longer in the live positions), the remaining single leg renders as a normal row.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The positions table MUST group all positions assigned to the same thesis group (with 2 or more legs present in the current positions list) into a single collapsible summary row.
- **FR-002**: Spread summary rows MUST be collapsed by default whenever positions are rendered (initial load, refresh, or account switch).
- **FR-003**: Each spread summary row MUST have a visible chevron icon (▶/▼) as the sole click target for expand/collapse. Only clicking the chevron triggers the toggle — clicking elsewhere on the summary row does nothing. The chevron MUST be placed in the Symbol cell, to the left of the thesis group name.
- **FR-004**: When expanded, the individual leg rows MUST appear directly below the summary row, visually indented or otherwise distinguished from top-level rows.
- **FR-005**: The summary row MUST display the thesis group name in the Symbol column and the shared underlying symbol (or "—") in the Underlying column.
- **FR-006**: The following columns on the summary row MUST show the sum across all legs: P&L, Delta, Gamma, Theta, Vega.
- **FR-007**: The following columns on the summary row MUST show "—": Mark, Qty, Type, Strike, IV.
- **FR-008**: Expiry and DTE MUST show the shared value if all legs share the same expiry date, otherwise "—".
- **FR-009**: If any leg contributing to a summed Greek was sourced from Black-Scholes, the BS badge MUST appear next to that Greek's sum on the summary row.
- **FR-010**: Positions NOT assigned to any thesis group MUST continue to render as individual rows with no change to existing behaviour.
- **FR-011**: A thesis group with only one position present in the live positions list MUST render that position as a regular individual row (no grouping or collapse toggle).

### Key Entities

- **Spread Summary Row**: A virtual row in the positions table representing a thesis group with 2+ assigned legs; displays aggregated metrics and owns a collapse/expand toggle.
- **Leg Row**: An individual position row that belongs to a spread group; hidden by default, shown when the parent spread row is expanded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trader with 3 two-leg spreads sees 3 rows (not 6) in the positions table by default — a 50% reduction in row count for spread positions.
- **SC-002**: Every collapsed spread summary row displays a non-blank value in the P&L, Delta, Gamma, Theta, and Vega columns.
- **SC-003**: Expand and collapse each complete in under 100ms (instant to the user — no loading state required).
- **SC-004**: Zero regressions in individual (non-spread) position rows — existing rendering, P&L colouring, thesis badge, and BS badge behaviour are unchanged.
- **SC-005**: A trader can read the net P&L and net Greeks for each of their spreads without expanding any row.

## Assumptions

- Spreads are identified by thesis group assignment: any thesis group with 2 or more positions currently present in the live positions list is treated as a spread and rendered as a collapsible group.
- The thesis group `template_type` (credit_spread, protective_put, etc.) does not affect whether grouping occurs — all multi-leg thesis groups are grouped. The type label is available for future use but is not a gate for this feature.
- Collapse/expand state is in-memory only and resets on any re-render (refresh, account switch, page reload). Persisting expand state across navigations is out of scope.
- The expand toggle uses a ▶/▼ chevron icon placed in the Symbol cell. Only the chevron is the click target (FR-003); the rest of the summary row is non-interactive.
- All legs in a real options spread share the same underlying symbol; the spec handles the edge case where they don't by showing "—" in the Underlying column.
- The Thesis column on the summary row can remain empty or show the thesis badge — this is an implementation detail since the entire row already represents the thesis group.

## Clarifications

### Session 2026-05-16

- Q: What area of the spread summary row triggers expand/collapse — the entire row or only the toggle icon? → A: Icon only (chevron ▶/▼). Clicking elsewhere on the summary row does nothing.
