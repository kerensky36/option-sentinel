# Quickstart: Fix Covered Call Screener — 100-Share Lot Filter

## Verify the fix

### Unit tests (no server required)

```bash
source .venv/bin/activate
pytest tests/unit/test_covered_call_screener.py -v
```

Expected: all lot-size filter tests pass.

### Manual verification scenarios

| Position | shares | Expected result |
|----------|--------|-----------------|
| AAPL     | 100    | Appears — 1 contract |
| MSFT     | 200    | Appears — 2 contracts |
| TSLA     | 50     | Filtered out (not shown) |
| NVDA     | 150    | Filtered out (not shown) |
| GOOG     | 300    | Appears — 3 contracts |

### Full regression

```bash
pytest tests/ -q
```

All 78+ tests must pass.
