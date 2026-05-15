# Quickstart: Fix Covered Call Screener — 100-Share Lot Filter

## Verify the lot-size filter

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

All tests must pass.

---

## Verify screener result caching

### Behaviour to confirm

1. **Initial load** (cold cache): Navigate to `/screener`. The screener auto-fetches from
   Schwab on first visit (`screener_results` key absent from sessionStorage). Results render
   after the Schwab API round-trip.

2. **Subsequent load** (warm cache): Navigate away (e.g., dashboard) then back to `/screener`.
   Results render immediately from sessionStorage — no network request to `/api/screener/refresh`.
   Verify via browser DevTools → Network tab: no call to `/api/screener/refresh` on second load.

3. **Refresh button**: Click the ↻ Refresh button. A new call to `/api/screener/refresh` fires,
   overwrites the cache with fresh results, and re-renders.

4. **Logout clears cache**: Log out (or `eraseAll()` is triggered by a 401). Navigate back and
   log in. The screener fetches fresh data — sessionStorage is empty, so no stale results appear.

5. **Erase all data**: Trigger the erase-all action. sessionStorage is cleared.
   Return to screener — a fresh fetch occurs.

### Inspect the cache manually

In browser DevTools → Application → Storage → Session Storage → `localhost` (or your origin):

- Key: `screener_results`
- Value: JSON array of ScreenerResultView objects (set after first successful Refresh)
- Absent: before first load or after logout/erase

### Fractional share edge case

If your Schwab account reports a position quantity as a decimal (e.g., 100.5), confirm that:
- The screener service floors the value to 100 before the lot-size check (`int(longQuantity)`)
- The position appears as eligible with 1 contract

This is handled in `_fetch_stock_positions` (line 229 of `covered_call_screener.py`).
