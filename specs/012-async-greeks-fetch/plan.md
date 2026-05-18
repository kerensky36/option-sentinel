# Implementation Plan: Parallel Greeks Fetch

**Branch**: `012-async-greeks-fetch` | **Date**: 2026-05-17 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/012-async-greeks-fetch/spec.md`

## Summary

`_fetch_greeks` in `src/services/schwab_client.py` currently issues one `get_option_chain` call per unique underlying in a serial `for` loop. For a portfolio with N underlyings this means N sequential Schwab round-trips. The change extracts the per-underlying fetch into a named inner coroutine and uses `asyncio.gather(return_exceptions=True)` to fire all calls concurrently. Results are merged after all tasks complete. No public API, data model, UI, or test contract changes.

## Technical Context

**Language/Version**: Python 3.14  
**Primary Dependencies**: FastAPI, schwab-py==1.5.1 (httpx AsyncClient backend), asyncio (stdlib)  
**Storage**: N/A — stateless, ephemeral per-request  
**Testing**: pytest  
**Target Platform**: Linux server (Cloud Run)  
**Project Type**: web-service  
**Performance Goal**: Greeks fetch time ≈ single Schwab round-trip regardless of N underlyings  
**Constraints**: Public signatures of `_fetch_greeks` and `fetch_positions_and_greeks` must not change; per-underlying error isolation must be preserved  
**Scale/Scope**: Typical portfolio has 2–10 distinct underlyings

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Check | Result |
|-----------|-------|--------|
| I — Privacy-First / stateless server | `asyncio.gather` runs entirely within the request lifetime; no data escapes the request scope | ✅ Pass |
| I — sessionStorage for client data | No client-side changes | ✅ N/A |
| II — Zero shared server state | No module-level variables or caches added | ✅ Pass |
| II — No sensitive output in logs | No new logging added | ✅ Pass |
| III — Spec-Before-Code | spec.md committed before implementation | ✅ Pass |
| IV — Test-First | Failing tests written before implementation (enforced in tasks) | ✅ Tracked |
| V — Simplicity Boundary | `asyncio.gather` is stdlib; no new abstractions | ✅ Pass |

**Post-Phase-1 re-check**: No design change introduced; all gates still pass.

## Project Structure

### Documentation (this feature)

```text
specs/012-async-greeks-fetch/
├── plan.md              # This file
├── research.md          # Phase 0 — concurrency decisions
├── data-model.md        # Phase 1 — confirms no new entities
├── quickstart.md        # Phase 1 — 8-scenario verification protocol
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (affected files only)

```text
src/
└── services/
    └── schwab_client.py   # _fetch_greeks — the only file changed

tests/
└── unit/
    └── test_schwab_client.py   # new test file for _fetch_greeks
```

No new files are added to `src/`. No frontend, template, or route changes.

## Implementation Approach

### The Change (conceptual)

**Before** — serial loop:
```
for underlying, sym_list in underlying_to_symbols.items():
    try:
        resp = await client.get_option_chain(underlying, ...)
        # parse and add to greeks_by_symbol
    except Exception:
        pass
```

**After** — parallel gather:
```
async def _fetch_one(underlying, sym_list) -> dict[str, dict]:
    try:
        resp = await client.get_option_chain(underlying, ...)
        # parse and return partial dict
    except Exception:
        return {}

results = await asyncio.gather(
    *[_fetch_one(u, s) for u, s in underlying_to_symbols.items()],
    return_exceptions=True,
)
greeks_by_symbol = {}
for r in results:
    if not isinstance(r, Exception):
        greeks_by_symbol.update(r)
```

Key properties preserved:
- `_fetch_one` catches its own exceptions — same isolation as today
- `return_exceptions=True` means a failure in one task does not cancel or propagate to others
- `asyncio.gather` with one coroutine behaves identically to a single `await`
- `asyncio` is stdlib — no new dependency

### Test-First Requirements (Principle IV)

Three failing tests must exist and be confirmed red before the implementation change:

| Test name | What it proves |
|-----------|---------------|
| `test_fetch_greeks_issues_calls_concurrently` | All `get_option_chain` calls are issued before any resolves (uses asyncio event tracking or call-count assertion) |
| `test_fetch_greeks_one_failure_does_not_block_others` | When one underlying raises, other underlyings' Greeks are still returned |
| `test_fetch_greeks_empty_symbols_returns_empty_dict` | Empty input returns `{}` with no API call issued |

Existing tests in `tests/contract/test_positions_api.py` cover correctness and schema — those must continue to pass green throughout.

## Complexity Tracking

No constitution violations. No entries required.
