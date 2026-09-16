# Research: Auto-Group Spreads by Underlying + Expiry

## Decision 1: Grouping Key

**Decision**: Use the composite key `(underlying_symbol, expiry_date)`.

**Rationale**: Two positions with the same underlying but different expiries are logically independent (e.g., a Jun QQQ spread and a Jul QQQ spread). Grouping by underlying alone would mix their Greeks and P&L, producing meaningless aggregates. Using `(underlying, expiry)` keeps each spread cohesive. The user confirmed option B explicitly.

**Alternatives considered**:
- Underlying only (A): Rejected — misleads on calendar spreads.
- Underlying + expiry + strike range: Over-engineered for the current need; no basis for adding strike range heuristics without further user input.

---

## Decision 2: Group Label Format

**Decision**: `"UNDERLYING · EXPIRY"` — e.g., `"QQQ · 2026-06-20"`.

**Rationale**: Expiry is always shared within a group by definition, so displaying it in the label gives immediate context without expanding. The `·` separator is visually distinct from a dash (which could be confused with a negative sign in P&L).

**Alternatives considered**:
- Underlying only as label: Would not distinguish Jun from Jul groups at a glance.
- Full ISO date vs. short month: Full ISO (`2026-06-20`) is already used in the legs rows — consistency avoids confusion.

---

## Decision 3: Thesis Group Assignment Impact

**Decision**: Thesis assignments have no effect on grouping. They MAY still appear as a badge on expanded leg rows (purely informational).

**Rationale**: The user's intent is that grouping should work without thesis setup. Thesis badges are useful context when a trader has set them up, but they are not a grouping gate.

**Alternatives considered**:
- Remove thesis badges entirely: Out of scope; that is a separate UX decision.
- Use thesis group as tie-breaker: Adds complexity without user value.

---

## Decision 4: Group ID for DOM Attributes

**Decision**: Use `encodeURIComponent(underlying_symbol + '|' + expiry_date)` as the group ID string stored in `data-spread-id` and `data-spread-leg` attributes.

**Rationale**: The composite key contains a `|` separator that is valid in HTML attribute values but may cause unexpected parsing in some CSS selectors. `encodeURIComponent` produces a safe, unique, reversible key. The existing toggle listener uses `getAttribute` — not a CSS selector — so this is safe.

**Alternatives considered**:
- Hash (SHA): Unnecessary complexity for a client-only ID.
- Sequential integer index: Breaks on re-render if position order changes.

---

## Decision 5: `getThesisGroups` Import

**Decision**: Remove the `getThesisGroups` import from `positions_ui.js`. Retain `getAssignments` for thesis badges on expanded leg rows.

**Rationale**: `getThesisGroups` is only used by the old `buildSpreadGroups` to build the `groupMap`. The new function derives groups entirely from position data. `getAssignments` is still needed if thesis badges are shown on leg rows.

**Alternatives considered**:
- Keep both imports unused: Violates Principle V (Simplicity Boundary) — dead imports.
