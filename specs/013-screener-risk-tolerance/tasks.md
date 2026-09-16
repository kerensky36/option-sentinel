# Tasks: Screener Risk Tolerance Controls

**Input**: Design documents from `specs/013-screener-risk-tolerance/`  
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ quickstart.md ✅

**Tests**: Required — Principle IV (Test-First) is NON-NEGOTIABLE per the project constitution.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no in-flight dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

- [X] T001 Read `src/services/covered_call_screener.py`, `src/data/models.py`, `frontend/static/js/screener_ui.js`, `frontend/static/js/screener_cache.js`, and `frontend/templates/screener.html` to confirm current structure before making changes

**Checkpoint**: All files read and structure confirmed.

---

## Phase 2: Foundational — Failing Tests (BLOCKS all implementation)

**Purpose**: Write all backend tests RED before touching implementation. Principle IV gate.

**⚠️ CRITICAL**: All tests below MUST be confirmed failing before Phase 3 begins.

- [X] T002 In `tests/unit/test_covered_call_screener.py`, add `test_fetch_call_chain_uses_wide_dte_window`: mock the Schwab client and assert `get_option_chain` is called with `from_date` ≤ today + 7 days and `to_date` ≥ today + 55 days (proving the fetch window spans 7–60 DTE)
- [X] T003 In `tests/unit/test_covered_call_screener.py`, add `test_screener_result_includes_candidates`: mock a stock position with two liquid call options at different DTE values; assert each `ScreenerResultView` in the result has a non-empty `candidates` list
- [X] T004 In `tests/unit/test_covered_call_screener.py`, add `test_candidates_are_liquid_only`: include one option with `bid < 0.05` and one with `open_interest < 100` in the mock chain; assert neither appears in `candidates`
- [X] T005 In `tests/unit/test_covered_call_screener.py`, add `test_balanced_score_matches_current_output`: run the screener mock with a single 30–45 DTE candidate at delta=0.25 and assert `composite_score` equals the value produced by `_compute_composite_score` with the Balanced weights (this test passes GREEN now and must remain GREEN — regression guard)
- [X] T006 In `tests/contract/test_screener_api.py`, add `test_response_has_candidates_field`: assert each item in the screener API response contains a `candidates` key that is a list
- [X] T007 Run `pytest tests/unit/test_covered_call_screener.py tests/contract/test_screener_api.py -v` and confirm T002–T004, T006 are RED (AttributeError or AssertionError); T005 should be GREEN; document failure output

**Checkpoint**: T002–T004, T006 RED confirmed. T005 GREEN confirmed. Implementation may begin.

---

## Phase 3: US1 & US2 — Wide Fetch + Candidates in Response (Priority: P1) 🎯 MVP

**Goal**: Backend returns all liquid candidates per ticker across 7–60 DTE; initial Balanced result unchanged.

**Independent Test**: `pytest tests/unit/test_covered_call_screener.py tests/contract/test_screener_api.py -v` — T002–T006 all GREEN.

### Backend model change

- [X] T008 [US1] Add `candidates: list[dict] = []` field to `ScreenerResultView` in `src/data/models.py`

### Backend screener changes

- [X] T009 [US1] In `src/services/covered_call_screener.py`, rename `_DTE_MIN` → `_FETCH_DTE_MIN = 7` and `_DTE_MAX` → `_FETCH_DTE_MAX = 60`; add `_BALANCED_DTE_MIN = 30` and `_BALANCED_DTE_MAX = 45` as Balanced profile reference constants
- [X] T010 [US1] Update `_fetch_call_chain` in `src/services/covered_call_screener.py` to use `_FETCH_DTE_MIN` and `_FETCH_DTE_MAX` for the `from_date`/`to_date` calculation passed to `get_option_chain`
- [X] T011 [US1] Update `_find_best_call` in `src/services/covered_call_screener.py` to filter `liquid` using `_BALANCED_DTE_MIN`/`_BALANCED_DTE_MAX` (not the new fetch constants) so the server's Balanced pick is unchanged
- [X] T012 [US1] In `run_screener` in `src/services/covered_call_screener.py`, after `chain_options = await _fetch_call_chain(client, ticker)`, build `candidates` list: `[{"delta": o["delta"], "bid": o["bid"], "dte": o["dte"], "strike": o["strike"], "expiry": o["expiry"], "open_interest": o["open_interest"]} for o in chain_options if o["bid"] >= _MIN_BID and o["open_interest"] >= _MIN_OI]`
- [X] T013 [US1] Pass `candidates=candidates` into every `ScreenerResultView(...)` constructor call in `run_screener` in `src/services/covered_call_screener.py` (three call sites: call_written, no_liquid_options, and ranked result)

### Backend validation

- [X] T014 [US1] Run `pytest tests/unit/test_covered_call_screener.py tests/contract/test_screener_api.py -v` — confirm T002–T006 all GREEN
- [X] T015 [US1] Run `pytest tests/ -v` — confirm full suite passes with no regressions

**Checkpoint**: Backend returns candidates, Balanced score unchanged, all tests green.

---

## Phase 4: US1 & US4 — Profile Toggle UI (Priority: P1)

**Goal**: Profile toggle renders in screener, switches profile in sessionStorage, re-scores and re-ranks client-side instantly.

**Independent Test**: Open screener in browser, switch profiles, confirm no network request issued (DevTools Network tab) and ranking changes (quickstart Scenarios 4 & 5).

- [X] T016 [P] [US4] In `frontend/static/js/screener_cache.js`, add `saveScreenerProfile(name)` (writes `sessionStorage.setItem('screener_profile', name)`) and `loadScreenerProfile()` (returns `sessionStorage.getItem('screener_profile') || 'balanced'`); export both functions
- [X] T017 [US1] In `frontend/static/js/screener_ui.js`, add the `PROFILES` constant object with Conservative, Balanced, and Aggressive entries per the parameter table in `specs/013-screener-risk-tolerance/data-model.md`
- [X] T018 [US1] In `frontend/static/js/screener_ui.js`, add `rescoreResult(result, profile)` function: filters candidates by profile DTE window, picks nearest-delta candidate, computes annualised yield, yield score, delta safety, and composite score using profile weights; returns updated result object; returns `insufficient_data` result if no candidates survive DTE filter
- [X] T019 [US1] In `frontend/static/js/screener_ui.js`, add `applyProfile(results, profileName)` function: maps all results through `rescoreResult`, splits into recommended/other, sorts recommended by composite_score descending, calls `renderScreener` with the merged array
- [X] T020 [US1] In `frontend/static/js/screener_ui.js`, add `renderProfileToggle(activeProfile)` function that renders the three-button toggle (Conservative / Balanced / Aggressive) with the active button highlighted; wire each button's click handler to call `saveScreenerProfile(name)` then `applyProfile(cachedResults, name)` using the results stored in the module-level `cachedResults` variable
- [X] T021 [US1] In `frontend/static/js/screener_ui.js`, update `refreshScreener`: after `saveScreenerResults(results, ...)`, store results in module-level `cachedResults`; call `renderProfileToggle(loadScreenerProfile())` then `applyProfile(results, loadScreenerProfile())` instead of calling `renderScreener(results)` directly
- [X] T022 [US1] In `frontend/static/js/screener_ui.js`, update `handleAccountChange`: after loading cached results, set `cachedResults`, call `renderProfileToggle(loadScreenerProfile())` then `applyProfile(cachedResults, loadScreenerProfile())`
- [X] T023 [US1] In `frontend/templates/screener.html`, add a profile toggle container `<div id="screener-profile-toggle"></div>` between the refresh button row and the scoring details panel; the toggle is rendered into this element by `renderProfileToggle`
- [X] T024 [US1] Update the "How Scoring Works" panel in `frontend/templates/screener.html` to mention that the active profile adjusts target delta and DTE window (one sentence, no implementation details)
- [ ] T025 [US4] Verify profile toggle is visible and tappable at 375px viewport width (Chrome DevTools responsive mode); adjust Tailwind classes if any element overflows

**Checkpoint**: Profile toggle live, switching is instant with no network call, session persists across tab navigation.

---

## Phase 5: US2 — Wide Window Verified Client-Side

**Goal**: Confirm the wider DTE window actually surfaces short-DTE candidates when Aggressive is selected.

**Independent Test**: Quickstart Scenarios 5 and 6 — Aggressive shows lower delta / shorter DTE than Balanced for the same ticker.

- [ ] T026 [US2] Open the screener with a live Schwab token, select Aggressive, confirm at least one ticker shows a DTE value below 30 in the Strike/Expiry columns (proving the wider fetch window reached the client and the DTE filter is working)
- [ ] T027 [US2] Run quickstart Scenario 1 (regression diff) — curl before/after diff confirms Balanced output unchanged

**Checkpoint**: Wide window verified, regression confirmed.

---

## Phase 6: US3 — Fine-Grained Sliders (Priority: P2)

**Goal**: Advanced panel with target delta, DTE range, and Safety↔Yield slider re-scores without network calls.

**Independent Test**: Quickstart Scenario 8 — move any slider, observe no XHR in Network tab, results re-rank.

- [X] T028 [P] [US3] In `frontend/templates/screener.html`, add a collapsible `<details id="screener-advanced">` panel below the profile toggle with three `<input type="range">` controls: `screener-delta-slider` (min=0.10, max=0.45, step=0.01), `screener-dte-min-slider` (min=7, max=60, step=1), `screener-dte-max-slider` (min=7, max=60, step=1), `screener-yield-weight-slider` (min=0, max=100, step=1); include a label showing the current value next to each slider; panel is closed by default
- [X] T029 [US3] In `frontend/static/js/screener_ui.js`, add `initAdvancedSliders()` function: reads all four slider elements; on each `input` event, reads current slider values, builds a custom profile object `{targetDelta, dteMin, dteMax, yieldWeight: sliderValue/200, safetyWeight: (100-sliderValue)/200}` (so weights sum to 0.50 split + 0.50 IV = 1.0), calls `applyProfile(cachedResults, customProfile)`; ensure DTE min ≤ DTE max with a clamp; initialises slider values from the active preset when called
- [X] T030 [US3] In `frontend/static/js/screener_ui.js`, call `initAdvancedSliders()` after `renderProfileToggle` in both `refreshScreener` and `handleAccountChange`; when a preset toggle button is clicked, sync slider values to match the selected preset's parameters

**Checkpoint**: Sliders re-rank instantly, no network call, DTE min/max clamped correctly.

---

## Phase 7: Polish & Full Validation

- [X] T031 Run `pytest tests/ -v` — full suite green
- [ ] T032 [P] Run quickstart Scenarios 1–3 (backend correctness and candidates field)
- [ ] T033 [P] Run quickstart Scenarios 4–7 (toggle, profile comparison, session persistence)
- [ ] T034 Run quickstart Scenario 10 (mobile viewport at 375px — toggle visible, advanced panel collapsed)
- [ ] T035 Deploy to Cloud Run + Firebase with `bash scripts/deploy.sh` and smoke-test toggle on live app

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Tests)**: Depends on Phase 1 — BLOCKS Phases 3–6
- **Phase 3 (Backend)**: Depends on Phase 2 RED confirmation
- **Phase 4 (Toggle UI)**: Depends on Phase 3 (needs `candidates` in response to re-score)
- **Phase 5 (Wide Window)**: Depends on Phase 4 (needs live UI to verify)
- **Phase 6 (Sliders)**: Depends on Phase 4 (builds on profile infrastructure)
- **Phase 7 (Validation)**: Depends on all prior phases

### Within Phase 3

- T008 (model) → T009 (constants) → T010 (fetch) → T011 (find_best) → T012 (candidates list) → T013 (pass through) — sequential, same files

### Within Phase 4

- T016 (screener_cache.js) runs in parallel with T017–T024 (screener_ui.js + screener.html are different files but JS changes are sequential)
- T017 → T018 → T019 → T020 → T021 → T022 (sequential within screener_ui.js)
- T023, T024 (screener.html) can run in parallel with screener_ui.js changes

### Parallel Opportunities

- T016 ‖ T017–T024 (different files)
- T026 ‖ T027 (both read-only validation)
- T028 (HTML) ‖ T029–T030 (JS) (different files)
- T032 ‖ T033 (different quickstart scenarios)

---

## Implementation Strategy

### MVP (P1 only — Phases 1–5)

1. Phase 1: Read files
2. Phase 2: Write + confirm RED tests
3. Phase 3: Backend model + screener changes
4. Phase 4: Profile toggle UI
5. Phase 5: Live verification
6. **STOP and validate** — ship P1 toggle; P2 sliders are additive

### Full delivery (add Phase 6)

1. Complete MVP
2. Phase 6: Fine-grained sliders
3. Phase 7: Full validation + deploy

---

## Notes

- `cachedResults` is a module-level variable in `screener_ui.js` — initialised to `[]`, updated on every refresh or cache load
- `rescoreResult` must handle the case where `result.candidates` is undefined or empty (tickers with `insufficient_data` or `suppressed` that came from the server with no candidates)
- Suppressed tickers (call already written) pass through re-scoring unchanged — status stays `suppressed` regardless of profile
- The `composite_score` on suppressed and insufficient_data rows is always 0.0 regardless of profile
