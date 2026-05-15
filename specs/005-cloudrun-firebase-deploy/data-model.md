# Data Model: GCP Cloud Run + Firebase Hosting Deployment

**Feature**: 005-cloudrun-firebase-deploy
**Date**: 2026-05-13

---

## Overview

This feature introduces no new runtime data entities. All runtime data handling is unchanged from the 004 stateless refactor (token in `sessionStorage`, positions in `IndexedDB`, thesis in `localStorage`).

This document describes the **configuration entities** — the structured sets of values that operators supply and scripts consume — and the **build artefacts** produced by the frontend build step.

---

## Entity 1: Deploy Configuration

The set of environment variables required to run deploy scripts and the Cloud Run container. Split into two scopes.

### Cloud Run Container Variables (required at runtime)

| Variable | Required | Description |
|----------|----------|-------------|
| `SCHWAB_CLIENT_ID` | ✅ | Schwab developer app key |
| `SCHWAB_CLIENT_SECRET` | ✅ | Schwab developer app secret |
| `SCHWAB_REDIRECT_URI` | ✅ | OAuth callback URL (must match Schwab app config) |
| `SCHWAB_AUTH_URL` | ✅ | Schwab OAuth authorise endpoint |
| `SCHWAB_TOKEN_URL` | ✅ | Schwab token exchange endpoint |
| `RISK_FREE_RATE` | optional | Black-Scholes rate; defaults to `0.045` |

**Validation rule**: App fails fast at startup if any required variable is absent (enforced by `src/api/main.py` startup check, from T048).

### Deploy Script Variables (required at deploy time, not in container)

| Variable | Required | Description |
|----------|----------|-------------|
| `GCP_PROJECT_ID` | ✅ | GCP project to deploy Cloud Run and Firebase to |
| `CLOUD_RUN_SERVICE` | optional | Cloud Run service name; defaults to `option-sentinel` |
| `CLOUD_RUN_REGION` | optional | Cloud Run region; defaults to `us-central1` |
| `FIREBASE_PROJECT` | optional | Firebase project ID; defaults to `GCP_PROJECT_ID` |

---

## Entity 2: Firebase Hosting Configuration (`firebase.json`)

Describes the hosting site's public directory, rewrite rules, and CDN behaviour.

| Field | Value | Description |
|-------|-------|-------------|
| `public` | `dist` | Root directory of pre-built static files |
| `cleanUrls` | `true` | Strips `.html` extensions; `screener/index.html` served at `/screener` |
| `trailingSlash` | `false` | No trailing slash on URLs |
| `rewrites[].source` | `/api/**` | Proxy all API calls to Cloud Run |
| `rewrites[].source` | `/auth/**` | Proxy all auth routes to Cloud Run |
| `rewrites[].destination` | `/index.html` | SPA fallback — all other routes serve dashboard shell |
| `headers[].source` | `/static/**` | Long-lived cache for static assets (`Cache-Control: max-age=31536000`) |

**State transitions**: Firebase configuration is static; it is deployed once and updated only when route structure or Cloud Run service details change.

---

## Entity 3: Frontend Build Artefact (`dist/`)

The output directory produced by `scripts/build_frontend.py`, consumed by the Firebase Hosting deploy step.

```
dist/
├── index.html              # pre-rendered dashboard.html (current_page="thesis_monitor")
├── screener/
│   └── index.html          # pre-rendered screener.html (current_page="covered_call_screener")
└── static/                 # verbatim copy of frontend/static/
    ├── js/
    │   ├── auth.js
    │   ├── positions_ui.js
    │   ├── position_cache.js
    │   ├── screener_ui.js
    │   ├── thesis_store.js
    │   └── thesis_ui.js
    └── css/
```

**Lifecycle**: `dist/` is generated at deploy time and is gitignored. It must not be committed to source control.

**Inputs to build**:
- `frontend/templates/base.html` — shared layout
- `frontend/templates/dashboard.html` — dashboard shell
- `frontend/templates/screener.html` — screener shell (rendered with `setup_required=False`)
- `frontend/static/**` — copied verbatim

---

## Entity 4: Firebase Project Configuration (`.firebaserc`)

Maps the local project to the Firebase project ID.

```json
{
  "projects": {
    "default": "<GCP_PROJECT_ID>"
  }
}
```

Generated once during project setup (`firebase use --add` or manually). Committed to source control (contains no secrets).

---

## Relationships

```
Deploy Configuration
    │
    ├── Cloud Run Container Variables ─────► Cloud Run Service (runtime)
    │
    └── Deploy Script Variables ────────────► gcloud run deploy (build-time)
                                         └──► firebase deploy (build-time)

Firebase Hosting Configuration (firebase.json)
    │
    ├── /api/**  ────────────────────────────► Cloud Run Service (proxy)
    ├── /auth/** ────────────────────────────► Cloud Run Service (proxy)
    └── /**      ────────────────────────────► dist/index.html (SPA fallback)

Frontend Build Artefact (dist/)
    │
    └── Produced by: scripts/build_frontend.py
    └── Consumed by: firebase deploy --only hosting
```
