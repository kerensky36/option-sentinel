# Implementation Plan: Fix Covered Call Screener — 100-Share Lot Filter

**Branch**: `main` | **Date**: 2026-05-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/007-fix-lot-size-filter/spec.md`

## Summary

Two deliverables: (1) The 100-share lot-size gate in `run_screener()` — already implemented,
tested, and merged. Positions where `floor(shares) % 100 != 0` are silently excluded; eligible
positions carry a `contracts = floor(shares) // 100` field. (2) A sessionStorage-backed screener
result cache so that subsequent page loads are sub-second; the cache is cleared on explicit
Refresh, erase-all, and logout (all handled by the existing `eraseAll()` call in `auth.js`).

## Technical Context

**Language/Version**: Python 3.11+ (backend), JavaScript ES modules (frontend)
**Primary Dependencies**: FastAPI 0.136.1, schwab-py 1.5.1, Pydantic v2, Jinja2 3.1.6,
  slowapi 0.1.9 (backend) · Vanilla JS ES modules, no bundler (frontend)
**Storage**: No server-side storage. Client: sessionStorage (Schwab token + screener cache),
  IndexedDB `option-sentinel` (positions), localStorage (thesis). All cleared by `eraseAll()`.
**Testing**: pytest 9.0.3, pytest-asyncio 1.3.0 (backend unit & contract tests)
**Target Platform**: Cloud Run (backend), Firebase Hosting (frontend)
**Project Type**: Web application — Python API backend + vanilla-JS frontend
**Performance Goals**: Screener initial load: no hard ceiling (Schwab API round-trip).
  Subsequent cached load: <1 second (sessionStorage read + DOM render only).
**Constraints**: No server-side user state. All caching is client-side and session-scoped.
  sessionStorage is ephemeral to the browser tab; cleared on logout via `eraseAll()`.
**Scale/Scope**: Multi-user, single-tab session per user; each user has an independent OAuth token.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Privacy-First | ✅ Pass | Lot-size filter adds no persistence. Screener cache uses sessionStorage (tab-local, ephemeral). No server-side caching of user data. Token never in screener cache. |
| II. Security-First | ✅ Pass | No new attack surface. sessionStorage is cleared by existing `eraseAll()`. Screener result data (tickers, premiums) is session-local; not logged server-side. |
| III. Spec-Before-Code | ✅ Pass | Spec updated with caching requirements before implementation of cache feature begins. |
| IV. Test-First | ⚠️ Partial | Lot-size filter tests written before implementation (✅). Screener cache JS module needs a manual verification step; no JS test harness exists in this project. Acceptance is documented in quickstart.md. |
| V. Simplicity | ✅ Pass | Lot-size gate is one `continue` guard. sessionStorage cache is a thin wrapper (~30 LOC). Both justified by explicit requirements. |
| VI. Visual & Responsive | ✅ Pass | No UI layout changes. Existing empty-state and table render unchanged. |

**Constitution violations**: None. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/007-fix-lot-size-filter/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — modified entities
├── quickstart.md        # Phase 1 output — verification steps
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
frontend/
├── static/js/
│   ├── screener_cache.js   NEW — sessionStorage-backed screener result cache
│   └── screener_ui.js      MODIFIED — loads from cache on init; Refresh bypasses cache

src/
├── data/
│   └── models.py           MODIFIED — ScreenerResultView.contracts field (done)
└── services/
    └── covered_call_screener.py   MODIFIED — lot-size gate + contracts calc (done)

tests/
└── unit/
    └── test_covered_call_screener.py   MODIFIED — lot-size filter tests (done)
```

**Structure Decision**: Single project. Backend changes are confined to
`src/services/covered_call_screener.py` and `src/data/models.py`. Frontend changes are
confined to `frontend/static/js/`; no new routes or API endpoints required.

## Complexity Tracking

> No constitution violations. This section is empty.

---

## Phase 0 Research Decisions

See [research.md](research.md) for full rationale. Summary:

| # | Decision | Outcome |
|---|----------|---------|
| 1 | Where to gate lot-size | `run_screener()` before option chain fetch — done |
| 2 | `contracts` field placement | Plain `int` on `ScreenerResultView`, set at construction — done |
| 3 | Empty-state handling | Existing empty-array response + existing UI render — no change needed |
| 4 | Screener result cache storage | sessionStorage — see below |

### Decision 4: Screener Result Cache — sessionStorage

**Decision**: Cache screener results in sessionStorage under key `screener_results`.

**Rationale**:
- `eraseAll()` in `auth.js` calls `sessionStorage.clear()` — logout cache invalidation
  is handled automatically with zero new code.
- sessionStorage survives same-tab page navigation (dashboard → screener → back) so
  the cache is warm when the user returns to the screener.
- Sub-second subsequent loads are achievable: sessionStorage read + JSON.parse + DOM render
  completes in <50ms for a typical screener payload.
- Screener data is tab-local (no cross-tab bleed), consistent with the privacy principle.

**Alternatives considered**:
- IndexedDB: Overkill for a single array payload; adds async complexity. Reserved for
  positions (which have richer offline-cache needs).
- In-memory module variable: Lost on page navigation within the same origin. Rejected
  because navigating away from `/screener` and back would trigger a fresh Schwab fetch.
- localStorage: Survives logout unless explicitly cleared. Rejected — violates
  Principle I (user financial data must not persist beyond session).

---

## Phase 1 Design

### Data Model

See [data-model.md](data-model.md). New addition:

**Screener Result Cache** (client-side, not a server model):

| Storage | Key | Value | Cleared by |
|---------|-----|-------|-----------|
| sessionStorage | `screener_results` | `JSON.stringify(ScreenerResultView[])` | `eraseAll()`, explicit Refresh, erase-all action |

The cache payload is exactly the JSON array returned by `/api/screener/refresh`. No new
server model changes are required.

### Interface Contracts

The `/api/screener/refresh` endpoint contract is unchanged. The cache is an entirely
client-side concern. See existing `tests/contract/test_screener_api.py`.

### Screener Cache Module — `screener_cache.js`

```text
screener_cache.js  (new, ~35 LOC)
  saveScreenerResults(results: object[]) → void
  loadScreenerResults()                  → object[] | null
  clearScreenerResults()                 → void
```

All three functions are synchronous (sessionStorage is sync). `loadScreenerResults`
returns `null` if key is absent or JSON.parse fails (treats corrupted cache as a miss).

### `screener_ui.js` Changes

Current behaviour: `init()` always calls `refreshScreener()` → Schwab API fetch → render.

New behaviour:
- `init()`: call `loadScreenerResults()`. If hit → render immediately (no fetch). If miss → call `refreshScreener()` as before.
- `refreshScreener()`: after successful fetch, call `saveScreenerResults(results)` before rendering.
- Refresh button click: always calls `refreshScreener()` (which re-fetches and overwrites cache). No change to button wiring needed — the button already calls `refreshScreener()` directly.

### Fractional Shares

The existing lot-size gate in `run_screener()` uses `int(longQuantity)` via `_fetch_stock_positions`
(line 229: `long_qty = int(pos.get("longQuantity", 0))`), which already floors fractional
quantities. The gate `if shares <= 0 or shares % 100 != 0` then operates on the integer.
This satisfies the clarified requirement (floor before divisibility check) without any code change.

A test for `fractional_shares_floor` should be added: position with raw qty 100.5 → floor → 100 → eligible, 1 contract.

### Quickstart

See [quickstart.md](quickstart.md) — to be updated with caching verification steps.
