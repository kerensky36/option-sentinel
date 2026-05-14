# Tasks: GCP Cloud Run + Firebase Hosting Deployment

**Input**: Design documents from `specs/005-cloudrun-firebase-deploy/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/deploy.md ✅ quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to
- Exact file paths are required in every task description

---

## Phase 1: Setup

**Purpose**: Repository housekeeping before any implementation.

- [x] T001 Add `dist/` entry to `.gitignore` (generated build artefact — must never be committed)

---

## Phase 2: Foundational — Remove Dead Code (Blocking Prerequisite)

**Purpose**: Remove the `setup_required` guard leftover from before T051 removed `SCHWAB_CC_ACCOUNT_ID`. Without this fix, `screener.html` cannot be correctly pre-rendered (would always render the "Setup Required" block instead of the screener UI).

**⚠️ CRITICAL**: T005 (build script) depends on these changes being complete. No static rendering task can run until this phase is done.

- [x] T002 Fix `src/api/routes/screener.py`: delete line 19 (`setup_required = not bool(os.environ.get("SCHWAB_CC_ACCOUNT_ID"))`) and delete line 25 (`"setup_required": setup_required,`) from the `TemplateResponse` context dict
- [x] T003 [P] Fix `frontend/templates/screener.html`: delete lines 6–18 (the entire `{% if setup_required %}...{% else %}` block including the "Setup Required" UI and the `{% else %}` marker) and delete line 98 (`{% endif %}`); the screener Refresh UI that was inside `{% else %}` becomes the direct content of `{% block content %}`
- [x] T004 Run `pytest tests/` and confirm all 38 tests still pass after T002/T003; fix any regressions before proceeding

**Checkpoint**: `pytest tests/` passes. `/screener` route renders the screener UI directly (no "Setup Required" message). No `SCHWAB_CC_ACCOUNT_ID` references remain in `screener.py` or `screener.html`.

---

## Phase 3: User Story 1 — Deploy Backend to Cloud Run (Priority: P1) 🎯 MVP

**Goal**: Single script deploys the FastAPI backend to Cloud Run in us-central1 with correct constraints and env vars.

**Independent Test**: Export required env vars, run `bash scripts/deploy_backend.sh`. The script exits 0 and prints the Cloud Run HTTPS URL. `curl https://<url>/health` returns `{"status":"ok"}` within 3 seconds of a cold start.

### Implementation

- [x] T005 [US1] Create `scripts/deploy_backend.sh`:
  - Validate required env vars (`GCP_PROJECT_ID`, `SCHWAB_CLIENT_ID`, `SCHWAB_CLIENT_SECRET`, `SCHWAB_REDIRECT_URI`, `SCHWAB_AUTH_URL`, `SCHWAB_TOKEN_URL`); `echo "ERROR: missing $VAR"` and `exit 1` for each missing var
  - Run: `gcloud run deploy "${CLOUD_RUN_SERVICE:-option-sentinel}" --source . --region "${CLOUD_RUN_REGION:-us-central1}" --platform managed --min-instances 0 --max-instances 1 --allow-unauthenticated --project "$GCP_PROJECT_ID" --set-env-vars "SCHWAB_CLIENT_ID=$SCHWAB_CLIENT_ID,SCHWAB_CLIENT_SECRET=$SCHWAB_CLIENT_SECRET,SCHWAB_REDIRECT_URI=$SCHWAB_REDIRECT_URI,SCHWAB_AUTH_URL=$SCHWAB_AUTH_URL,SCHWAB_TOKEN_URL=$SCHWAB_TOKEN_URL,RISK_FREE_RATE=${RISK_FREE_RATE:-0.045}"`
  - After deploy, capture the service URL using `gcloud run services describe "${CLOUD_RUN_SERVICE:-option-sentinel}" --region "${CLOUD_RUN_REGION:-us-central1}" --project "$GCP_PROJECT_ID" --format "value(status.url)"` and print `✓ Backend deployed: <URL>`
  - Make executable: `chmod +x scripts/deploy_backend.sh`

**Checkpoint**: Running `bash scripts/deploy_backend.sh` with env vars set deploys Cloud Run and prints the service URL. Missing-var errors print clearly with the variable name.

---

## Phase 4: User Story 2 — Serve Frontend via Firebase Hosting (Priority: P1)

**Goal**: Static HTML pages and JS/CSS served from Firebase CDN. `/api/**` and `/auth/**` requests proxied to Cloud Run.

**Independent Test**: Run `python scripts/build_frontend.py` — `dist/index.html` and `dist/screener/index.html` are created with rendered HTML. Then run `bash scripts/deploy_frontend.sh` with `GCP_PROJECT_ID` set — Firebase deploys and prints the `.web.app` URL. Navigate directly to `https://<site>.web.app/screener` — page loads (not 404).

### Implementation

- [x] T006 [P] [US2] Create `scripts/build_frontend.py`:
  - Import `jinja2`, `shutil`, `pathlib.Path`
  - Clean and recreate `dist/` at project root (`shutil.rmtree("dist", ignore_errors=True)`, `Path("dist").mkdir()`)
  - Copy `frontend/static/` → `dist/static/` using `shutil.copytree("frontend/static", "dist/static")`
  - Create Jinja2 env: `Environment(loader=FileSystemLoader("frontend/templates"))` — loader MUST be rooted at `frontend/templates` (where `base.html` lives) so `{% extends "base.html" %}` resolves correctly
  - Render `dashboard.html` with `{"current_page": "thesis_monitor"}` → write to `dist/index.html`
  - Create dir + render `screener.html` with `{"current_page": "covered_call_screener", "setup_required": False}` → write to `dist/screener/index.html`
  - Print each output path on success: `✓ dist/index.html`, `✓ dist/screener/index.html`

- [x] T007 [P] [US2] Create `firebase.json` at project root:
  ```json
  {
    "hosting": {
      "public": "dist",
      "cleanUrls": true,
      "trailingSlash": false,
      "headers": [
        {
          "source": "/static/**",
          "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }]
        }
      ],
      "rewrites": [
        { "source": "/api/**",  "run": { "serviceId": "option-sentinel", "region": "us-central1" } },
        { "source": "/auth/**", "run": { "serviceId": "option-sentinel", "region": "us-central1" } },
        { "source": "**", "destination": "/index.html" }
      ]
    }
  }
  ```
  Note: `serviceId` defaults to `option-sentinel`; update if `CLOUD_RUN_SERVICE` is customised.

- [x] T008 [P] [US2] Create `.firebaserc` at project root as an operator reference template:
  ```json
  {
    "projects": {
      "default": "REPLACE_WITH_YOUR_GCP_PROJECT_ID"
    }
  }
  ```
  This file is for reference; `scripts/deploy_frontend.sh` uses `--project $GCP_PROJECT_ID` and does not depend on this file being set correctly.

- [x] T009 [US2] Create `scripts/deploy_frontend.sh`:
  - Validate `GCP_PROJECT_ID` is set; exit 1 with clear message if missing
  - Run `python scripts/build_frontend.py`; exit 1 if build fails
  - Run `firebase deploy --only hosting --project "$GCP_PROJECT_ID"`
  - After deploy, print `✓ Frontend deployed: https://$GCP_PROJECT_ID.web.app`
  - Make executable: `chmod +x scripts/deploy_frontend.sh`

**Checkpoint**: `python scripts/build_frontend.py` produces `dist/index.html`, `dist/screener/index.html`, and `dist/static/`. After `bash scripts/deploy_frontend.sh`, the Firebase URL is printed and `/screener` loads without 404. `/api/**` and `/auth/**` proxy to Cloud Run.

---

## Phase 5: User Story 4 — One-Command Full Deployment (Priority: P2)

**Goal**: Single script deploys backend then frontend in the correct order, surfacing both URLs.

**Independent Test**: Run `bash scripts/deploy.sh` with all env vars set. Both services deploy without intervention. Output shows Cloud Run URL and Firebase Hosting URL. If backend fails, frontend deploy does not run.

### Implementation

- [x] T010 [US4] Create `scripts/deploy.sh`:
  - `set -e` at top (fail fast on any error)
  - Print `→ Deploying backend to Cloud Run…`
  - Call `bash scripts/deploy_backend.sh`; capture Cloud Run URL: `CLOUD_RUN_URL=$(gcloud run services describe "${CLOUD_RUN_SERVICE:-option-sentinel}" --region "${CLOUD_RUN_REGION:-us-central1}" --project "$GCP_PROJECT_ID" --format "value(status.url)")`
  - Print `→ Deploying frontend to Firebase Hosting…`
  - Call `bash scripts/deploy_frontend.sh`
  - Print final summary: `✓ Done.\n  Backend:  $CLOUD_RUN_URL\n  Frontend: https://$GCP_PROJECT_ID.web.app`
  - Print reminder: `⚠  Update SCHWAB_REDIRECT_URI to: https://$GCP_PROJECT_ID.web.app/auth/callback`
  - Make executable: `chmod +x scripts/deploy.sh`

**Checkpoint**: `bash scripts/deploy.sh` deploys both services, prints both URLs, and reminds the operator to update `SCHWAB_REDIRECT_URI`.

---

## Phase 6: Polish

- [x] T011 [P] Update `README.md` Cloud Run Deployment section: replace the existing code block (raw gcloud commands with old env var names) with a reference to `bash scripts/deploy.sh`; list required env vars (`GCP_PROJECT_ID`, `SCHWAB_CLIENT_ID`, `SCHWAB_CLIENT_SECRET`, `SCHWAB_REDIRECT_URI`, `SCHWAB_AUTH_URL`, `SCHWAB_TOKEN_URL`); keep the note about `max-instances=1`
- [x] T012 [P] Run `pytest tests/` one final time to confirm clean pass after all changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — run immediately
- **Phase 2 (Foundational)**: Must follow Phase 1; T002 and T003 are parallel; T004 follows T002+T003
- **Phase 3 (US1 Backend)**: Can start after Phase 1 (independent of Phase 2 bug fix — different files)
- **Phase 4 (US2 Frontend)**: T006/T007/T008 parallel after Phase 1; T009 follows T006; all require Phase 2 complete (correct screener.html for pre-rendering)
- **Phase 5 (US4 Combined)**: Must follow Phase 3 (T005) and Phase 4 (T009)
- **Phase 6 (Polish)**: Follows all implementation phases

### Parallel Opportunities

```text
Phase 2: T002 ‖ T003 (different files)
Phase 3+4: T005 (backend script) can run in parallel with T006/T007/T008 (frontend artifacts)
Phase 4: T006 ‖ T007 ‖ T008 (different files)
Phase 6: T011 ‖ T012
```

---

## Implementation Strategy

### MVP (US1 = deployable backend)

1. Complete Phase 1 (Setup)
2. Complete Phase 2 (Bug Fix)
3. Complete Phase 3 (US1 — backend deploy script)
4. **STOP and VALIDATE**: `bash scripts/deploy_backend.sh` deploys successfully; `curl /health` responds
5. Backend is live and testable at this point

### Incremental Delivery

- Phase 4 (US2 + US3): Adds frontend hosting and API proxy — full app accessible at Firebase URL
- Phase 5 (US4): Adds convenience combined deploy script
- Phase 6: Clean up README, final test pass

### Total Tasks

| Phase | Tasks | Parallel? |
|-------|-------|-----------|
| Phase 1 (Setup) | 1 | — |
| Phase 2 (Bug Fix) | 3 | T002 ‖ T003 |
| Phase 3 (US1 Backend) | 1 | — |
| Phase 4 (US2 Frontend) | 4 | T006 ‖ T007 ‖ T008 |
| Phase 5 (US4 Combined) | 1 | — |
| Phase 6 (Polish) | 2 | T011 ‖ T012 |
| **Total** | **12** | |
