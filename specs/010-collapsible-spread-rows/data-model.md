# Data Model: Collapsible Spread Rows

No new persistent entities. All data is derived at render time from existing stores.

---

## Runtime Entities (in-memory only, not stored)

### SpreadGroup

Computed by `buildSpreadGroups(positions, assignments, thesisGroups)` before rendering.

| Field | Type | Description |
|-------|------|-------------|
| `thesisGroupId` | string (UUID) | ID of the thesis group |
| `thesisGroupName` | string | Display name of the thesis group |
| `legs` | Position[] | Array of position objects assigned to this group (2+ items) |
| `isExpanded` | boolean | Current expand/collapse state; always `false` on initial render |

### AggregatedRow

Derived from a `SpreadGroup` for rendering the summary row.

| Field | Derived from | Value when uniform | Value when mixed / not applicable |
|-------|--------------|--------------------|-----------------------------------|
| `name` | `thesisGroupName` | — | — |
| `underlying` | `legs[*].underlying_symbol` | shared value | "—" |
| `type` | `legs[*].option_type` | — | "—" (always "—") |
| `strike` | `legs[*].strike` | — | "—" (always "—") |
| `expiry` | `legs[*].expiry_date` | shared value | "—" |
| `qty` | `legs[*].quantity` | — | "—" (always "—") |
| `mark` | `legs[*].current_mark` | — | "—" (always "—") |
| `pnl` | `sum(legs[*].unrealised_pnl)` | — | always summed |
| `dte` | `legs[*].days_to_expiry` | shared value | "—" |
| `delta` | `sum(non-null legs[*].delta)` | — | "—" if all null |
| `gamma` | `sum(non-null legs[*].gamma)` | — | "—" if all null |
| `theta` | `sum(non-null legs[*].theta)` | — | "—" if all null |
| `vega` | `sum(non-null legs[*].vega)` | — | "—" if all null |
| `iv` | — | — | "—" (always "—") |
| `hasBsGreek` | `any(legs[*].{greek}_source === 'calculated')` per Greek | — | per-Greek flag |

---

## Existing Entities (unchanged)

### Position (from Schwab API, cached in sessionStorage)

Relevant fields consumed by this feature:

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | string | OCC option symbol — used to match thesis assignments |
| `underlying_symbol` | string | Used for aggregated Underlying column |
| `option_type` | string | "call" or "put" |
| `strike` | number | |
| `expiry_date` | string | ISO date |
| `quantity` | number | Negative = short |
| `current_mark` | number | Per-unit mark price |
| `unrealised_pnl` | number | Summed for spread P&L |
| `days_to_expiry` | number | |
| `delta`, `gamma`, `theta`, `vega` | number\|null | Summed for spread Greeks |
| `delta_source`, `gamma_source`, `theta_source`, `vega_source` | string\|null | "calculated" = Black-Scholes |
| `implied_volatility` | number\|null | Not aggregated — always "—" on summary row |

### ThesisGroup (from localStorage via thesis_store.js)

| Field | Type | Notes |
|-------|------|-------|
| `id` | string (UUID) | Matched against assignments |
| `name` | string | Displayed in Symbol column of summary row |
| `template_type` | string | Informational only — does not gate collapsible behaviour |

### ThesisAssignment (from localStorage via thesis_store.js)

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | string | OCC option symbol |
| `thesis_group_id` | string\|null | UUID of assigned thesis group |

---

## State Transition: Collapse / Expand

```
Initial render
      │
      ▼
[COLLAPSED] ◄──── re-render (refresh / account switch)
      │
   toggle click
      │
      ▼
[EXPANDED]
      │
   toggle click
      │
      ▼
[COLLAPSED]
```

Collapse state lives only in the DOM (`hidden` class on leg rows). No sessionStorage or
localStorage involved.
