# Visual Verification: Auto-Group Spreads by Underlying + Expiry

After implementation, verify these 8 scenarios manually in the browser. All scenarios use the live positions dashboard.

---

## Scenario 1 — Two-leg same-underlying same-expiry → one collapsed group

**Setup**: Have (or mock) two open positions: QQQ put and QQQ call, same expiry.
**Expected**: One collapsed summary row labelled `"QQQ · <expiry>"`. No individual QQQ rows visible by default.
**Pass**: ✅ One row shown.
**Fail**: ❌ Two individual rows shown, or no row shown.

---

## Scenario 2 — Two-leg groups for two different expiries → two separate rows

**Setup**: Two QQQ Jun positions + two QQQ Jul positions.
**Expected**: Two collapsed rows: `"QQQ · 2026-06-XX"` and `"QQQ · 2026-07-XX"`. Four individual rows hidden.
**Pass**: ✅ Two separate collapsed rows.
**Fail**: ❌ One merged "QQQ" row, or four individual rows.

---

## Scenario 3 — Single position on an underlying → individual row (no group)

**Setup**: One SPY position with no other SPY positions at that expiry.
**Expected**: A regular individual row for SPY — no chevron, no group header.
**Pass**: ✅ Individual row rendered.
**Fail**: ❌ Shows as a group with chevron.

---

## Scenario 4 — Expand a group

**Setup**: A collapsed group row is visible.
**Action**: Click the ▶ chevron.
**Expected**: Chevron rotates to ▼. Individual leg rows appear directly below the summary row, indented.
**Pass**: ✅ Legs visible, chevron ▼.
**Fail**: ❌ Nothing happens, or all rows expand.

---

## Scenario 5 — Collapse an expanded group

**Setup**: A group is expanded (legs visible, chevron ▼).
**Action**: Click the ▼ chevron.
**Expected**: Leg rows hidden, chevron returns to ▶.
**Pass**: ✅ Legs hidden.
**Fail**: ❌ Legs remain visible.

---

## Scenario 6 — Clicking summary row outside the chevron does nothing

**Setup**: A collapsed group row.
**Action**: Click anywhere on the row EXCEPT the ▶ chevron (e.g., the P&L cell).
**Expected**: Nothing happens. Row stays collapsed.
**Pass**: ✅ No change.
**Fail**: ❌ Row expands or any other change occurs.

---

## Scenario 7 — Aggregated metrics on summary row

**Setup**: A two-leg group (e.g., -1 QQQ put + +1 QQQ call).
**Expected on summary row**:
- P&L: sum of both legs (correct sign and colour)
- Delta, Gamma, Theta, Vega: each shows arithmetic sum
- Mark, Qty, Type, Strike, IV: each shows `—`
- Expiry: shows the shared expiry date
- Underlying: shows `—` in the Underlying column (since the label already shows both)

Wait — re-check: Underlying column on the summary row. The label (`Symbol` column) shows `"QQQ · 2026-06-20"`. The separate `Underlying` column should show the underlying symbol since it's always shared. **Correct expected**: Underlying column shows `QQQ`.

**Pass**: ✅ Metrics as described.
**Fail**: ❌ Any metric incorrect.

---

## Scenario 8 — Refresh resets all groups to collapsed

**Setup**: Expand one or more groups.
**Action**: Click the Refresh button and wait for positions to reload.
**Expected**: All groups reset to collapsed (▶ chevron, leg rows hidden).
**Pass**: ✅ All groups collapsed after refresh.
**Fail**: ❌ Any group remains expanded after refresh.
