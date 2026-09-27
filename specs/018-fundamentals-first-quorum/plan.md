# Implementation Plan: Fundamentals-First Quorum

**Branch**: `claude/quorum-members-option-greeks-hqkzrd` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/018-fundamentals-first-quorum/spec.md` (amends spec 017)

## Summary

Make the quorum judge an option on its own numbers first, with market news as a second-stage check.

- **Fundamentals at refresh**: a positions refresh computes each leg's fundamentals with a new pure module (`fundamentals.py`) and attaches them to `PositionView` along with an `as_of` time. Realised vol comes from one Schwab price-history call per underlying.
- **Quorum request**: Quorum posts the browser's legs plus realised vol and `as_of`. The server validates strictly, checks freshness, verifies the token with one light Schwab call, re-derives the fundamentals, and runs the five seats.
- **Seats and timing**: four fundamentals seats run immediately, alongside the news fetch and the research agent. The Macro & News Overlay seat waits for news and research and is the only seat that sees them.
- **Fixes in the same change**:
  - Greek placeholder values are rejected and zeros are kept.
  - The option-chain request is narrowed to held expiries and strikes.
  - The screener's fake IV rank is replaced with IV/RV.
  - News is capped at 12 headlines, 5 reserved for the ticker, 48 h max age, 3 s feed timeout.

## Technical Context

**Language/Version**: Python 3.11 (backend), JavaScript ES modules (frontend)

**Primary Dependencies**: Existing only — FastAPI 0.136.1, Pydantic v2, schwab-py 1.5.1 (`get_price_history_every_day`, `get_option_chain(from_date, to_date, strike)`, `get_account_numbers` confirmed present), google-adk 2.10.0, feedparser, httpx, numpy/scipy (already used by `bs_calculator.py`). **No new dependencies.**

**Storage**: None server-side. Browser: positions (now with `as_of` + `fundamentals`) in the existing sessionStorage cache.

**Testing**: pytest + pytest-asyncio; fake ADK `BaseLlm` for seats (existing pattern); fake schwab client objects recording calls; fixture RSS bytes.

**Target Platform**: Cloud Run (unchanged); Firebase Hosting frontend (unchanged).

**Project Type**: Web app (FastAPI + vanilla JS).

**Performance Goals**: Typical time-to-verdict ≥ 5 s faster than spec 017 (SC-101). Hard cap 60 s. Positions refresh no slower than today: the narrower chain request offsets the added price-history call.

**Constraints**: Stateless server; no position data in logs or error bodies; privacy allow-list (FR-113); Schwab ~120 req/min.

**Scale/Scope**: 1 new backend module and 1 new test module; edits to 7 backend files, 5 frontend files, 1 template; test updates in 8 files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design: still passing.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Privacy-First | ✅ | Server keeps nothing between requests. Client data stays in sessionStorage (existing cache). The request drops `account_hash`. The model receives only the FR-113 allow-list, verified by the privacy scan of every model request (SC-107). Data Use page updated in the same change (FR-120). |
| II — Security-First | ✅ | Bearer still required and now **verified with Schwab before any model call** (D-107). Strict schema with `extra="forbid"`, bounded values and a 16 KiB body cap (D-106). 422 bodies never echo submitted values ("Zero sensitive output"). Rate limit 5/min unchanged. The account-hash IDOR rule no longer applies because no hash is sent. Security events: 401 logged via the existing `401_invalid_token`. Prompt-injection surface shrinks: no free-text fields accepted from the browser, and seats 1–4 see no headlines. |
| III — Spec-Before-Code | ✅ | spec.md, plan and design artifacts are committed before any `src/`, `frontend/` or `tests/` change. |
| IV — Test-First | ✅ | Every FR has a failing test first (see quickstart table). Security controls (strict schema, stale 409, token check, no-echo 422) get failing contract tests before implementation. |
| V — Simplicity | ✅ | One new pure module. No caches, no new dependencies, no strategy-specific payoff code (D-104). |
| VI — Visual & Responsive | ✅ | Only small UI changes: a "Data as of" line, a 409 message, and the screener "IV/RV" column. Existing responsive panel unchanged. |

No violations, so the Complexity Tracking table is not needed.

**Trade-off the user accepted**: 017 FR-002 (server re-fetches, never trusts client values) is intentionally withdrawn. A tampered request can only corrupt the caller's own advisory vote. It cannot reach other users' data, place trades, or smuggle identifying data or free text to the model. This is recorded in spec Clarifications. No constitution text is affected.

## Architecture

```text
GET /api/positions/refresh
  _fetch_positions ──► held legs
  gather ┬─ _fetch_greeks (narrowed chain per underlying, D-110)
         └─ fetch_realised_vols (price history per underlying, D-102)
  build_greeks (placeholder guard, D-109)
  fundamentals.leg_fundamentals ──► PositionView{..., as_of, fundamentals}

POST /api/quorum/vote {as_of, legs[]}
  configured? ─► validate (422) ─► fresh? (409) ─► verify_token (401/502)
  build_position_context ─► leg_fundamentals (re-derived) + position_fundamentals
  run_quorum:
    t=0 ┬─ seats 1–4 (fundamentals message, no news)  ─────────────┐
        ├─ fetch_headlines ─► select_headlines (≤12, 48 h) ─┐       │
        └─ _research (underlying + events before expiry) ───┴─► seat 5 (overlay)
    tally_votes (unchanged) ──► QuorumResult{..., as_of, position_fundamentals}
```

## Project Structure

### Documentation (this feature)

```text
specs/018-fundamentals-first-quorum/
├── spec.md
├── plan.md                         # this file
├── research.md                     # D-101 – D-114
├── data-model.md
├── contracts/quorum-api-contract.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md                        # /speckit-tasks (not yet created)
```

### Source Code Changes

```text
src/services/fundamentals.py              NEW    realised_volatility, leg_fundamentals, position_fundamentals (pure)
src/services/greeks_service.py            MODIFY placeholder guard; zero is not missing (D-109)
src/services/bs_calculator.py             MODIFY + prob_itm() helper (N(±d2)) reused by fundamentals
src/services/schwab_client.py             MODIFY narrowed chain (D-110), fetch_realised_vols, verify_token,
                                                 as_of + fundamentals on PositionView
src/services/covered_call_screener.py     MODIFY IV/RV + vol_score replace _iv_rank_from_chain (D-113)
src/services/news_feeds.py                MODIFY 3 s timeout, select_headlines (D-112)
src/services/quorum_agents.py             MODIFY FR-114 seats, two prompt templates, concurrent topology,
                                                 research refocus, build_position_context(QuorumLegIn)
src/data/models.py                        MODIFY LegFundamentals, PositionFundamentals, QuorumLegIn,
                                                 QuorumRequest v2, PositionView/Context/QuorumResult/ScreenerResultView
src/api/routes/quorum.py                  MODIFY manual body parse + generic 422, 409 freshness, token check,
                                                 no Schwab re-fetch, no route-level headline fetch

frontend/static/js/quorum_ui.js           MODIFY send {as_of, legs}; "Data as of"; 409 message; drop account_hash
frontend/static/js/screener_ui.js         MODIFY IV/RV column; vol_score in client re-ranking
frontend/templates/partials/screener_table.html  MODIFY IV/RV column
frontend/static/js/demo_data.js           MODIFY canned quorum (new lenses, as_of); demo positions as_of/fundamentals;
                                                 demo screener fields
frontend/templates/data_use.html          MODIFY Vertex AI row fields; price-history row (FR-120)

tests/unit/test_fundamentals.py           NEW
tests/unit/test_bs_calculator.py          MODIFY prob_itm
tests/unit/test_schwab_client.py          MODIFY placeholder/zero Greeks, narrowed chain kwargs, realised vols, as_of
tests/unit/test_covered_call_screener.py  MODIFY IV/RV, vol_score
tests/unit/test_news_feeds.py             MODIFY select_headlines, timeout
tests/unit/test_quorum_agents.py          MODIFY seats, prompt isolation, concurrency, privacy scan
tests/contract/test_quorum_api.py         MODIFY v2 contract (422/409/401/502, no Schwab re-fetch)
tests/contract/test_positions_api.py      MODIFY as_of + fundamentals in response
tests/contract/test_screener_api.py       MODIFY new fields
tests/contract/test_data_use_page.py      MODIFY new rows
```

**Structure Decision**: Existing single-repo web layout (`src/` backend, `frontend/` static + templates, `tests/unit` + `tests/contract`). No new directories.

## Implementation Order (for /speckit-tasks)

1. **Foundation**: models, then `fundamentals.py` and `prob_itm`, then the Greek guard. All pure and test-first.
2. **US4 + US5** (refresh quality and speed): placeholder guard, narrowed chain, realised vols, `as_of` and fundamentals on `PositionView`.
3. **US1 + US2** (quorum): v2 request and validation, token check, context building, seat recast, concurrency, headline selection, then frontend `quorum_ui.js` and demo data.
4. **US3** (screener IV/RV): backend, then frontend.
5. **Disclosure page, then full suite and quickstart browser checks.**

## Risks

| Risk | Mitigation |
|---|---|
| Price history is empty for index underlyings | `$` prefix map (D-102); falls back to unavailable, never blocks the refresh |
| Narrowed chain misses a held contract (e.g. adjusted/non-standard symbols) | Any held symbol left unmatched triggers one full-chain retry for that underlying; covered by a unit test |
| Cached positions without `as_of` after deploy | Frontend treats a missing `as_of` as stale → asks for refresh (no 422 surprise) |
| Seat 5 alone can't outvote four fundamentals seats | Intended: news is an overlay, not a co-equal lens (user direction) |
