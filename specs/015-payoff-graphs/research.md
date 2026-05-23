# Research: Option Payoff Graphs (015)

## D-001 — Chart Rendering Approach

**Decision**: Hand-rolled inline SVG via DOM string injection — no chart library.

**Rationale**: The payoff curve is a simple polyline with a handful of annotations (strike markers, max gain/loss labels, zero line). A full chart library (Chart.js, D3, Highcharts) would require either a CDN `<script>` tag (blocked by CSP `script-src` policy unless added to allowed origins) or a bundling step the project does not have. Rolling ~150 lines of SVG generation code costs nothing in runtime, avoids bundle weight, and produces a chart that is stylistically identical to the rest of the app because we control every pixel.

**Alternatives considered**:
- **Chart.js via CDN**: Rejected — requires adding CDN to CSP `script-src`; adds ~200 KB; default styles clash with dark theme and require significant override work.
- **D3 via CDN**: Rejected — same CSP issue; D3 is overkill for a static expiration-only line chart.
- **Canvas 2D API**: Considered — Canvas is slightly harder to make accessible and requires extra work for responsive scaling. SVG scales automatically with CSS `width: 100%` and is semantically inspectable.

---

## D-002 — Payoff Math: Formula and `cost` Field Semantics

**Decision**: `cost` is the per-share signed premium basis. Negative for short positions (premium received), positive for long positions (premium paid).

**Formula** (per leg, per share, at expiration):

```
intrinsic(price) = max(price - strike, 0)   [call]
intrinsic(price) = max(strike - price, 0)   [put]

legPayoff(price) = sign(quantity) * intrinsic(price) - cost
```

Expanding:
- Long call (qty > 0, cost > 0): `intrinsic - cost` → profit only above breakeven
- Short call (qty < 0, cost < 0): `-intrinsic - cost` = `|cost| - intrinsic` → profit capped at premium received
- Long put  (qty > 0, cost > 0): `intrinsic - cost`
- Short put (qty < 0, cost < 0): `|cost| - intrinsic`

**Total combined P&L per share at price P**:
```
total(P) = Σ legPayoff_i(P) * |quantity_i|
```

Note: `cost` values in the position data are per-share. The graph displays P&L per share (not per contract) for clarity.

**Verification**: Short put qty=-1, cost=-3.85, strike=195:
- P=200: `|-1| * (sign(-1) * 0 - (-3.85))` = `1 * (0 + 3.85)` = 3.85 ✓ (keep premium)
- P=190: `1 * (-1 * 5 - (-3.85))` = `1 * (-5 + 3.85)` = -1.15 ✓ (loss from assignment)

---

## D-003 — Price Range for the Graph

**Decision**: X-axis spans `[minStrike × 0.65, maxStrike × 1.35]` rounded to clean tick values.

**Rationale**: A 35% band around the outer strikes ensures both the flat premium-received region and the full gain/loss transition are visible for typical short-term spreads. For extreme-width spreads this may still clip, but the max gain/loss annotations always display the dollar value regardless of whether the flat asymptote is visible.

**Alternative**: Fixed ±30% of the mid-strike. Rejected — for wide spreads the lower strike can fall near the edge; the min/max strike anchoring is more reliable.

---

## D-004 — Graph Injection Point in the DOM

**Decision**: Insert a `<tr class="payoff-graph-row hidden" id="payoff-{id}"><td colspan="15">...</td></tr>` immediately after the clicked row. For spread groups, insert between the summary row and the first leg row. For standalone rows, insert after the row itself.

**Rationale**: Keeps the graph visually attached to the position it describes. The `colspan` spanning all 15 columns (Symbol through Thesis) gives the SVG full width without disrupting the table layout. Existing tests for table structure remain unaffected because the graph row carries a dedicated class.

---

## D-005 — Click UX: Graph vs. Leg Expand

**Decision**: The existing ▶ chevron button (`data-spread-toggle`) expands/collapses leg detail rows — this is unchanged. Clicking anywhere else on a spread summary row toggles the payoff graph row. For standalone rows, clicking the row directly toggles the graph.

**Rationale**: These are two different intents (see leg details vs. understand the risk/reward shape). They warrant separate controls. The chevron is the natural "drill down" affordance; the row click is the "visualise" affordance. The click handler explicitly checks `e.target.closest('[data-spread-toggle]')` and returns early if matched, so the two behaviours cannot interfere.

---

## D-006 — Single-Graph Constraint

**Decision**: At most one payoff graph is visible at a time. Opening a new graph first hides any currently open graph.

**Rationale**: Multiple open graphs make the table extremely long and confusing. A single visible graph is sufficient for the primary use case (examining one position at a time). Implementation: module-level `let openGraphId = null`; each toggle first hides `openGraphId` if set, then opens the new one.

---

## D-007 — Test Strategy for Payoff Math

**Decision**: Write Python unit tests in `tests/unit/test_payoff_math.py` that validate the payoff formula numerically. The JS implementation must produce identical results for the same inputs.

**Rationale**: The project has no JS test runner (no Jest/Vitest). The payoff math is pure arithmetic with no side effects — the formula is identical in Python and JavaScript. Python tests let us satisfy Principle IV (Test-First) and confirm correctness before writing the JS implementation. Any discrepancy between Python and JS implementations is detectable by running the Python tests against manually verified expected values, then confirming the JS function output in the browser during the quickstart verification.

**Covered cases**:
1. Single short put at expiry (standard covered-put payoff)
2. Single long call (long call payoff)
3. Bull call spread (two legs combined)
4. Put spread (two legs)
5. Iron condor (four legs)
6. Max gain and max loss values match analytical formulas
