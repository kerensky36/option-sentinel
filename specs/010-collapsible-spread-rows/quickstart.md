# Quickstart: Collapsible Spread Rows — Visual Verification

These steps verify the feature against each acceptance scenario in spec.md.
No automated frontend test framework exists; this document serves as the
manual test protocol (see plan.md Complexity Tracking).

## Prerequisites

- App running locally (`uvicorn src.api.main:app --reload`)
- Logged in with a Schwab account that has at least 2 open option positions
- OR: positions table populated from cache (click Refresh at least once)

---

## Setup: Create a test spread

1. Open the dashboard at `http://localhost:8000`
2. In the **Thesis Groups** panel, create a new thesis group:
   - Name: `Test Spread`
   - Type: `Credit Spread`
3. Note two position symbols from the positions table (e.g., `AAPL 250117C00200000` and `AAPL 250117C00210000`)
4. Assign both positions to the `Test Spread` thesis group

---

## Verification Scenarios

### SC1 — Collapsed by default (FR-001, FR-002, US1.AC1)

- **Expected**: The positions table shows ONE row labelled `Test Spread` instead of two individual leg rows
- **Check**: Symbol column reads `Test Spread`, not the OCC option symbols
- **Check**: A toggle control (chevron or arrow) is visible on the left of the row
- **PASS if**: Only 1 summary row visible; 0 leg rows visible

### SC2 — Expand toggle (US1.AC2)

- Click the toggle control on the `Test Spread` row
- **Expected**: Two leg rows appear directly below the summary row
- **Check**: Leg rows are visually indented or otherwise distinguished from top-level rows
- **Check**: Both OCC symbols are now visible
- **PASS if**: 2 leg rows appear after clicking

### SC3 — Collapse toggle (US1.AC3)

- With the spread expanded, click the toggle again
- **Expected**: Leg rows disappear; only the summary row remains
- **PASS if**: 0 leg rows visible after second click

### SC4 — Non-spread positions unaffected (US1.AC4)

- Any position NOT assigned to a thesis group should still appear as an individual row
- **PASS if**: Unassigned positions render exactly as before this feature

### SC5 — P&L aggregation (US2.AC1)

- Note the individual P&L for each leg (expand the spread to read them)
- Collapse the spread
- **Expected**: Summary row P&L = sum of both leg P&L values
- **Check**: Green if net positive, red if net negative
- **PASS if**: P&L matches manual sum

### SC6 — Greeks aggregation (US2.AC2, AC3)

- With spread expanded, note Delta, Gamma, Theta, Vega for each leg
- Collapse the spread
- **Expected**: Summary row Delta = sum of leg deltas; same for Gamma, Theta, Vega
- **PASS if**: Each Greek matches manual sum (within floating point rounding)

### SC7 — Non-additive columns show "—" (US2.AC4–AC6)

- On the collapsed summary row, verify:
  - IV column: "—"
  - Mark column: "—"
  - Qty column: "—"
  - Type column: "—"
  - Strike column: "—"
- **PASS if**: All five columns show "—"

### SC8 — Shared columns (US2.AC7–AC12)

- Symbol: shows thesis group name (`Test Spread`)
- Underlying: shows underlying symbol (e.g., `AAPL`) — same for all legs of a vanilla spread
- Expiry: shows expiry date if both legs share the same expiry
- DTE: shows days-to-expiry if both legs share the same expiry
- **PASS if**: All match expectations

### SC9 — Single-leg thesis group (US1.AC5)

- Create a second thesis group and assign only ONE position to it
- **Expected**: That position renders as a regular individual row with the thesis badge visible
- **No toggle appears**
- **PASS if**: Single position row, no collapse behaviour

### SC10 — Reset on refresh (Edge Cases)

- Expand a spread so legs are visible
- Click **Refresh**
- **Expected**: All spreads return to collapsed state after data reloads
- **PASS if**: Spread rows are collapsed after refresh

### SC11 — Mobile viewport (Principle VI)

- Open DevTools, switch to a mobile viewport (e.g., iPhone 12)
- **Expected**: Toggle is tappable; summary row and leg rows are readable; no horizontal overflow
- **PASS if**: Feature is fully functional on a 390px-wide viewport

---

## Success bar

All 11 scenarios must pass before the feature is considered complete.
