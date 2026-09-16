# Research: Collapsible Spread Rows

## Decision 1: Spread identification mechanism

**Decision**: A "spread" is any thesis group that has 2 or more positions from the current live
positions list assigned to it, regardless of `template_type`.

**Rationale**: The thesis assignment store (`thesis_store.js`) is already the only client-side
grouping mechanism. Using it avoids any new data structures or UI. The `template_type` field
(credit_spread, protective_put, etc.) is informational and need not gate the collapsible
behaviour — a trader who assigns two legs to a "custom" thesis group clearly intends them as a group.

**Alternatives considered**:
- Filter by `template_type` in ("credit_spread", "protective_put"): Rejected — unnecessarily
  restrictive; a trader could create a custom multi-leg thesis that should also be collapsible.
- New explicit "spread" concept separate from thesis groups: Rejected — overengineering; the
  thesis store already solves grouping.

---

## Decision 2: Collapse toggle mechanism

**Decision**: Use custom JS toggle with `data-spread-id` attributes and a CSS `hidden` class rather
than native `<details>/<summary>` HTML.

**Rationale**: Native `<details>` wrapping `<tr>` elements is invalid HTML (a `<details>` element
cannot be a direct child of `<tbody>`). Custom JS toggle with `data-*` attributes integrates
cleanly with the existing table structure and the existing inline HTML string approach used in
`positions_ui.js`.

**Alternatives considered**:
- `<details>/<summary>` HTML: Rejected — invalid inside `<table><tbody>`. Would require switching
  to a non-table layout, which is a larger change than this feature warrants.
- CSS accordion (checkbox hack): Rejected — even more fragile inside tables; no accessibility benefit.

---

## Decision 3: Aggregation rules per column

| Column | Rule | Rationale |
|--------|------|-----------|
| Symbol | Thesis group name | Identifies the spread, not a single leg symbol |
| Underlying | Shared value if all legs match, else "—" | Meaningful only when uniform |
| Type | "—" | Legs are typically different types (call + put, or call + call with different roles) |
| Strike | "—" | Definitionally different per leg |
| Expiry | Shared value if all legs match, else "—" | Calendar spreads have different expiries |
| Qty | "—" | Net quantity (e.g., -1 + 1 = 0) is misleading |
| Mark | "—" | Per-leg mark prices are not additive |
| P&L | Sum | Net P&L of the spread is the primary metric traders care about |
| DTE | Shared value if all legs match, else "—" | Same logic as Expiry |
| Delta | Sum | Net delta is a standard spread metric |
| Gamma | Sum | Net gamma is a standard spread metric |
| Theta | Sum | Net theta (daily decay) is the primary spread management metric |
| Vega | Sum | Net vega is a standard spread metric |
| IV | "—" | Per-leg IV values are not additive; spread-level IV has no standard definition |
| Thesis | Empty / badge omitted | The entire row *is* the thesis group; badge would be redundant |

---

## Decision 4: BS badge on aggregated Greeks

**Decision**: If any contributing leg has `{greek}_source === 'calculated'` (Black-Scholes), the
BS badge appears on the corresponding summed Greek in the summary row.

**Rationale**: Matches existing convention in `positions_ui.js`; warns the trader that the aggregate
includes an estimated Greek.

---

## Decision 5: dist/ sync

**Decision**: `dist/static/js/positions_ui.js` must be updated alongside the source file.

**Rationale**: The project serves `dist/` in production (Firebase Hosting). There is no automated
build step — the dist copy is manually maintained. A task must explicitly copy/update both files.

**Alternatives considered**:
- Build script: Out of scope for this feature.
- Serve directly from `frontend/`: Not how the project is configured.

---

## Decision 6: Null Greek handling

**Decision**: For each summable Greek, sum only non-null leg values. If all legs are null for a
given Greek, show "—". If at least one leg has a value, show the partial sum (and the BS badge
if any contributing leg was calculated).

**Rationale**: Partial sums are still directionally useful. Showing "—" only when there is truly
no data prevents information loss.
