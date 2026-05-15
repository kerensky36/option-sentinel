# Option Sentinel

> A personal options position monitor built with Claude Pro, spec-driven from day one.

![Status](https://img.shields.io/badge/status-complete-brightgreen)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20Vanilla%20JS%20%2B%20sessionStorage-informational)
![Auth](https://img.shields.io/badge/brokerage-Charles%20Schwab-4a7c59)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What it does

Option Sentinel connects to your Charles Schwab account and gives you a **live, visual dashboard** of every open options position — with Greeks, P&L, and the tools to make informed management decisions without hunting through the brokerage UI.

| Capability | Detail |
|---|---|
| **Live positions** | On-demand refresh from Schwab — one button, immediate update |
| **Greeks** | Delta, gamma, theta, vega, IV — sourced from Schwab API, Black-Scholes fallback |
| **Thesis groups** | Group positions by named thesis — stored in your browser only |
| **Covered call screener** | Ranks long stock positions by covered-call income opportunity |
| **Mobile-ready** | Visual-first responsive dashboard — readable on your phone mid-session |
| **Erase All** | One button wipes every piece of your data from the browser instantly |

<img width="1284" height="535" alt="image" src="https://github.com/user-attachments/assets/2bcfa959-d30a-4996-aa1b-130d7a3069a9" />
<img width="1456" height="695" alt="image" src="https://github.com/user-attachments/assets/e2408fd7-4df0-4bc4-9a87-9c8e9be83f40" />

---

## Privacy & Data Handling

This section explains exactly where your data lives, how it flows, and how to erase it. No hand-waving.

### The core guarantee

> **Your Schwab token and position data never reside on the server.** The server forwards your token to Schwab and returns raw data. It stores nothing. Logs nothing sensitive.

### Login flow — step by step

```
1. You click "Connect Schwab Account"
   └─ You are redirected to Schwab's own login page (api.schwabapi.com)
      Option Sentinel never sees your Schwab username or password.

2. You log in and approve the app at Schwab
   └─ Schwab redirects you back to Option Sentinel with a one-time auth code.

3. Option Sentinel exchanges that code for a token
   └─ This step requires your App Secret and must happen server-side.
      The token is returned to your browser via an inline <script> tag
      in the callback page response.
      The server discards the token immediately after sending the response.
      The token is never written to a database, file, or log.

4. Your browser stores the token in sessionStorage
   └─ sessionStorage is tab-local — it is automatically cleared when
      you close the tab or browser. It cannot be accessed by any
      other website or browser tab.

5. Every Refresh request sends the token as an Authorization header
   └─ The server reads the header, forwards it to Schwab, returns
      the raw JSON response. It does not log the Authorization header
      value. It does not store it. It is only in memory for the
      milliseconds of that request.

6. Your browser caches position data in sessionStorage
   └─ sessionStorage is tab-local — it is automatically cleared when
      you close the tab or browser. Position data is available for
      the duration of the tab session without additional network
      requests until you click Refresh again.
```

### Where each piece of data lives

| Data | Location | Cleared when |
|---|---|---|
| Schwab token | Browser `sessionStorage` | Tab/browser closed, Logout, or Erase All |
| Cached positions | Browser `sessionStorage` | Tab/browser closed, or Erase All |
| Screener cache | Browser `sessionStorage` | Tab/browser closed, or Erase All |
| Thesis groups & assignments | Browser `localStorage` | Erase All, or manual browser data clear |
| **Server storage** | **None** | **N/A — nothing is stored server-side** |

### What Cloud Run sees

Cloud Run (the server) sees:
- The URL path of each request (e.g., `/api/positions/refresh`)
- The `Authorization: Bearer` header — **value forwarded to Schwab, not logged**
- Standard HTTP metadata (timestamps, response codes)

Cloud Run never sees or stores:
- Your Schwab credentials
- Your position data at rest
- Your thesis groups, spreads, or exit goals
- Any data from a previous session

### Erase All Data

The **"Erase All Data"** button is available in the navigation on every page. Clicking it (after a confirmation prompt) runs the following in your browser:

```javascript
sessionStorage.clear()              // removes Schwab token, cached positions, screener cache
localStorage.clear()                // removes thesis groups and assignments
window.location.replace('/auth/login')       // returns to login screen
```

The server receives no request during this operation. After erasing, the app is in exactly the same state as a fresh install.

### Two-browser / two-device behaviour

Because all data is browser-local, your data on one device is not available on another. If you log in on your phone, your desktop session is unaffected (and vice versa). This is a privacy feature, not a limitation — nothing syncs through any server.

---

## Architecture

```
Browser                          Cloud Run (stateless)          Schwab API
  │                                      │                           │
  │  [you click Refresh]                 │                           │
  │  fetch('/api/positions/refresh')     │                           │
  │  Authorization: Bearer <token>      │                           │
  ├─────────────────────────────────────►│                           │
  │                                      ├── GET /accounts (token) ─►│
  │                                      │◄─ positions JSON ─────────┤
  │◄─ positions JSON ────────────────────┤   (token never stored)    │
  │                                      │                           │
  │  sessionStorage.setItem(positions)   │                           │
  │  render table from JSON              │                           │
  │  apply thesis labels from            │                           │
  │  localStorage                        │                           │
```

The server is a thin, stateless forwarder. It holds no data between requests.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async, clean, minimal cold start |
| Frontend | Vanilla JS ES modules | No build pipeline; no framework cold-start cost |
| Client storage | sessionStorage + localStorage | Token and position/screener caches (sessionStorage, tab-scoped); thesis groups (localStorage, persists across tabs) |
| Schwab client | schwab-py + httpx | schwab-py for OAuth exchange; forwarded as Bearer on each request |
| Greeks fallback | scipy + numpy | Black-Scholes; no third-party BS library needed |
| Deployment | GCP Cloud Run | Scale-to-zero; min-instances=0; max-instances=1 |
| Tests | pytest + pytest-asyncio | Fast, no DB fixtures needed |

---

## Quickstart

Full setup instructions: [`specs/004-stateless-ephemeral-refactor/quickstart.md`](specs/004-stateless-ephemeral-refactor/quickstart.md)

Short version:

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env   # fill in Schwab credentials

# 3. Run (no DB setup needed)
uvicorn src.api.main:app --reload
# → open http://localhost:8000
# → click "Connect Schwab Account"
```

---

## Project governance

This project has a ratified [constitution](.specify/memory/constitution.md) (v2.0.0) that governs every implementation decision.

| # | Principle | Non-negotiable |
|---|---|---|
| I | **Privacy-First Data Handling** | Token and position data never persisted server-side; token only in browser sessionStorage |
| II | **Spec-Before-Code** | Spec commits precede app commits — always |
| III | **Test-First** | Tests written and failing before implementation begins |
| IV | **Simplicity Boundary** | Single user, single account; no scope creep |
| V | **Visual & Responsive UI** | Visual-first dashboard; fully functional on mobile viewports |

---

## How this is being built: Claude Pro + Speckit

Option Sentinel is developed through a spec-driven workflow using
**[Speckit](https://github.com/github/spec-kit)** and **Claude Pro**:

```
specify  →  clarify  →  plan  →  tasks  →  implement
```

Planning artifacts live in [`specs/004-stateless-ephemeral-refactor/`](specs/004-stateless-ephemeral-refactor/):

```
specs/004-stateless-ephemeral-refactor/
├── spec.md          ← source of truth for requirements
├── plan.md          ← stack, structure, constitution check
├── research.md      ← technology decisions + rationale
├── data-model.md    ← entities, token flow diagram
├── contracts/
│   └── http.md      ← API endpoint contracts
├── quickstart.md    ← setup guide
└── tasks.md         ← 58 implementation tasks (45 + 13 Phase 10)
```

---

## Current status

| Phase | Status |
|---|---|
| Constitution ratified (v2.0.0) | ✅ Done |
| Stateless architecture spec | ✅ Done |
| Plan + research + data model | ✅ Done |
| 45 tasks generated | ✅ Done |
| Phase 1 — Teardown (delete DB/scheduler/alerts) | ✅ Done |
| Phase 2 — Foundational (Pydantic models, deps, OAuth) | ✅ Done |
| Phase 3 — OAuth login (sessionStorage token delivery) | ✅ Done |
| Phase 4 — Positions dashboard (Refresh button, sessionStorage cache) | ✅ Done |
| Phase 5 — Erase All Data | ✅ Done |
| Phase 6 — Thesis groups (localStorage) | ✅ Done |
| Phase 7 — Covered call screener (stateless) | ✅ Done |
| Phase 8 — Dockerfile + Cloud Run | ✅ Done |
| Phase 9 — Test cleanup + documentation | ✅ Done |
| Phase 10 — Multi-user OAuth (stateless PKCE, dynamic accounts) | ✅ Done |

**All 45/45 tasks complete. Phase 10 (multi-user OAuth) also complete.** App is deployed and stateless.

---

## Deployment (Cloud Run + Firebase Hosting)

Backend runs on GCP Cloud Run (stateless, scale-to-zero). Frontend is served from Firebase Hosting CDN, with `/api/**` and `/auth/**` proxied to Cloud Run.

**Required env vars**: `GCP_PROJECT_ID`, `SCHWAB_CLIENT_ID`, `SCHWAB_CLIENT_SECRET`, `SCHWAB_REDIRECT_URI`, `SCHWAB_AUTH_URL`, `SCHWAB_TOKEN_URL`

```bash
# One-command deploy (backend + frontend)
export GCP_PROJECT_ID=your-project-id
export SCHWAB_CLIENT_ID=...
export SCHWAB_CLIENT_SECRET=...
export SCHWAB_REDIRECT_URI=https://your-project.web.app/auth/callback
export SCHWAB_AUTH_URL=https://api.schwabapi.com/v1/oauth/authorize
export SCHWAB_TOKEN_URL=https://api.schwabapi.com/v1/oauth/token

bash scripts/deploy.sh
```

Or deploy individually:
```bash
bash scripts/deploy_backend.sh    # Cloud Run only
bash scripts/deploy_frontend.sh   # Firebase Hosting only
```

Full setup instructions: [`specs/005-cloudrun-firebase-deploy/quickstart.md`](specs/005-cloudrun-firebase-deploy/quickstart.md)

No database, no volume mounts, no Redis. Cold start target: under 3 seconds. `max-instances=1` required (PKCE state is in-memory).

---

## Reducing token churn with Codesight

As the codebase grows, **Codesight** generates a compressed `.codesight/KNOWLEDGE.md` snapshot that Claude reads at the start of every session instead of crawling the tree.

```bash
codesight generate   # regenerate after significant changes
```

---

## Licence

MIT
