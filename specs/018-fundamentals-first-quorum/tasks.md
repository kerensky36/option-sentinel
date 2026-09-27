# Tasks: Fundamentals-First Quorum

**Input**: Design documents from `specs/018-fundamentals-first-quorum/`
**Prerequisites**: plan.md, spec.md, research.md (D-101–D-114), data-model.md, contracts/quorum-api-contract.md, quickstart.md

**Tests**: Required (Constitution IV). Each test task MUST be run and seen failing before its implementation task. Security controls (US2) get failing contract tests first.

**Story map** (spec.md):
- US1 (P1): quorum judges the option on its numbers first
- US2 (P1): faster quorum using browser data
- US3 (P2): honest IV/RV in quorum and screener
- US4 (P2): trustworthy Greeks
- US5 (P3): faster positions refresh

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Confirm the baseline: run `pytest -q` on the branch before any change and record the pass count in the PR checklist. No new dependencies are needed (plan: schwab-py 1.5.1 already has `get_price_history_every_day`, `get_option_chain(from_date, to_date, strike)`, `get_account_numbers`).

---

## Phase 2: Foundational (blocks all stories)

**Purpose**: the models, pure fundamentals math, and refresh-time realised vol plus `as_of`, which every story reads.

### Tests (write first, confirm failing)

- [ ] T002 [P] Create `tests/unit/test_fundamentals.py` for `realised_volatility`:
  - 31 synthetic closes with a known log-return stdev → sample stdev × √252 within 1e-9
  - fewer than 20 returns → `None`
  - any close ≤ 0 → `None`
  - only the last 31 closes are used when more are given (D-102)
- [ ] T003 [P] In `tests/unit/test_fundamentals.py`, add `leg_fundamentals` reference cases (D-103):
  - Call cases:
    - `moneyness_pct` is `(S−K)/S×100`
    - `prob_itm` is `N(d2)`
  - Put cases:
    - `moneyness_pct` is `(K−S)/S×100`
    - `prob_itm` is `N(−d2)`
  - `expected_move = S×σ×√(max(dte,1)/365)`
  - Share-equivalent and dollar Greeks:
    - `position_delta = delta×q×100`
    - `dollar_delta = position_delta×S`
    - `position_gamma = gamma×q×100`
    - `dollar_theta = theta×q×100`
    - `dollar_vega = vega×q×100`
  - IV/RV ratio:
    - `iv_rv_ratio = σ/RV`
    - `None` when RV is `None` or 0
  - Figures that go `None`:
    - missing `S` → moneyness, expected move, prob ITM and dollar delta are all `None`
    - missing σ → expected move and prob ITM are `None`
  - `dte = 0` does not divide by zero
- [ ] T004 [P] In `tests/unit/test_fundamentals.py`, add `position_fundamentals` reference cases (D-104). Each case checks breakevens, max profit/loss, the unbounded flags and `pct_max_profit_captured` against hand-worked values:
  - long call: max profit unbounded, one breakeven at K+cost
  - short put
  - bull call vertical
  - iron condor: two breakevens; max profit = net credit×100×q; max loss = width−credit
  - short strangle: max loss unbounded
  - two-expiry calendar: `single_expiry=False`, all payoff figures `None`
  - net Greeks when one leg's Greek is missing → `None`, not partial
  - `theta_pct_of_remaining` → `None` when the remaining premium is 0
- [ ] T005 [P] In `tests/unit/test_bs_calculator.py`, add `prob_itm(S,K,T,r,sigma,option_type)`:
  - call equals `norm.cdf(d2)`
  - put equals `norm.cdf(-d2)`
  - `T<=0` or `sigma<=0` returns `None`
- [ ] T006 [P] In `tests/unit/test_schwab_client.py`, add `fetch_realised_vols` tests with a fake client whose `get_price_history_every_day` returns candle JSON:
  - one call per distinct underlying
  - `start_datetime` ≈ now−60 days
  - index map: `SPX`/`SPXW`→`$SPX`, `NDX`→`$NDX`, `RUT`→`$RUT`, `VIX`→`$VIX`
  - error or empty candles → `None` for that underlying without raising
- [ ] T007 [P] In `tests/unit/test_schwab_client.py`, test `fetch_positions_and_greeks`:
  - every `PositionView` has the same tz-aware UTC `as_of`
  - every `PositionView` has a populated `fundamentals` object
  - price history runs concurrently with the chain fetch (both awaited via one `gather`)
- [ ] T008 [P] In `tests/contract/test_positions_api.py`, check that `GET /api/positions/refresh` items include `as_of` and a `fundamentals` object with every LegFundamentals key (data-model.md), and that the response is still a JSON array (D-114).

### Implementation

- [ ] T009 In `src/data/models.py`, add `LegFundamentals` exactly as in data-model.md:
  - float-or-null fields: `realised_volatility`, `iv_rv_ratio`, `moneyness_pct`, `expected_move`, `prob_itm`, `position_delta`, `dollar_delta`, `position_gamma`, `dollar_theta`, `dollar_vega`, all default `None`
  - add `PositionFundamentals` with these fields:
    - float-or-null: `net_position_delta`, `net_dollar_delta`, `net_position_gamma`, `net_dollar_theta`, `net_dollar_vega`, `max_profit`, `max_loss`, `pct_max_profit_captured`, `theta_pct_of_remaining`
    - `breakevens: list[float] = []`
    - bools: `max_profit_unbounded`, `max_loss_unbounded`, `single_expiry`
  - `PositionView` gains `as_of: datetime | None = None` and `fundamentals: LegFundamentals = LegFundamentals()`
- [ ] T010 In `src/services/bs_calculator.py`, add `prob_itm()` using the same d1/d2 as `bs_greeks` (makes T005 pass).
- [ ] T011 Create `src/services/fundamentals.py` as pure functions with no I/O:
  - `realised_volatility(closes, *, window=30)`
  - `leg_fundamentals(leg, realised_vol, *, r)`: `leg` is any object exposing the PositionLegContext fields; reuse `prob_itm`
  - `position_fundamentals(legs, net_unrealised_pnl)`: piecewise-linear payoff evaluated at P=0 and at each strike, with the tail slope from `Σq·100` over calls (D-104)
  - makes T002–T004 pass
- [ ] T012 In `src/services/schwab_client.py`, add `fetch_realised_vols(client, underlyings)` with the `$` index map (D-102). Update `fetch_positions_and_greeks` to:
  - `gather` the chain and price-history fetches
  - stamp one `as_of = datetime.now(timezone.utc)`
  - attach `fundamentals=leg_fundamentals(view, rv[underlying], r=RISK_FREE_RATE)`

  Makes T006–T008 pass.

**Checkpoint**: refresh returns fundamentals and `as_of`; all pre-existing tests still pass.

---

## Phase 3: User Story 1 — Quorum judges the option on its numbers first (P1) 🎯 MVP

**Goal**: FR-114 seats. Seats 1–4 see fundamentals only; seat 5 sees fundamentals, research brief and headlines. Seats 1–4 start immediately; headlines ≤ 12 within 48 h.
**Independent test**: with the existing 017 request path (server re-fetch), a quorum returns five cards with the new lenses. Fake-LLM prompts show seats 1–4 carry figures and no headlines or brief.

### Tests (write first, confirm failing)

- [ ] T013 [P] [US1] In `tests/unit/test_news_feeds.py`, add `select_headlines(ticker_items, general_items, *, now, limit=12, ticker_quota=5, max_age=timedelta(hours=48))`:
  - drops items with no `published`
  - drops items older than 48 h
  - dedupes case-folded titles across both lists
  - takes ≤ 5 newest ticker items and fills to 12 with the newest general items
  - fewer ticker items than 5 → more general items fill the gap
  - output is newest first
  - `FEED_TIMEOUT_SECONDS == 3.0`
- [ ] T014 [P] [US1] Update `tests/unit/test_quorum_agents.py`:
  - `SEATS` ids are exactly `greeks_exposure, volatility_pricing, time_decay_pnl, strike_assignment, macro_news_overlay` in that order, and only the last has `uses_news=True`
  - with a recording fake `BaseLlm`, seats 1–4 requests contain the FUNDAMENTALS block and no headline title or brief text
  - seat 5's request contains both
  - with a research agent that sleeps longer than the seats, seats 1–4 complete before research finishes (FR-119)
  - research failure → seat 5 still votes on headlines alone
  - the seat instruction for 1–4 requires citing a figure (FR-115)
  - the research instruction mentions events before expiry (FR-117)
  - privacy scan still passes over every recorded request (SC-107)

### Implementation

- [ ] T015 [US1] In `src/services/news_feeds.py`:
  - set `FEED_TIMEOUT_SECONDS = 3.0`
  - add a pure `select_headlines` (D-112)
  - `fetch_headlines(underlying, *, client=None)` fetches general and ticker feeds separately, then returns `select_headlines(...)` (makes T013 pass)
- [ ] T016 [US1] In `src/data/models.py`:
  - `PositionLegContext` gains `fundamentals: LegFundamentals`
  - `PositionContext` gains `position_fundamentals: PositionFundamentals` and `as_of: datetime`
  - `QuorumResult` gains `as_of: datetime` and `position_fundamentals: PositionFundamentals`
- [ ] T017 [US1] In `src/services/quorum_agents.py`:
  - `Seat` gains `uses_news: bool`; replace `SEATS` with the FR-114 lenses and focus text
  - split `_SEAT_INSTRUCTION` into a fundamentals template (seats 1–4: "form your vote from the FUNDAMENTALS block; cite at least one specific figure") and an overlay template (seat 5: "judge whether news confirms or overrides the fundamentals; cite a headline or research point, or say news was thin")
  - `_seat_message` builds a fundamentals-only DATA block for seats 1–4 and fundamentals + brief + headlines for seat 5
  - refocus `_RESEARCH_INSTRUCTION` on the underlying and scheduled events before expiry (earnings, ex-dividend, macro releases) plus a short macro note
- [ ] T018 [US1] In `src/services/quorum_agents.py`, rework `run_quorum(ctx, *, model=None, seat_timeout=40.0, research_timeout=15.0, headline_fetcher=fetch_headlines)`:
  - start seats 1–4, `headline_fetcher(ctx.underlying_symbol)` and `_research` concurrently
  - start seat 5 once headlines and research have both finished
  - gather votes in `SEATS` order
  - tally unchanged
  - fill `as_of` and `position_fundamentals` on the result

  Makes T014 pass.
- [ ] T019 [US1] In `src/services/quorum_agents.py`, update `build_position_context(legs, *, realised_vols, as_of)`:
  - accept objects exposing the PositionLegContext fields
  - re-derive `LegFundamentals` via `fundamentals.leg_fundamentals`
  - compute `position_fundamentals`
  - raise `ValueError` for 0 legs or more than one underlying

  In `src/api/routes/quorum.py`, pass `realised_vols` from each `PositionView.fundamentals.realised_volatility` and `as_of` from the re-fetched views. Remove the route-level `fetch_headlines` call; `run_quorum` now fetches news. The 017 request path stays for this story.
- [ ] T020 [US1] In `tests/contract/test_quorum_api.py`, update existing 017 contract tests for the new seat ids, `as_of` and `position_fundamentals` in the 200 body, and patch `run_quorum`'s `headline_fetcher` instead of the route's `fetch_headlines`.
- [ ] T021 [US1] In `frontend/static/js/quorum_ui.js`:
  - loading text becomes "five analysts are reviewing the position…"
  - button title becomes "Ask the quorum: close, hold, or roll?"
  - relabel "Headlines used" as "News given to the Macro & News analyst"
  - lens labels come from the server; no hard-coded lens names
- [ ] T022 [P] [US1] In `frontend/static/js/demo_data.js`, update the canned `/api/quorum/vote` result to the five FR-114 lenses with figure-citing rationales and ≤ 12 headlines, and add `as_of` and `position_fundamentals` (017 FR-018 still client-side only).

**Checkpoint**: US1 demoable end to end via the 017 request path.

---

## Phase 4: User Story 2 — Faster quorum using browser data (P1)

**Goal**: FR-110–FR-113. No Schwab re-fetch; strict validation; token check; freshness; "Data as of".
**Independent test**: SC-102 and SC-106 contract tests pass. The browser request carries `{as_of, legs}` with no `account_hash`, and the panel shows "Data as of HH:MM".

### Tests (write first, confirm failing)

- [ ] T023 [P] [US2] Rewrite the request-side cases in `tests/contract/test_quorum_api.py` for the v2 contract (contracts/quorum-api-contract.md), with a fake schwab client that records calls:
  - **200 path**:
    - exactly one `get_account_numbers` call
    - no `get_account`, `get_option_chain` or `get_price_history*` calls (SC-102)
  - **422**, body exactly `{"detail": "Invalid quorum request", "fields": [...]}` and never containing any submitted value:
    - an extra top-level field, and an extra leg field
    - `delta` 1.5, `gamma` −0.1, `implied_volatility` 0 or 11, `strike` 0, `quantity` 0, `days_to_expiry` 1501
    - `underlying_symbol` "spy" or "SPY;DROP", and NaN or Infinity floats
    - 0 legs, 5 legs, two underlyings
    - a body over 16 KiB, and a non-JSON body
  - **409**:
    - `as_of` 16 minutes old
    - `as_of` 3 minutes in the future
  - **401**: Schwab `get_account_numbers` returns 401, the `401_invalid_token` security event is logged, and the fake model is never called
  - **502**: Schwab returns 500 or raises
  - **503**: not configured, with no Schwab call
  - **504**: timeout
  - `Cache-Control: no-store` on responses
  - the 404 case is removed
- [ ] T024 [P] [US2] In `tests/unit/test_quorum_agents.py`, check that `build_position_context` from `QuorumLegIn` re-derives fundamentals from only the leg fields and `realised_volatility`, and matches `leg_fundamentals` output exactly. The privacy scan uses the v2 request (no account hash anywhere).

### Implementation

- [ ] T025 [US2] In `src/data/models.py`, add `QuorumLegIn` with `model_config = ConfigDict(extra="forbid")`. All floats must be finite. Quote the data-model.md bounds verbatim:

  | Field | Bound |
  |---|---|
  | `underlying_symbol` | regex `^\$?[A-Z0-9./^-]{1,10}$` |
  | `option_type` | `"call"` \| `"put"` |
  | `strike` | 0 < x ≤ 1 000 000 |
  | `expiry_date` | today − 1 day ≤ x ≤ today + 4 years |
  | `days_to_expiry` | 0 ≤ x ≤ 1 500 |
  | `quantity` | −100 000 ≤ x ≤ 100 000, x ≠ 0 |
  | `cost` | 0 ≤ x ≤ 1 000 000 |
  | `current_mark` | 0 ≤ x ≤ 1 000 000 |
  | `unrealised_pnl` | \|x\| ≤ 1 000 000 000 |
  | `delta` | −1 ≤ x ≤ 1 or null |
  | `gamma` | 0 ≤ x ≤ 10 or null |
  | `theta` | \|x\| ≤ 10 000 or null |
  | `vega` | 0 ≤ x ≤ 10 000 or null |
  | `implied_volatility` | 0 < x ≤ 10 or null |
  | `underlying_price` | 0 < x ≤ 1 000 000 or null |
  | `realised_volatility` | 0 ≤ x ≤ 10 or null |

  Replace `QuorumRequest` with `extra="forbid"`, `as_of: AwareDatetime`, and `legs: list[QuorumLegIn]` (1–4 items); remove `symbols` and `account_hash`.
- [ ] T026 [US2] In `src/services/schwab_client.py`, add `verify_token(client)`:
  - call `get_account_numbers()`
  - 401 → raise `TokenRejected`
  - any other non-2xx or exception → raise `TokenCheckFailed`
  - never read or log the body (D-107)
- [ ] T027 [US2] Rewrite `src/api/routes/quorum.py` in this order:
  1. `quorum_configured()` else 503.
  2. `await request.body()`: over 16 KiB → generic 422.
  3. `QuorumRequest.model_validate_json`: on `ValidationError` → 422 `{"detail": "Invalid quorum request", "fields": [".".join(map(str, e["loc"])) ...]}`.
  4. Freshness `now−15min ≤ as_of ≤ now+2min` else 409 `{"detail": "Position data is stale — refresh positions and try again"}`.
  5. `verify_token`: `TokenRejected` → `log_security_event("401_invalid_token", request)` + 401 `{"detail": "Missing or invalid token"}`; `TokenCheckFailed` → 502 `{"detail": "Could not verify Schwab login"}`.
  6. `build_position_context(body.legs, realised_vols={...from legs}, as_of=body.as_of)`: `ValueError` → generic 422.
  7. `run_quorum` under 60 s else 504.

  Remove the `fetch_positions_and_greeks` import. Makes T023–T024 pass.
- [ ] T028 [US2] In `frontend/static/js/quorum_ui.js`:
  - `initQuorum` keeps full leg objects per id (not just symbols)
  - `_openPanel` posts `{as_of, legs}`: `as_of` is the oldest leg `as_of`; each leg is mapped to the QuorumLegIn keys only, with `realised_volatility` from `leg.fundamentals?.realised_volatility ?? null`; no `account_hash` and no `symbol`
  - a missing `as_of` on any leg shows the stale message without calling the server
  - `_errorMessage` handles:
    - 409 → "Position data is more than 15 minutes old — refresh positions and try again."
    - 422 → "Quorum request was rejected — refresh positions and try again."
    - 502 → "Could not verify your Schwab login — try again."
    - drop the 404 case
  - `renderResult` shows "Data as of HH:MM" (local time from `result.as_of`) next to the verdict
- [ ] T029 [P] [US2] In `frontend/static/js/demo_data.js`, give demo positions `as_of` (now) and `fundamentals`, so the demo request path builds the same payload shape.

**Checkpoint**: both P1 stories are done. This is the MVP.

---

## Phase 5: User Story 3 — Honest IV/RV in quorum and screener (P2)

**Goal**: FR-109, D-113. Quorum IV/RV is already delivered by Phase 2 + US1; this phase covers the screener.
**Independent test**: with IV 30% and RV 20%, the screener shows `1.50×` and `vol_score` is 100·(1.5−0.8)/0.7 = 100.

- [ ] T030 [P] [US3] Update `tests/unit/test_covered_call_screener.py`:
  - remove the `_iv_rank_from_chain` tests
  - `vol_score` is 0 at ratio ≤ 0.8, 100 at ≥ 1.5, and linear between
  - RV unavailable → `iv_rv_ratio`/`vol_score` are `None` and the composite volatility component is 0
  - IV comes from the recommended call's contract `volatility` (percent → decimal)
  - one `get_price_history_every_day` per ticker
- [ ] T031 [P] [US3] In `tests/contract/test_screener_api.py`, check that response items have `implied_volatility`, `realised_volatility`, `iv_rv_ratio` and `vol_score`, and no `iv_rank`.
- [ ] T032 [US3] Update `src/data/models.py` and `src/services/covered_call_screener.py`:
  - `ScreenerResultView` drops `iv_rank` and gains `implied_volatility`, `realised_volatility`, `iv_rv_ratio`, `vol_score` (all `float | None = None`)
  - delete `_iv_rank_from_chain`
  - `_fetch_call_chain` also returns each contract's `volatility`
  - reuse `schwab_client.fetch_realised_vols` for held tickers
  - `_compute_composite_score(vol_score=..., ...)` keeps the 0.50 weight

  Makes T030–T031 pass.
- [ ] T033 [US3] In `frontend/static/js/screener_ui.js`:
  - the client re-rank uses `result.vol_score || 0` in place of `iv_rank`
  - the column header becomes "IV/RV"
  - cells show `iv_rv_ratio.toFixed(2) + '×'` or "—"
- [ ] T034 [P] [US3] In `frontend/templates/partials/screener_table.html`, rename the `iv_rank_cell` macro to `iv_rv_cell(ratio)` (green when ≥ 1.2, "—" when none) and set the header to "IV/RV".
- [ ] T035 [P] [US3] In `frontend/static/js/demo_data.js`, the demo screener rows use the new fields instead of `iv_rank`.

---

## Phase 6: User Story 4 — Trustworthy Greeks (P2)

**Goal**: FR-106, FR-107, D-109.
**Independent test**: delta −999 → recalculated and labelled `calculated`; gamma 0 → kept and labelled `api`.

- [ ] T036 [P] [US4] In `tests/unit/test_schwab_client.py` (or a new `tests/unit/test_greeks_service.py`), test `build_greeks`:
  - each of −999, NaN, inf and out-of-range values for delta, gamma, theta, vega and IV → `None` then the BS value with `*_source="calculated"`
  - gamma 0.0 → 0.0 with source `api`, and no fallback when all four Greeks are present and one is 0
  - IV 25.3 → 0.253
  - IV −999 → `None`, falling back to a sigma of 0.25
- [ ] T037 [US4] In `src/services/greeks_service.py`:
  - add `_valid(value, lo, hi)` requiring a finite float in range, with ranges delta [−1,1], gamma [0,10], theta [−10000,10000], vega [0,10000], raw IV (0,1000]
  - apply it before building the result
  - change the fallback trigger to `any(v is None for v in (delta, gamma, theta, vega))`

  Makes T036 pass.

---

## Phase 7: User Story 5 — Faster positions refresh (P3)

**Goal**: FR-108, D-110, SC-108.
**Independent test**: the chain request kwargs for one held SPY contract include `from_date`, `to_date` and `strike`, and the Greeks match the full-chain fixture.

- [ ] T038 [P] [US5] In `tests/unit/test_schwab_client.py`, test `_fetch_greeks` with a recording fake client:
  - the underlying is parsed via `_parse_occ_symbol`, not `symbol[:6]`
  - `from_date` is the min held expiry and `to_date` the max
  - `strike=` is set only when exactly one distinct strike is held
  - `contract_type` is CALL or PUT when all held legs share a type, otherwise ALL
  - a held symbol missing from the narrowed response triggers exactly one full-chain retry for that underlying
  - Greeks are identical to the current full-chain behaviour
- [ ] T039 [US5] In `src/services/schwab_client.py`, implement the narrowed `_fetch_greeks` with the single full-chain retry (makes T038 pass).

---

## Phase 8: Polish & Cross-Cutting

- [ ] T040 [P] In `tests/contract/test_data_use_page.py`, check that the Vertex AI row lists the new fundamentals fields, that the positions/Schwab row mentions daily price history for realised volatility, and that the page no longer says the account identifier is sent with a quorum (FR-120). Write first and confirm failing.
- [ ] T041 In `frontend/templates/data_use.html`, update the rows per T040 (makes T040 pass). Constitution I (Data Use Disclosure) requires this in the same change.
- [ ] T042 [P] In `README.md`, rewrite the Quorum capability description to the fundamentals-first seats, and update the privacy table (no account hash sent with quorum; price history fetched for realised vol).
- [ ] T043 Run the full `pytest -q` and `node --check` on every changed JS file (`quorum_ui.js`, `screener_ui.js`, `demo_data.js`); both must be green.
- [ ] T044 Re-read the diff adversarially against Constitution II:
  - no position values in any log line or 4xx body
  - no module-level mutable state added
  - the CSP is unchanged
- [ ] T045 Update the PR #6 description with the implemented scope. Leave quickstart.md browser scenarios 1–11 as a manual checklist, since they need a live Schwab + Vertex AI deployment.

---

## Dependencies & Execution Order

```text
Phase 1 ─► Phase 2 (foundational) ─┬─► US1 (P1) ─► US2 (P1) ─┐
                                   ├─► US3 (P2) ─────────────┤
                                   ├─► US4 (P2) ─────────────┼─► Phase 8
                                   └─► US5 (P3) ─────────────┘
```

- **US2 depends on US1**: both rewrite `quorum.py`, `quorum_agents.py` and `quorum_ui.js`. US1 lands the seat and topology changes on the 017 request path, and US2 then swaps the request path.
- **US3, US4 and US5** depend only on Phase 2 and are independent of each other and of US1/US2. US4 and US5 don't even need Phase 2 beyond T001.
- **Shared files**:
  - `schwab_client.py` is touched by T012, T026 and T039
  - `models.py` by T009, T016, T025 and T032
  - `demo_data.js` by T022, T029 and T035

  Tasks touching the same file run sequentially.

## Parallel Opportunities

- Phase 2 tests T002–T008 are all [P] (T002–T004 share a new file but are separable sections; write together).
- Once Phase 2 is done, run US3 (T030–T035), US4 (T036–T037) and US5 (T038–T039) in parallel with US1, keeping the shared-file caveats above in mind.
- Within US1: T013 ∥ T014; T022 ∥ T017–T021.
- Within US2: T023 ∥ T024; T029 ∥ T025–T028.

## Implementation Strategy

1. **MVP**: Phase 1 → Phase 2 → US1 → US2. This delivers the user's core ask: fundamentals-first votes, faster, with news as an overlay.
2. **Then**: US4 (small, improves every seat's inputs) → US5 (refresh speed) → US3 (screener).
3. **Finish** with Phase 8 before marking the PR ready. Commit after each phase with the phase name in the message, following Constitution III: this spec and tasks are already committed ahead of the code.

**Totals**: 45 tasks — Setup 1, Foundational 11, US1 10, US2 7, US3 6, US4 2, US5 2, Polish 6.
