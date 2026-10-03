# Feature Specification: AI Cost Guard & Deployment Hardening

**Feature Branch**: `022-ai-cost-guard-hardening`
**Created**: 2026-10-03
**Status**: Draft
**Input**: Security scan (2026-10-03) of data security, the GCP build, and AI cost exposure. User decision: a **global** daily cap on AI analyses (no per-user state, consistent with constitution Principle I); AI stays available outside market hours.

## Context

Any Schwab customer can sign in to the public app and call `POST /api/quorum/vote` (six Vertex AI calls including one Google Search-grounded call) and `POST /api/quorum/summary` (one call). The only limit today is an in-memory 5/minute per-client-IP rate limit, which allows thousands of analyses a day. A summary token can be replayed for 15 minutes. The Cloud Run service runs as whatever service account the project defaults to (usually the Compute default account with project Editor). Secrets are plain environment variables. The dependency audit script cannot run, and one dependency has known advisories. A spec file in git shows the first 12 characters of the Schwab app key and secret.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Hard daily ceiling on AI spend (Priority: P1)

The owner sets a maximum number of AI analyses per day for the whole service. Once it is reached, nobody can start a new analysis until the next day, so the Vertex AI bill has a known upper bound no matter how many accounts call it.

**Independent Test**: Set `QUORUM_DAILY_CAP=2`. Two valid vote requests succeed; the third returns 429 with `reason: "daily_cap"` and a `Retry-After` header, and the model is not called.

**Acceptance Scenarios**:

1. **Given** fewer than `QUORUM_DAILY_CAP` analyses today, **When** a valid vote request arrives, **Then** it runs and counts one analysis.
2. **Given** the cap is reached, **When** any vote request arrives, **Then** the server returns 429 `{"detail": …, "reason": "daily_cap"}` with `Retry-After` (seconds until midnight America/New_York) and no model call is made.
3. **Given** a request that fails validation, freshness or the Schwab token check, **When** it is rejected, **Then** it does not count against the cap.
4. **Given** a new day in America/New_York, **When** the first vote request arrives, **Then** the count starts from zero.
5. **Given** `QUORUM_DAILY_CAP=0`, **When** a vote or summary request arrives, **Then** the server returns 503 `reason: "paused"` (kill switch) and makes no model call.
6. **Given** the cap is reached, **When** the advice panel shows the error, **Then** it reads "Today's AI analysis limit has been reached — it resets at midnight ET."

---

### User Story 2 — A summary costs at most one model call per vote (Priority: P1)

**Independent Test**: Post the same valid summary token twice: the first returns 200, the second returns 403 "Summary request rejected" and the summariser is called once.

**Acceptance Scenarios**:

1. **Given** a summary token already used once, **When** it is posted again within its lifetime, **Then** the server returns 403 with the same body as every other rejected token and makes no model call.
2. **Given** the used-token record, **When** a token's lifetime has passed, **Then** its record is dropped (memory stays bounded).

---

### User Story 3 — Least-privilege, secret-safe deployment (Priority: P1)

**Independent Test**: Run `scripts/deploy_backend.sh` without `CLOUD_RUN_SERVICE_ACCOUNT`: it exits with an error before deploying. With it set, the deploy command passes `--service-account`, takes `SCHWAB_CLIENT_SECRET`, `QUORUM_SEAL_KEY` and `LOG_PEPPER` from Secret Manager, and never puts their values on the command line.

**Acceptance Scenarios**:

1. **Given** no dedicated service account is configured, **When** the backend deploy runs, **Then** it stops with instructions to run `scripts/setup_gcp_security.sh`.
2. **Given** the deploy runs, **Then** `SCHWAB_CLIENT_SECRET`, `QUORUM_SEAL_KEY` and `LOG_PEPPER` are mounted with `--update-secrets` and are absent from `--update-env-vars`.
3. **Given** the one-time setup script, **When** it runs, **Then** it creates the service account, grants only `roles/aiplatform.user` and `roles/logging.logWriter` on the project plus `roles/secretmanager.secretAccessor` on the three secrets, creates the secrets (generating random values for the seal key and pepper when not supplied), and moves the running service onto them.
4. **Given** the app starts with `HTTPS_ONLY=true` (production) and `LOG_PEPPER` unset or equal to the public default, **Then** startup fails.
5. **Given** the deploy runs, **Then** `--max-instances 1` is kept (the daily cap is held in that one instance's memory).

---

### User Story 4 — Supply chain and container hygiene (Priority: P2)

**Acceptance Scenarios**:

1. **Given** `requirements.txt`, **When** `pip-audit` runs, **Then** no known vulnerabilities are reported.
2. **Given** `scripts/audit.sh`, **When** it runs, **Then** it audits `requirements.txt` (no longer fails on missing hashes).
3. **Given** a push or pull request to `main`, **Then** CI runs the test suite and `pip-audit`, and CodeQL scans both Python and JavaScript.
4. **Given** the container image, **Then** the app runs as a non-root user.
5. **Given** the repository, **Then** no file shows any part of a real Schwab app key or secret.

### Edge Cases

- Cold start or redeploy resets the in-memory count. The spend ceiling per day is therefore `QUORUM_DAILY_CAP × (restarts + 1)`; the billing budget (quickstart) is the backstop outside the app.
- A request that passes the cap check and then times out still counts: its model calls were made.
- Invalid `QUORUM_DAILY_CAP` (non-integer or negative) → the default (300) is used and a warning is logged.

## Requirements *(mandatory)*

- **FR-501**: The server MUST keep a single, service-wide count of AI analyses started in the current America/New_York day, held in memory only, with no user identifier.
- **FR-502**: `POST /api/quorum/vote` MUST check and increment the count only after body validation, freshness, Schwab token verification and context building succeed, and before any model call.
- **FR-503**: When the count has reached `QUORUM_DAILY_CAP` (default 300), the vote route MUST return 429 with `reason: "daily_cap"` and `Retry-After`, and log a `quorum_daily_cap_reached` security event.
- **FR-504**: `QUORUM_DAILY_CAP=0` MUST pause AI: vote and summary return 503 with `reason: "paused"`.
- **FR-505**: A summary token MUST be accepted at most once; replays return the existing 403 rejection. Used-token records MUST expire with the token.
- **FR-506**: The advice panel MUST show a specific message for `daily_cap` and `paused`.
- **FR-507**: The backend deploy MUST require `CLOUD_RUN_SERVICE_ACCOUNT` and pass it as `--service-account`, mount the three secrets from Secret Manager, pass `QUORUM_DAILY_CAP` through when set, and keep `--max-instances 1`.
- **FR-508**: A one-time `scripts/setup_gcp_security.sh` MUST create the least-privilege service account and the secrets and migrate the service; it MUST NOT remove roles from other accounts (it prints that step instead).
- **FR-509**: With `HTTPS_ONLY=true`, startup MUST fail if `LOG_PEPPER` is unset or is the public default.
- **FR-510**: `python-multipart` MUST be upgraded past the published advisories; `scripts/audit.sh` MUST run; CI MUST run tests, `pip-audit`, and CodeQL for Python and JavaScript.
- **FR-511**: The container MUST run as a non-root user.
- **FR-512**: The partial Schwab key/secret values in `specs/004-stateless-ephemeral-refactor/quickstart.md` MUST be replaced with placeholders. (History still holds them; the owner rotates the Schwab app secret.)
- **FR-513**: No data-use disclosure change: the cap stores no user data.

## Success Criteria

- **SC-501**: With the default cap, worst-case AI analyses per instance-day are bounded at 300 (about $12/day at ~4¢ per analysis at list prices).
- **SC-502**: Replaying a summary token never causes a second model call (automated test).
- **SC-503**: `pip-audit -r requirements.txt` reports zero known vulnerabilities.
- **SC-504**: No secret value appears in the deploy command line or in `gcloud run services describe` env vars after migration.

## Out of Scope (owner actions, documented in quickstart)

- Rotating the Schwab app secret.
- Billing budget with Pub/Sub alerts and a function that disables Vertex AI on breach; Vertex AI per-minute quota caps.
- Removing `roles/aiplatform.user` / Editor from the Compute default service account.
- Pinning the base image by digest (needs registry access from the owner's machine).
- Per-user caps (would need per-user server state — constitution Principle I).
