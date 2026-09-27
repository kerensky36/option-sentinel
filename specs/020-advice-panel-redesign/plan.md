# Implementation Plan: Advice Panel Redesign

**Branch**: `020-advice-panel-redesign` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/020-advice-panel-redesign/spec.md` (amends specs 017, 018, 019)

## Summary

Redesign how quorum advice is requested and shown, and add a model-written summary that cannot contradict the vote or invent numbers.

- **Button**: the Quorum column goes. An `ADVICE(Agentic)` button with a hazard stripe sits in the first cell of every spread summary row and standalone option row. It opens the panel under that row without touching spread expansion or the payoff graph.
- **Panel**: a pure SVG builder draws the radial vote ring (slate HOLD, blue ROLL, hatched orange CLOSE, text on every mark). Beside it sits the summary area; below it, five collapsible analyst rows with cited-figure chips, then a collapsed brief-and-headlines section.
- **Figure catalog**: at vote time the server turns the position fundamentals into a named list of figures, each with a label and a display value. Seats cite figures by name, and the server supplies the values.
- **Two-step summary**: `/api/quorum/vote` returns as today, plus cited figures and an opaque, HMAC-signed `summary_token` that carries the summariser's inputs. The panel then posts the token to a new `/api/quorum/summary`. The server verifies the signature and age (15 min), makes one summariser call (10 s budget, 15 s route limit), fills `{placeholders}` from the catalog, checks the title against the verdict, and removes or discards text containing model-typed digits. Nothing is stored.
- **Post-review (Session b)**: the ADVICE(Agentic) button takes the Erase All Data button's Tailwind classes (D-313). The first successful result per position (row id + sorted leg symbols) is saved in sessionStorage with its summary and reused on later clicks until sign-out, Erase All Data or tab close, with no new requests (D-314, new `quorum_cache.js`).
- **Demo mode**: `demo_quorum.js` builds the catalog, the cited figures and a `demo.` token. `demo_data.js` intercepts `/api/quorum/summary` and answers with a template summary, so the client path is identical and nothing leaves the browser (D-312).

## Technical Context

**Language/Version**: Python 3.11 (backend), JavaScript ES modules (frontend)

**Primary Dependencies**: Existing only. FastAPI, Pydantic v2, google-adk (`LlmAgent` with `output_schema`, as the seats use), slowapi. Standard-library `hmac`, `hashlib`, `base64`, `json` for the token. **No new dependencies.**

**Storage**: None server-side. The summary token is carried by the browser in the DOM for the life of the panel only (017 FR-015). Nothing goes into sessionStorage.

**Testing**: pytest + pytest-asyncio with the fake ADK `BaseLlm` (existing pattern) for seats and the summariser. The Node harness pattern from spec 019 covers the pure JS modules (ring builder, panel renderer, demo summary).

**Target Platform**: Cloud Run backend and Firebase Hosting frontend (unchanged). New env var `QUORUM_SEAL_KEY` is passed by `scripts/deploy_backend.sh` the same way as `LOG_PEPPER`.

**Project Type**: Web app (FastAPI + vanilla JS).

**Performance Goals**: Time to verdict unchanged against the spec 018 build (SC-306). The summary appears or shows as unavailable within 15 s of the verdict.

**Constraints**:
- Stateless server: verification by signature, not storage.
- The privacy allow-list (018 FR-113) and the privacy scan of every model request apply to the summariser too.
- No position data in logs.
- Rate limit 5/min on each route.
- Panel must work at 360 px.

**Scale/Scope**:
- New backend modules: `figure_catalog.py`, `quorum_summary.py`.
- Backend edits: 4 files (models, quorum_agents, quorum route, deploy script).
- New frontend modules: `quorum_ring.js`, and `positions_rows.js` (pure row HTML builders moved out of `positions_ui.js` so they can be tested in Node).
- Frontend edits: 4 files (quorum_ui.js rewrite, positions_ui.js, demo_quorum.js, demo_data.js) and 1 template (`data_use.html`).
- Tests: 3 new test modules, 2 new Node harnesses, and 5 updated.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design: still passing.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Privacy-First | ✅ | The summariser sees only seat outputs, the tally, and figures derived from the FR-113 fields. The summary token holds only those, never the Bearer token or any account identifier. The token lives in the DOM for the panel's life and is never written to browser storage. The data-use page is updated in the same change (FR-322). The existing privacy scan test is extended to the summariser request (FR-314). |
| II — Security-First | ✅ | New endpoint: Bearer required and verified with Schwab (D-305), rate limit 5/min, 24 KiB body cap, and a strict schema with `extra="forbid"`. The token is HMAC-SHA256 signed with a server secret and checked in constant time; a bad, expired or NO_QUORUM token is rejected before any model call (FR-306a, SC-310). If `QUORUM_SEAL_KEY` is unset, the summary route answers 503. Seat rationales enter the prompt inside DATA markers labelled untrusted (FR-308). Model output is checked on the server and escaped on the client. Error bodies never echo the token. Every control gets a failing test first. |
| III — Spec-Before-Code | ✅ | spec.md (with clarifications), plan and design artifacts are committed on this branch before any `src/`, `frontend/` or `tests/` change. |
| IV — Test-First | ✅ | Each FR maps to a failing test in quickstart.md before implementation, including the token checks, placeholder filling, digit and title guards, and the no-summary-call rule for NO_QUORUM. |
| V — Simplicity | ✅ | Two small pure backend modules and one pure JS module. There is no session store, no cache, no streaming and no new dependency. The two-step request was the user's choice (Clarifications). A signed token is the simplest stateless way to trust data coming back from the browser. |
| VI — Visual & Responsive | ✅ | The vote is shown as a picture (ring), with text kept to the summary and collapsed rows. Vote colours avoid P&L and warning colours. At 360 px the layout stacks and the panel is pinned to the visible width. |

No violations, so the Complexity Tracking table is not needed.

## Architecture

```text
POST /api/quorum/vote {as_of, legs[]}            (unchanged checks, 60 s)
  build_position_context
  figure_catalog.build(ctx)  ─► catalog {name: {label, value, display}}
  run_quorum(ctx, catalog)
    seats get catalog names in their message; ballot gains cited[] (≤5 names)
    tally_votes (unchanged)
  QuorumResult{..., votes[].cited_figures[{name,label,display}],
               summary_token: seal({verdict, tally, votes, catalog+tally figures, issued_at})
                              or null when NO_QUORUM / seal key unset}

Browser: render verdict + ring + rows immediately
  verdict == NO_QUORUM ─► fixed text, no request
  token present ─► "Writing summary…" ─► POST /api/quorum/summary {token}

POST /api/quorum/summary {summary_token}         (15 s)
  configured? ─► seal key set? (503) ─► parse (422) ─► verify_token (401/502)
  unseal: HMAC ok? age ≤ 15 min? verdict != NO_QUORUM?  (403 on any failure, no model call)
  summarise (10 s): LlmAgent(output_schema=SummaryDraft), untrusted DATA block
  guard: fill {placeholders}; title/explanation must be clean and must not name
         another action or direction; drop dirty bullets or dissent sentences
  200 {status: "ok", summary{title, explanation, why[], dissent}}
    | 200 {status: "unavailable"}   (model failed, timed out, or failed the guard)
```

## Project Structure

### Documentation (this feature)

```text
specs/020-advice-panel-redesign/
├── spec.md
├── plan.md               # this file
├── research.md           # D-301–D-312
├── data-model.md         # FigureCatalog, CitedFigure, SummaryToken, SummaryDraft, QuorumSummary
├── quickstart.md         # test commands, FR→test map, browser checks
├── contracts/
│   └── quorum-api-contract.md   # vote v3 additions + POST /api/quorum/summary
├── mock/advice-panel-mock.html  # UI reference (revision 3)
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code Changes

```text
src/
├── data/models.py                 # AnalystBallot.cited; CitedFigure; AnalystVote.cited_figures;
│                                  # QuorumResult.summary_token; SummaryDraft; QuorumSummary;
│                                  # SummaryRequest; SummaryResponse
├── services/
│   ├── figure_catalog.py          # NEW (pure): build(ctx) and add_tally(...) → catalog; display formatting
│   ├── quorum_summary.py          # NEW: seal/unseal token; summariser agent + prompt; guard (fill, digits, title)
│   └── quorum_agents.py           # seat message lists catalog names; ballot → cited_figures; token issued
└── api/routes/quorum.py           # vote: attach token; NEW POST /quorum/summary

frontend/
├── static/js/
│   ├── quorum_ring.js             # NEW (pure): ringSvg(result) → SVG string; vote palette constants
│   ├── quorum_ui.js               # rewrite: button HTML, panel layout, rows, expand-all, summary fetch
│   ├── positions_rows.js          # NEW (pure): header, standalone, spread summary and leg row HTML
│   ├── positions_ui.js            # uses positions_rows.js; wiring only
│   ├── demo_quorum.js             # catalog + cited figures + demo token + buildDemoSummary()
│   └── demo_data.js               # intercept /api/quorum/summary in demo mode
└── templates/data_use.html        # disclose the summary request (FR-322)

scripts/deploy_backend.sh          # pass QUORUM_SEAL_KEY like LOG_PEPPER

tests/
├── unit/test_figure_catalog.py            # NEW
├── unit/test_quorum_summary.py            # NEW: seal/unseal, guard, prompt shape, timeout, privacy scan
├── unit/quorum_ui_harness.mjs + test_quorum_ui.py   # NEW: ring, panel and row HTML via Node
├── unit/test_quorum_agents.py             # cited figures, catalog in seat message
├── unit/test_demo_quorum.py               # demo summary + cited figures
├── contract/test_quorum_api.py            # vote token; summary route auth/limits/403/503/200
├── contract/test_data_use_page.py         # summary row present
└── unit/test_deploy_backend.py            # QUORUM_SEAL_KEY passed through
```

**Structure Decision**: Keep the existing layout (FastAPI in `src/`, vanilla ES modules in `frontend/static/js/`). The new logic goes into two pure backend modules and one pure JS module so it can be unit-tested without a model, a browser or the network.

## Implementation Order (for /speckit-tasks)

1. **Foundation**: models, `figure_catalog.py`, and the seal/unseal half of `quorum_summary.py`, each with failing tests first.
2. **US1 (P1)**: button placement and Quorum column removal (positions_ui + quorum_ui button HTML). This is independent of the backend.
3. **US2 (P1)**: `quorum_ring.js` and the panel skeleton (verdict badge, warning banner, ring, tally) on today's result shape.
4. **US4 (P2)**: analyst rows, expand all, the collapsed brief and headlines section, and seat cited figures (backend ballot plus rows).
5. **US3 (P2)**: summary token on the vote result, the `/quorum/summary` route, summariser, guard, the client's second request and its states, and the demo template summary.
6. **Polish**: data-use page, deploy script, 360 px browser check, greyscale check, privacy scan extension.

US1 and US2 ship value with no backend change. US3 depends on the Foundation step and US4's cited figures, because the catalog is shared.

## Risks

- **Seat prompt change affects vote quality.** Adding the catalog and a `cited` list to the seat output could shift how seats vote. Mitigation: the catalog is listed after FUNDAMENTALS, `cited` is optional, and rationale rules are unchanged. SC-105 (018) is re-checked in a live review.
- **The summariser writes digits anyway, so many summaries lose bullets or are discarded.** Mitigation: the prompt has a worked placeholder example and says to avoid number words. SC-309 (8 of 10 summaries shown in full) is the live check. If it fails, tune the prompt before shipping.
- **Token size.** Five rationales (≤600 chars each), the catalog and the tally come to about 6–9 KB after base64, well under the 24 KiB cap.
- **Seal key not configured in production.** The route returns 503 and the panel shows "Summary unavailable", so the votes still work. The deploy script warns when the key is missing.
- **The key differs between Cloud Run instances.** The key comes from an env var shared by every instance. It is never generated per process.
