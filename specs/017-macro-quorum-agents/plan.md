# Implementation Plan: Macro News Voting Quorum

**Branch**: `claude/google-adk-options-quorum-jaeq8f` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

## Summary

Add a **Quorum** button to each option / spread row. It calls a new `POST /api/quorum/vote` endpoint that re-fetches the position from Schwab, gathers macro headlines from CNBC, Yahoo Finance and Bloomberg RSS feeds, has a Google ADK research agent (Google Search grounding) write a macro brief, then asks five independent Google ADK analyst agents — each with a fixed macro lens — to vote CLOSE / HOLD / ROLL. A deterministic Python tally turns the five ballots into a verdict (strict 3-of-5 majority, else NO_CONSENSUS / NO_QUORUM). Gemini is reached through Vertex AI in the operator's GCP project. The result panel shows verdict, tally, analyst cards, and the headlines used.

## Technical Context

**Language/Version**: Python 3.11 (backend), JavaScript ES modules (frontend)
**Primary Dependencies**: New — `google-adk==2.10.0` (agents, Vertex AI Gemini via `google-genai`), `feedparser==6.0.14` (RSS parsing). Existing — FastAPI, httpx, slowapi, schwab-py.
**Storage**: None. ADK `InMemorySessionService` created and discarded inside the request. Result is not written to sessionStorage (FR-015).
**Testing**: pytest + pytest-asyncio. ADK seats run against a fake `BaseLlm` subclass — no network in tests. Feeds tested from fixture XML bytes. Route tested with `TestClient` and patched `fetch_positions_and_greeks` / `run_quorum` / `fetch_headlines`.
**Target Platform**: Cloud Run (existing), service account granted `roles/aiplatform.user`.
**Project Type**: Web app (FastAPI + vanilla JS).
**Performance Goals**: < 60 s end to end (FR-012); seats run concurrently so latency ≈ research + slowest seat.
**Constraints**: Stateless; no secrets added (Vertex uses ADC); CSP unchanged (`connect-src 'self'` — all outbound calls are server-side).
**Scale/Scope**: 3 new backend modules, 1 new route, 1 new frontend module, small edits to 4 existing files.

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Privacy-First | ⚠️ BLOCKED — needs user decision | Sending position details to Vertex AI is a new outbound flow that Principle I (v3.2.0) does not permit. A bounded amendment is proposed in research D-008 but has NOT been approved or applied. Proposal: user-initiated, de-identified FR-011 fields only, operator's own GCP project, nothing persisted. SC-003 test proves no account hash/token reaches the model. Result is never persisted (FR-015). |
| II — Security-First | ✅ | Bearer required; `account_hash` validated via existing `fetch_positions_and_greeks` before any model call; strict 5/min rate limit; generic errors; no sensitive logging; input bounded by Pydantic; prompt-injection contained (D-006); all rendered text escaped; outbound links `rel="noopener noreferrer"`. New deps pinned. |
| III — Spec-Before-Code | ✅ | spec/plan/tasks and constitution amendment committed before any `src/`, `frontend/`, `tests/` change. |
| IV — Test-First | ✅ | Tally, feed parsing, agent orchestration, and route contract tests are written and seen failing before implementation. |
| V — Simplicity | ✅ (see Complexity Tracking) | No agent framework abstractions beyond "seat" definitions. Tally is plain Python. |
| VI — Visual | ✅ | Verdict as a coloured badge + tally bars; analyst cards in a responsive grid (1 col mobile, 5 col desktop). |

## Project Structure

### Documentation

```text
specs/017-macro-quorum-agents/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/quorum-api-contract.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code Changes

```text
requirements.txt                         MODIFY — + google-adk==2.10.0, feedparser==6.0.14
.env.example                             MODIFY — Vertex AI + QUORUM_MODEL settings

src/data/models.py                       MODIFY — QuorumRequest, PositionLegContext, PositionContext,
                                                  Headline, AnalystBallot, AnalystVote, TallyEntry, QuorumResult
src/services/quorum_tally.py             NEW — pure tally_votes()
src/services/news_feeds.py               NEW — FEEDS, parse_feed(), fetch_headlines()
src/services/quorum_agents.py            NEW — SEATS, build agents, run_quorum(), quorum_configured(),
                                                build_position_context()
src/api/routes/quorum.py                 NEW — POST /api/quorum/vote
src/api/main.py                          MODIFY — include quorum router

frontend/static/js/quorum_ui.js          NEW — button wiring, panel rendering (escaped)
frontend/static/js/positions_ui.js       MODIFY — Quorum column + initQuorum()
frontend/static/js/payoff_graph.js       MODIFY — ignore clicks on [data-quorum-btn]; colspan 14→15
frontend/static/js/demo_data.js          MODIFY — canned /api/quorum/vote result

tests/unit/test_quorum_tally.py          NEW
tests/unit/test_news_feeds.py            NEW
tests/unit/test_quorum_agents.py         NEW
tests/contract/test_quorum_api.py        NEW
```

## Agent Topology

```text
POST /api/quorum/vote
  │ fetch_positions_and_greeks (existing, validates account_hash)
  │ build_position_context  ──► de-identified PositionContext
  │ fetch_headlines         ──► ≤30 Headlines (CNBC, Yahoo Finance, Bloomberg RSS)
  ▼
  MacroResearcher  (LlmAgent + google_search)  ──► macro_brief (optional; failure → None)
  ▼
  asyncio.gather ─┬─ Seat 1 RatesFed        (LlmAgent, output_schema=AnalystBallot)
                  ├─ Seat 2 Volatility
                  ├─ Seat 3 GrowthInflation
                  ├─ Seat 4 UnderlyingNews
                  └─ Seat 5 PositionRisk
  ▼   (each: own Runner + InMemorySessionService, wait_for 45 s, error → abstain)
  tally_votes()  (pure Python, FR-007) ──► QuorumResult
```

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|--------------------------------------|
| `google-adk` dependency (+ its transitive deps) | User requirement; gives Vertex AI Gemini, structured output, and search grounding in one supported library | Raw `google-genai` would re-implement agent/run/session plumbing and search-grounding wiring |
| `feedparser` dependency | Robust RSS/Atom parsing across three publishers' differing feeds | Hand-rolled `xml.etree` parsing: more code, more edge cases, same outcome |
| Five seats instead of one agent | A quorum is the requested product; independent lenses reduce single-model bias | A single agent cannot "vote" |
| Separate research agent | ADK's `google_search` built-in tool cannot share an agent with structured output / other tools | Giving every seat search would multiply cost and latency by 5 |
