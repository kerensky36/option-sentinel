# Quickstart: Payoff Graph Verification Protocol (015)

All scenarios use the demo mode accounts. Navigate to the app → click "Try Demo" → select the relevant demo account.

---

## Scenario 1 — Bull Put Spread (AAPL): Graph Opens on Row Click

1. Select "DEMO — Options Spreads" account
2. Observe the positions table has an "AAPL · 2025-07-18" spread group row
3. Click the spread group row (not the ▶ chevron)
4. **Expected**: A payoff graph appears inline below the summary row, above any expanded leg rows
5. **Expected**: The graph title reads "AAPL · 2025-07-18"
6. **Expected**: Two vertical dashed strike lines appear at 185 and 195
7. **Expected**: Max gain annotation is green and reads approximately "+1.90/share" (3.85 - 1.95)
8. **Expected**: Max loss annotation is red and reads approximately "-8.10/share" (195 - 185 - 1.90)

---

## Scenario 2 — Graph Closes on Second Click

1. Follow Scenario 1 to open the AAPL spread graph
2. Click the same summary row again
3. **Expected**: The payoff graph collapses/hides

---

## Scenario 3 — Escape Key Closes Graph

1. Follow Scenario 1 to open the AAPL spread graph
2. Press the Escape key
3. **Expected**: The payoff graph hides

---

## Scenario 4 — Only One Graph Open at a Time

1. Open the AAPL spread graph (Scenario 1)
2. Click the "SPY · 2025-06-20" spread group row
3. **Expected**: The AAPL graph disappears; a new SPY iron condor payoff graph appears

---

## Scenario 5 — Iron Condor (SPY): Four Legs, Four Strike Lines

1. Select "DEMO — Options Spreads" account
2. Click the "SPY · 2025-06-20" spread group row
3. **Expected**: Graph shows exactly 4 vertical strike lines (at 520, 560 for put spread; no, wait — SPY has a put at 520 and a call at 560)
4. **Expected**: The combined payoff curve is flat at the net credit amount between the two short strikes and slopes down beyond each outer strike
5. **Expected**: Max gain and max loss annotations both visible

---

## Scenario 6 — Covered Call (Single Leg): Graph on Standalone Row

1. Select "DEMO — Equities & ETFs" account
2. Observe the positions table has standalone covered call rows (AAPL, NVDA, etc.)
3. Click the AAPL covered call row
4. **Expected**: A payoff graph appears below the row
5. **Expected**: Graph shows a line that is flat at the premium received to the left of the strike, then slopes downward to the right
6. **Expected**: Strike marker at 220.00

---

## Scenario 7 — Chevron Still Works After Graph Feature Added

1. Select "DEMO — Options Spreads" account
2. Click the ▶ chevron on the AAPL spread group row (NOT the row itself)
3. **Expected**: Leg rows expand/collapse as before — no payoff graph appears from chevron click
4. **Expected**: Click the row body → graph appears; click chevron → legs expand; both work independently

---

## Scenario 8 — Max Gain/Loss Values Match Formula

1. Open the AAPL · 2025-07-18 put spread graph
2. Note the annotated max gain value
3. Calculate manually: net premium = 3.85 (received) - 1.95 (paid) = 1.90/share
4. **Expected**: Max gain annotation ≈ +1.90/share
5. Calculate manually: max loss = (195 - 185) - 1.90 = 10 - 1.90 = 8.10/share (loss = -8.10)
6. **Expected**: Max loss annotation ≈ -8.10/share

---

## Scenario 9 — Graph Fits App Theme (Visual Check)

1. Open any payoff graph
2. **Expected**: Dark background consistent with the table; no white or light-grey canvas
3. **Expected**: Minimal chrome — no bold borders, no chart title box, no legend box
4. **Expected**: Font matches app (JetBrains Mono or similar monospace)
5. **Expected**: No chart toolbar, zoom controls, or hover tooltips

---

## Scenario 10 — Graph Not Shown for Non-Option Rows

1. If any equity-only (non-option) positions were to appear in the table, clicking them should not produce a payoff graph
2. **Verification**: All positions in demo mode are options — confirm all rows show a graph on click
3. **Edge case**: Refresh the positions table while a graph is open → graph closes cleanly without error in the browser console
