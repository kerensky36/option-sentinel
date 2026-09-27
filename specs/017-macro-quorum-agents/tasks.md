# Tasks: Macro News Voting Quorum

**Input**: Design documents from `specs/017-macro-quorum-agents/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/quorum-api-contract.md

**Tests**: Required (Constitution IV). Each test task MUST be seen failing before its implementation task.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Constitution v3.3.0 — approved and applied by project owner request (research D-008)
- [x] T002 [P] Add `google-adk==2.10.0` and `feedparser==6.0.14` to `requirements.txt`
- [x] T003 [P] Document `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `QUORUM_MODEL` in `.env.example`

## Phase 2: Foundational

- [x] T004 Add QuorumRequest, PositionLegContext, PositionContext, Headline, AnalystBallot, AnalystVote, TallyEntry, QuorumResult to `src/data/models.py` (data-model.md)

## Phase 3: User Story 1 — Ask the Quorum About One Position (P1) 🎯 MVP

### Tests (write first, confirm failing)

- [x] T005 [P] [US1] `tests/unit/test_quorum_tally.py` — spec scenarios 2–4 and exhaustive 4⁵ check against FR-007 (SC-002)
- [x] T006 [P] [US1] `tests/unit/test_news_feeds.py` — parse CNBC/Yahoo/Bloomberg fixture XML, HTML stripping, non-http links dropped, dedupe, newest-first, 30 cap, failing feed tolerated
- [x] T007 [P] [US1] `tests/unit/test_quorum_agents.py` — fake BaseLlm: 5 seats vote, malformed/raising/slow seat → abstain without affecting others, research failure → brief None, no account hash/token in any model request (SC-003), mixed underlyings → ValueError, `quorum_configured()` env rules
- [x] T008 [P] [US1] `tests/contract/test_quorum_api.py` — 200 shape, 401, 404 unknown symbol, 422 (>4 legs, duplicates, mixed underlyings, bad account hash), 503 not configured, 504 timeout, `Cache-Control: no-store`

### Implementation

- [x] T009 [US1] `src/services/quorum_tally.py` — `tally_votes()`
- [x] T010 [US1] `src/services/news_feeds.py` — `FEEDS`, `parse_feed()`, `fetch_headlines()`
- [x] T011 [US1] `src/services/quorum_agents.py` — `SEATS`, researcher + seat agents, `run_quorum()`, `build_position_context()`, `quorum_configured()`
- [x] T012 [US1] `src/api/routes/quorum.py` + register router in `src/api/main.py`
- [x] T013 [US1] `frontend/static/js/quorum_ui.js` — button click → POST → verdict + tally panel; loading/error states; one panel at a time
- [x] T014 [US1] `frontend/static/js/positions_ui.js` — Quorum column on standalone + spread summary rows; call `initQuorum()`
- [x] T015 [US1] `frontend/static/js/payoff_graph.js` — ignore `[data-quorum-btn]` clicks; colspan 15

## Phase 4: User Story 2 — See Why Each Analyst Voted (P2)

- [x] T016 [US2] `quorum_ui.js` — analyst cards (lens, vote, confidence, rationale, roll direction, abstained), macro brief, headline list with publisher + safe links, disclaimer (FR-016, FR-017)

## Phase 4b: User Story 4 — Data Use Disclosure (P2)

- [x] T021 [US4] `tests/contract/test_data_use_page.py` — GET /data-use 200 without auth, lists every data use incl. Vertex AI row and "no user-identifiable or pedigree data"; login page and dashboard link to it (write first, confirm failing)
- [x] T022 [US4] `frontend/templates/data_use.html` + route in `src/api/routes/dashboard.py`; links in `login.html` and `base.html`
- [x] T023 [US4] Quorum panel notice + link (FR-020) in `quorum_ui.js`

## Phase 5: User Story 3 — Demo Mode (P3)

- [x] T017 [US3] `frontend/static/js/demo_data.js` — canned `/api/quorum/vote` response (FR-018)

## Phase 6: Polish

- [x] T018 [P] README: Quorum capability row + privacy table row + setup pointer
- [x] T019 Run full `pytest` suite; `node --check` all changed JS
- [ ] T020 Walk through quickstart.md browser scenarios (manual, needs Vertex-enabled deployment)

## Phase 7: Deployment

- [x] T024 `tests/unit/test_build_frontend.py` + `scripts/build_frontend.py` — pre-render `/data-use` to `dist/data-use/index.html`. Firebase Hosting rewrites every non-`/api`/`/auth` path to `index.html`, so without this FR-019's page is unreachable in production (write test first, confirm failing)
- [x] T025 `tests/unit/test_backend_changed.py` + `scripts/backend_changed.sh` — decide whether the backend needs redeploying by diffing the deployed commit (Cloud Run service label `commit-sha`) against the working tree for backend paths (write test first, confirm failing)
- [x] T026 `scripts/deploy.sh` — single entry point: deploy backend only when T025 says it changed (`--force-backend` / `--skip-backend` overrides), always deploy frontend
- [x] T027 `scripts/deploy_backend.sh` — use `--update-env-vars` (stop wiping vars set outside the script), pass optional `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `QUORUM_MODEL`, `LOG_PEPPER` when set, label the service with `commit-sha`
- [x] T028 `tests/unit/test_deploy_backend.py` + `scripts/deploy_backend.sh` — always pass the Vertex AI variables: `GOOGLE_GENAI_USE_VERTEXAI` defaults to `TRUE`, `GOOGLE_CLOUD_PROJECT` to `GCP_PROJECT_ID`, `GOOGLE_CLOUD_LOCATION` to the Cloud Run region; `.env` values override; `GOOGLE_GENAI_USE_VERTEXAI=FALSE` disables the quorum (write test first, confirm failing)

## Dependencies

T001–T004 → tests T005–T008 (fail) → T009–T012 (pass) → T013–T015 → T016 → T017 → T018–T020.
