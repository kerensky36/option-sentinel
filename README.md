# Option Sentinel

> A personal options position monitor built with Claude Pro, spec-driven from day one.

![Status](https://img.shields.io/badge/status-planning%20complete-blue)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20HTMX%20%2B%20SQLite-informational)
![Auth](https://img.shields.io/badge/brokerage-Charles%20Schwab-4a7c59)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What it does

Option Sentinel connects to your Charles Schwab account and gives you a **live, visual dashboard** of every open options position — with Greeks, P&L, and the tools to make informed management decisions without hunting through the brokerage UI.

| Capability | Detail |
|---|---|
| **Live positions** | Pulls all open options legs from Schwab every 5 minutes during market hours |
| **Greeks** | Delta, gamma, theta, vega, IV — sourced from Schwab API, with Black-Scholes fallback |
| **Thesis groups** | Group positions by named thesis (IV crush, earnings fade, directional, etc.) |
| **Exit scoring** | Automatic proximity score (0–100) against P&L %, DTE, and price targets |
| **Alerts** | Email when a spread hits 50% profit, at 14/7/3 DTE, or on binary event flag |
| **Mobile-ready** | Visual-first responsive dashboard — readable on your phone mid-session |

<img width="1284" height="535" alt="image" src="https://github.com/user-attachments/assets/2bcfa959-d30a-4996-aa1b-130d7a3069a9" />

---

## Architecture at a glance

```
Schwab API
    │
    ▼  (every 5 min, market hours)
APScheduler poll job
    │
    ├── schwab-py  ──── positions
    ├── httpx      ──── option chains + Greeks
    └── scipy      ──── Black-Scholes fallback
    │
    ▼
SQLite (local)     ←── all data stays on your machine
    │
    ▼
FastAPI + Jinja2
    │
    ▼
HTMX + Tailwind CSS  ──── Server-Sent Events (5-min push updates)
    │
    ▼
Browser  (localhost:8000)
```

No cloud sync. No third-party analytics. No native mobile app.
Everything runs locally and the only outbound destination is the Schwab API.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async, clean, the obvious Python web choice |
| Frontend | HTMX + Tailwind CSS (CDN) | No build pipeline; server renders everything; SSE for live updates |
| Database | SQLite → Postgres-switchable | Config-only migration path; local default |
| ORM | SQLAlchemy 2.x + Alembic | Standard; migrations keep the Postgres switch effortless |
| Scheduler | APScheduler | Lightest fit for a 5-min cron + daily check; no Celery/Redis needed |
| Schwab client | schwab-py + httpx | schwab-py for OAuth; raw httpx for Greeks from `/chains` |
| Greeks fallback | scipy + numpy (custom ~100 lines) | No third-party BS lib; full control; py_vollib is dormant |
| Alerts | aiosmtplib | Async SMTP; retry logic built in |
| Tests | pytest + pytest-asyncio | Integration tests hit real SQLite; no mocks |

---

## Quickstart

Full setup instructions are in [`.speckit/quickstart.md`](.speckit/quickstart.md).

Short version:

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env   # fill in Schwab credentials + SMTP

# 3. Initialise DB
alembic upgrade head

# 4. Authenticate with Schwab (one-time, then every 7 days)
python -m src.auth.schwab_oauth

# 5. Run
uvicorn src.api.main:app --reload
# → open http://localhost:8000
```

---

## Project governance

This project has a ratified [constitution](.specify/memory/constitution.md) (v1.1.0) that governs every implementation decision. The six principles:

| # | Principle | Non-negotiable |
|---|---|---|
| I | **Local-First Privacy** | All data on your machine; only Schwab API receives outbound traffic |
| II | **Spec-Before-Code** | Spec commits precede app commits — always |
| III | **Test-First** | Tests written and failing before implementation begins |
| IV | **Alert Reliability** | Every alert delivers or logs a retry; idempotent by design |
| V | **Simplicity Boundary** | Single user, single account; no scope creep |
| VI | **Visual & Responsive UI** | Visual-first dashboard; fully functional on mobile viewports |

---

## How this is being built: Claude Pro + Speckit

Option Sentinel is being developed entirely through a spec-driven workflow using
**[Speckit](https://github.com/github/spec-kit)** and **Claude Pro**. The approach
replaces ad-hoc vibe-coding with a structured sequence:

```
specify  →  clarify  →  plan  →  tasks  →  implement
```

Each step is a slash command. Claude drives the work; the spec is the source of truth.

### The workflow in practice

| Step | Command | What happens |
|---|---|---|
| 1 | `/speckit-specify` | Write or update the feature spec from a description |
| 2 | `/speckit-clarify` | Claude asks ≤5 targeted questions; answers encoded into spec |
| 3 | `/speckit-plan` | Architecture, data model, contracts, quickstart generated |
| 4 | `/speckit-tasks` | 59 ordered tasks with file paths, test-first enforced |
| 5 | `/speckit-implement` | Claude executes tasks sequentially, committing as it goes |

All planning artifacts live in [`.speckit/`](.speckit/):

```
.speckit/
├── spec.md          ← source of truth for requirements
├── plan.md          ← stack, structure, constitution check
├── research.md      ← technology decisions + rationale
├── data-model.md    ← all 8 entities with fields + constraints
├── contracts/
│   └── http.md      ← 11 FastAPI endpoint contracts
├── quickstart.md    ← setup guide
└── tasks.md         ← 59 implementation tasks
```

### Spec-before-code: why commit order matters

One of the constitution's governing rules is that **spec changes are committed before
app changes** in every session. This means the git history tells a coherent story:

```
spec: add credit spread profit target rule
feat: implement profit target alert engine
spec: add thesis group model
feat: implement thesis CRUD + assignment routes
```

This makes the Gource visualisation meaningful — you can watch the spec evolve and
the app materalise in response.

---

## Reducing token churn with Codesight

As the codebase grows, starting a new Claude session without context is expensive —
the agent has to re-read files it has already understood. **Codesight** solves this
by generating a compressed `.codesight/KNOWLEDGE.md` snapshot of the codebase that
Claude reads at the start of every session instead of crawling the tree.

Setup (once codesight is configured):

```bash
# Regenerate after significant changes
codesight generate
```

Then in `.claude/settings.json` or `CLAUDE.md`:

```
Always read .codesight/KNOWLEDGE.md before starting any task if it exists.
```

The result: Claude starts each session with accurate codebase context in a fraction
of the tokens, and you spend your Pro quota on implementation rather than orientation.

---

## Current status

| Phase | Status |
|---|---|
| Constitution ratified (v1.1.0) | ✅ Done |
| Spec written + clarified | ✅ Done |
| Plan + research + data model | ✅ Done |
| 59 tasks generated | ✅ Done |
| Implementation | ⬜ Ready to start (`/speckit-implement`) |

**MVP target**: User Story 1 (tasks T001–T026) — live dashboard with Schwab positions
and Greeks. Everything else builds on that foundation.

---

## Feature roadmap

The spec covers five user stories in priority order:

1. **P1 — Live Position Dashboard** — positions, mark price, P&L, DTE, Greeks
2. **P2 — Credit Spread Profit Target Alert** — email when spread hits 50% profit
3. **P2 — Expiry Warning Escalation** — email at 14, 7, and 3 DTE
4. **P2 — Binary Event Exit Protocol** — one-button full-portfolio exit alert
5. **P3 — Thesis Groups & Position Scoring** — group by thesis, exit proximity score

SMS alerts via Twilio are a stretch goal after the core is stable.

---

## Licence

MIT
