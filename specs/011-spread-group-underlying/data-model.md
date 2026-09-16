# Data Model: Auto-Group Spreads by Underlying + Expiry

No new persistent entities. All data is derived at render time from the positions array already in sessionStorage.

---

## Runtime Entities (in-memory only)

### UnderlyingGroup

Computed by the new `buildSpreadGroups(positions)` before rendering.

| Field | Type | Description |
|-------|------|-------------|
| `groupId` | string | `encodeURIComponent(underlying + '\|' + expiry)` — used as DOM attribute value |
| `groupName` | string | Display label: `"QQQ · 2026-06-20"` |
| `underlying` | string | Underlying symbol (shared across all legs) |
| `expiry` | string | ISO expiry date (shared across all legs) |
| `legs` | Position[] | 2+ position objects with this underlying+expiry |
| `isExpanded` | boolean | Always `false` on initial render |

### AggregatedSummary

Derived from an `UnderlyingGroup` for display on the collapsed summary row.

| Field | Derived from | Notes |
|-------|--------------|-------|
| `pnl` | `sum(legs[*].unrealised_pnl)` | Always computed |
| `underlying` | `group.underlying` | Always present — same as group key |
| `expiry` | `group.expiry` | Always present — same as group key |
| `dte` | `sharedOrNull(legs[*].days_to_expiry)` | Should be uniform; shows "—" only if data inconsistency |
| `delta` | `sum(non-null legs[*].delta)` | "—" if all null |
| `gamma` | `sum(non-null legs[*].gamma)` | "—" if all null |
| `theta` | `sum(non-null legs[*].theta)` | "—" if all null |
| `vega` | `sum(non-null legs[*].vega)` | "—" if all null |
| `hasBsGreek.{greek}` | `any(legs[*].{greek}_source === 'calculated')` | Per-Greek BS badge flag |

Always "—" columns (never computed): Mark, Qty, Type, Strike, IV.

---

## Grouping Key

```
groupKey = encodeURIComponent(position.underlying_symbol + "|" + position.expiry_date)
```

Two positions form a group if and only if they share the same `(underlying_symbol, expiry_date)` pair and that group has 2+ members.

---

## State Transition: Collapse / Expand (unchanged from feature 010)

```
Initial render
      │
      ▼
[COLLAPSED] ◄──── re-render (refresh / account switch / page reload)
      │
  chevron click
      │
      ▼
[EXPANDED]
      │
  chevron click
      │
      ▼
[COLLAPSED]
```

Collapse state lives in the DOM (`hidden` class on leg rows) only. No sessionStorage or localStorage involved.
