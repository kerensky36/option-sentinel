# Data Model: Parallel Greeks Fetch

**Feature**: 012-async-greeks-fetch  
**Date**: 2026-05-17

## Overview

This feature introduces no new data models, entities, or storage. It is a pure internal refactor of the `_fetch_greeks` function in `src/services/schwab_client.py`.

## Unchanged Contracts

### `_fetch_greeks` return type

```
dict[str, dict]
```

Keys are OCC symbol strings (e.g. `"QQQ   260618P00650000"`).  
Values are dicts with keys: `delta`, `gamma`, `theta`, `vega`, `implied_volatility`, `underlying_price`.

This signature and value structure are identical before and after the change.

### `fetch_positions_and_greeks` return type

```
list[PositionView]
```

Unchanged. Defined in `src/data/models.py`.

## Internal Change Summary

| Before | After |
|--------|-------|
| `for underlying in underlyings: resp = await client.get_option_chain(...)` | `results = await asyncio.gather(*[_fetch_one(u, s) for u, s in underlyings.items()], return_exceptions=True)` |
| One dict built incrementally in loop | One dict built by merging list of dicts from gather |
| Exception per underlying swallowed by `except Exception: pass` | Exception per underlying returned as value by `gather(return_exceptions=True)`, skipped in merge |
