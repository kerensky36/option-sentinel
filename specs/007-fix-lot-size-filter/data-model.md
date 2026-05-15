# Data Model: Fix Covered Call Screener — 100-Share Lot Filter

## Modified Entity: ScreenerResultView

**File**: `src/data/models.py`

| Field | Type | Change | Description |
|-------|------|--------|-------------|
| `contracts` | `int` | **NEW** | Number of available 100-share option contracts = `shares // 100`. Always ≥ 1 for positions that pass the lot-size gate. |

All other fields on `ScreenerResultView` are unchanged.

### Validation Rules

- `contracts` is set to `shares // 100` by the screener service at construction time.
- Only positions where `shares > 0 and shares % 100 == 0` reach result construction;
  all others are filtered before a `ScreenerResultView` is created.
- `contracts` is therefore always a positive integer in any result returned to the caller.

## Filter Logic (not a model entity — documented here for completeness)

The lot-size gate in `run_screener()`:

```
if shares <= 0 or shares % 100 != 0:
    skip position (no ScreenerResultView created)
```

This gate runs before any Schwab option chain API call for the position.
