# Research: GCP Cloud Run + Firebase Hosting Deployment

**Feature**: 005-cloudrun-firebase-deploy
**Date**: 2026-05-13

---

## Decision 1: Frontend Serving Model

**Decision**: Pre-render Jinja2 templates to static HTML files at deploy time; serve from Firebase Hosting CDN. Only `/api/**` and `/auth/**` routes are proxied to Cloud Run.

**Rationale**:
- Page loads served from CDN edge (no cold-start impact for HTML pages)
- Cheaper Cloud Run usage — only API/auth requests hit the container
- The existing templates contain no per-request dynamic data: `dashboard.html` and `screener.html` only use `current_page` (a static string) for nav highlighting; all position/screener data is loaded by client-side JS
- `login.html` uses `dev_login_available` (server-only flag) → served by Cloud Run via proxy; does NOT need pre-rendering

**Alternatives considered**:
- Full Cloud Run proxy (Firebase as passthrough only): Simpler, no build step, but every page load hits Cloud Run and incurs cold-start latency when idle
- Separate Cloud Run URL for API / Firebase URL for frontend: Requires CORS config and breaks the Schwab OAuth callback domain assumptions

**Pre-render scope**:
| Template | Pre-rendered? | Context needed | Output path |
|----------|--------------|---------------|-------------|
| `dashboard.html` | ✅ Yes | `current_page="thesis_monitor"` | `dist/index.html` |
| `screener.html` | ✅ Yes | `current_page="covered_call_screener"`, `setup_required=False` | `dist/screener/index.html` |
| `login.html` | ❌ No — proxied | `dev_login_available` (dynamic) | Cloud Run `/auth/login` |

**Note**: `screener.html` uses `setup_required` which was a leftover from before T051 removed the `SCHWAB_CC_ACCOUNT_ID` env var requirement. The screener route must be updated to remove this check before pre-rendering. In production, `setup_required` is always `False` (dynamic account resolution).

---

## Decision 2: Firebase Hosting Proxy to Cloud Run

**Decision**: Use Firebase Hosting native Cloud Run rewrites (`"run": { "serviceId": "...", "region": "..." }`) to proxy `/api/**` and `/auth/**`.

**Rationale**:
- Native first-party integration — no Cloud Functions or other intermediary required
- Firebase handles SSL termination; proxied requests reach Cloud Run on the same GCP network
- Single domain for the user — no CORS needed for proxied routes
- The PKCE OAuth callback (`/auth/callback`) receives the correct redirect URI since it appears to come from the Firebase domain

**Cookie forwarding**: Firebase Hosting strips all cookies at the proxy boundary **except** cookies named `__session`. This app uses **no server-side session cookies** — the Schwab token lives in `sessionStorage` and the PKCE state is in-memory. Cookie stripping is therefore a non-issue.

**Headers**: Firebase injects `X-Forwarded-For` and `X-Forwarded-Host` headers. The app does not read these, so no impact.

**Alternatives considered**:
- Cloud Functions proxy: More flexible but adds a function cold-start and billing tier
- `firebase.json` using `functions` rewrite: Deprecated in favour of `run` rewrite for Cloud Run services

---

## Decision 3: Build Process for Static Assets

**Decision**: Single Python script (`scripts/build_frontend.py`) that uses Jinja2 directly to pre-render templates and copies static assets to `dist/`.

**Rationale**:
- No new tool dependencies — Python and Jinja2 are already in `requirements.txt`
- Runs in the same virtualenv used for the app
- Simple, auditable, < 50 lines

**Key implementation note**: `jinja2.Environment(loader=FileSystemLoader("frontend/templates"))` must be rooted at the directory containing `base.html`. Child templates that `{% extends "base.html" %}` are resolved relative to this loader root.

**Output layout**:
```
dist/
├── index.html              # pre-rendered dashboard.html
├── screener/
│   └── index.html          # pre-rendered screener.html (clean URL: /screener)
└── static/                 # copied verbatim from frontend/static/
    ├── js/
    └── css/
```

**Alternatives considered**:
- Webpack/Vite: Heavy, introduces a Node.js toolchain for a vanilla-JS project
- Manual copy: Error-prone, not reproducible

---

## Decision 4: Deploy Script Language

**Decision**: Shell scripts (`scripts/deploy_backend.sh`, `scripts/deploy_frontend.sh`, `scripts/deploy.sh`).

**Rationale**:
- gcloud and firebase-cli are shell-native tools; wrapping them in Python adds no value
- Shell scripts are trivially composable and readable for deploy pipelines
- No dependencies beyond gcloud CLI and firebase-cli being installed

**Alternatives considered**:
- Python subprocess: Same result, more code
- Makefile: Reasonable alternative, but shell scripts are more portable and visible

---

## Decision 5: Container Build Strategy

**Decision**: `gcloud run deploy --source .` — Cloud Build builds the Dockerfile and deploys in one step.

**Rationale**:
- No local Docker daemon required (Cloud Build runs remotely)
- Simpler deploy script (one command vs. build + push + deploy)
- Dockerfile already validated from the 004 implementation (T037)

**Alternatives considered**:
- Local `docker build` + push to Artifact Registry: More control but requires local Docker daemon and an Artifact Registry setup step
- Cloud Build trigger (CI/CD): Out of scope; manual deploys are sufficient for a single-user project

---

## Decision 6: Secret / Environment Variable Management

**Decision**: Schwab credentials passed via `--set-env-vars` in the deploy script; operator provides values as shell environment variables before running the script.

**Rationale**:
- Simplest approach for a single-operator project
- No GCP Secret Manager setup required
- Values are never stored in the repository (only passed at deploy time)

**Alternatives considered**:
- GCP Secret Manager + `--set-secrets`: More secure, appropriate for teams, but adds setup complexity for a single user
- `.env` file baked into the image: Disallowed by the constitution (no credential leakage)

---

## Screener Route Bug (must fix in this feature)

`src/api/routes/screener.py` still sets `setup_required = not bool(os.environ.get("SCHWAB_CC_ACCOUNT_ID"))`. Since T051 removed the `SCHWAB_CC_ACCOUNT_ID` dependency from the screener service, this env var will not be set in production and the screener page will always show "Setup Required".

**Fix**: Remove the `setup_required` logic from the screener route. Pass `setup_required=False` explicitly, or remove the conditional from the template.
