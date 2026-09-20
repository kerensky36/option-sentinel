# Quickstart: T+0 Payoff Overlay Verification Protocol (016)

All scenarios use the demo mode accounts, same as specs/015. Navigate to the app → click "Try Demo" → select "DEMO — Options Spreads". Assumes `demo_data.js` has been updated with a plausible `underlying_price` per position (task-phase change): AAPL ≈ 190, SPY put/call spread ≈ 535, TSLA ≈ 288, SPY iron condor ≈ 555.

---

## Scenario 1 — Today Curve Appears Alongside Expiration Curve

1. Click the "AAPL · 2025-07-18" spread group row (57 days to expiry, IV ~0.30/0.29 on its legs)
2. **Expected**: Two curves are visible — the existing orange/reference Expiration curve, and a second, visually distinct "Today" curve
3. **Expected**: Between the two strikes (185/195), the Today curve's value differs visibly from the Expiration curve's value (extrinsic value present)
4. **Expected**: Far from both strikes, the two curves converge toward the same asymptote

---

## Scenario 2 — Price Marker Shows Both Values

1. Continue from Scenario 1
2. **Expected**: A vertical marker appears at ~$190 (the fixture's AAPL underlying price)
3. **Expected**: The marker is labeled with both the Today curve's P&L and the Expiration curve's P&L at that price
4. **Expected**: The two labeled values differ from one another (matches Scenario 1's extrinsic-value observation)

---

## Scenario 3 — Checkpoint Control Redraws the Second Curve

1. Continue from Scenario 1
2. Select the "+1 week" checkpoint
3. **Expected**: The Today curve redraws to a shape between the original Today curve and the Expiration curve; the Expiration reference curve is unchanged
4. Select "+2 weeks"
5. **Expected**: The curve moves further toward the Expiration curve's shape than "+1 week" did
6. Select "Expiration"
7. **Expected**: The checkpoint-controlled curve now coincides exactly with the reference curve — visually, only one line is distinguishable

---

## Scenario 4 — Checkpoint Resets to "Today" on Reopen (FR-013)

1. Open the AAPL spread graph, select "+2 weeks"
2. Close the graph (click the row again)
3. Click the "SPY · 2025-06-20" spread group row to open a different graph
4. **Expected**: The new graph opens with "Today" selected, not "+2 weeks"
5. Close it, reopen the AAPL graph
6. **Expected**: The AAPL graph also reopens on "Today" — the earlier "+2 weeks" selection was not remembered

---

## Scenario 5 — Checkpoint Availability Near Expiration

1. Find or temporarily note a position with fewer than 14 days to expiry (the SPY put/call spread fixture is 29 DTE — both +1wk and +2wk available; use browser devtools to inspect a shorter-DTE case, or verify via `tests/unit/test_bs_pricing.py`'s availability cases if no fixture is short enough)
2. **Expected**: For a position with 10 days to expiry, "+2 weeks" is not selectable; "+1 week" and "Today" are
3. **Expected**: For a position with 5 days to expiry, only "Today" and "Expiration" are selectable

---

## Scenario 6 — Iron Condor (Four Legs): Overlay Still Applies

1. Click the "SPY · 2025-08-15" iron condor spread group row (86 DTE)
2. **Expected**: Today curve and Expiration curve both render correctly across all four strikes (530/540/575/585)
3. **Expected**: Price marker at ~$555 labels both curves
4. Switch through all four checkpoints
5. **Expected**: No errors; each checkpoint redraws correctly

---

## Scenario 7 — Single-Leg Position: Overlay Still Applies

1. Select "DEMO — Equities & ETFs" account
2. Click a standalone covered call row
3. **Expected**: Today curve and Expiration curve both render (assuming the fixture has a valid IV and DTE > 0); checkpoint control is present and functional

---

## Scenario 8 — Missing IV Falls Back Gracefully (FR-008)

1. Using browser devtools, temporarily edit one leg of a cached position to have `implied_volatility: null` (or use a fixture already lacking it, if one exists)
2. Reload/re-render the positions table and open that position's graph
3. **Expected**: Only the Expiration curve renders — no Today curve, no checkpoint control, no console error

---

## Scenario 9 — Missing Underlying Price Falls Back Gracefully (FR-007)

1. Using browser devtools, temporarily edit a position to have `underlying_price: null`
2. Open that position's graph
3. **Expected**: Both curves still render (if IV/DTE are otherwise valid); no vertical price marker appears; no console error

---

## Scenario 10 — No Regression to Existing Expiration-Only Behavior

1. Re-run specs/015's quickstart Scenarios 1–10 in full
2. **Expected**: All still pass unchanged — strike lines, max gain/loss annotations, chevron/graph click separation, single-graph-at-a-time, Escape-to-close, and dark-theme styling are all identical to before this feature
