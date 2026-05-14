# Feature Specification: GCP Cloud Run + Firebase Hosting Deployment

**Feature Branch**: `005-cloudrun-firebase-deploy`
**Created**: 2026-05-13
**Status**: Draft
**Input**: User description: "I want to deploy this to GCP as CloudRun + Firebase hosting for the frontend. Add GCP Cloud Run + Firebase Hosting deployment: Dockerfile for stateless FastAPI backend deployed via Cloud Run, firebase.json with SPA rewrite and /api/** proxy to Cloud Run service, and deploy scripts for both frontend and backend targeting us-central1"

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Deploy Backend to Cloud Run (Priority: P1)

The operator runs a backend deploy script that packages and deploys the stateless API server to GCP Cloud Run in us-central1. After deployment, the API is accessible at a stable HTTPS URL and responds to health checks.

**Why this priority**: The backend must be live before the frontend can function. This is the minimum deployable unit.

**Independent Test**: Run the backend deploy script with GCP credentials configured. After completion, the service's health endpoint responds with an OK status within 3 seconds of a cold start.

**Acceptance Scenarios**:

1. **Given** valid GCP credentials and all required environment variables, **When** the backend deploy script runs, **Then** Cloud Run reports the service as healthy and `/health` returns 200.
2. **Given** a deployed Cloud Run service that has been idle, **When** the first request arrives, **Then** the response is received within 3 seconds.
3. **Given** a Cloud Run deployment missing any required environment variable, **When** the container starts, **Then** startup fails with a clear error listing the missing variable names — no silent failures.

---

### User Story 2 — Serve Frontend via Firebase Hosting (Priority: P1)

The operator runs a frontend deploy script that publishes the static frontend files to Firebase Hosting. The app is immediately accessible at a Firebase HTTPS URL. Every application route loads correctly when navigated to directly.

**Why this priority**: Firebase Hosting delivers the static frontend with CDN performance and provides the routing layer for the API proxy — required before end-to-end testing is possible.

**Independent Test**: Run the frontend deploy script. Open `https://<firebase-site>.web.app/screener` directly in a new browser tab — the screener page loads without a 404.

**Acceptance Scenarios**:

1. **Given** a successful frontend deploy, **When** a user navigates directly to `/`, `/screener`, or any app route, **Then** the correct page loads (no 404 from Firebase).
2. **Given** a successful frontend deploy, **When** the user loads the login page and clicks "Connect Schwab Account", **Then** the OAuth redirect to Schwab initiates.
3. **Given** a successful frontend deploy, **When** static files (JavaScript, CSS) are requested, **Then** they are served with caching headers that allow CDN-layer caching.

---

### User Story 3 — API and Auth Proxy to Cloud Run (Priority: P1)

All requests to `/api/**` and `/auth/**` made from the Firebase-hosted frontend are transparently forwarded to the Cloud Run backend. The user interacts with a single domain; the backend is not directly exposed.

**Why this priority**: Without this proxy, the frontend and backend cannot communicate — the core product is non-functional.

**Independent Test**: After deploying both services, complete the OAuth login flow from the Firebase URL, then click Refresh on the dashboard. Positions load. No CORS errors appear in browser DevTools.

**Acceptance Scenarios**:

1. **Given** both services deployed, **When** the frontend calls `/api/positions/refresh` with a valid bearer token, **Then** the response returns positions data from Cloud Run.
2. **Given** both services deployed, **When** Schwab redirects to `/auth/callback`, **Then** Cloud Run handles the token exchange and the browser stores the token in sessionStorage.
3. **Given** an absent or expired token, **When** any `/api/**` endpoint is called, **Then** Cloud Run returns 401 and the client redirects to the login page.

---

### User Story 4 — One-Command Full Deployment (Priority: P2)

A single top-level deploy script deploys both the backend and frontend in the correct order (backend first, then frontend), printing the live URLs upon completion.

**Why this priority**: Developer experience improvement. P1 stories cover individual deployments; this is a convenience wrapper for routine re-deployments.

**Independent Test**: From a shell with credentials configured, run the combined deploy script. Both services deploy without intervention, and the output shows the Cloud Run URL and Firebase Hosting URL.

**Acceptance Scenarios**:

1. **Given** GCP credentials configured, **When** the combined deploy script runs, **Then** both Cloud Run and Firebase Hosting are updated and the URLs are printed.
2. **Given** a backend deploy failure, **When** the combined deploy script is running, **Then** the frontend deploy does not proceed and the error is surfaced clearly.

---

### Edge Cases

- What if the Schwab developer app's registered callback URL does not match the Firebase Hosting domain? The OAuth flow fails with a redirect_uri mismatch; the operator must update the Schwab app and `SCHWAB_REDIRECT_URI`.
- What if Cloud Run scales to zero mid-session? Cold-start latency is expected on the next request; the UI should indicate loading.
- What if the operator deploys the frontend before the backend? Proxy routes exist but return gateway errors until the backend is live.
- What if the Cloud Run service URL changes? The Firebase proxy target must be updated and the frontend redeployed.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An operator MUST be able to deploy the API backend to Cloud Run in us-central1 by running a single script, with all configuration supplied via environment variables.
- **FR-002**: An operator MUST be able to deploy the static frontend to Firebase Hosting by running a single script, with all configuration supplied via environment variables.
- **FR-003**: Deploy scripts MUST require no manual editing of URLs or identifiers between runs — all targets (GCP project, service name, Firebase site) MUST be read from environment variables or a shared configuration file.
- **FR-004**: Firebase Hosting MUST proxy all `/api/**` and `/auth/**` requests to the Cloud Run service URL.
- **FR-005**: Firebase Hosting MUST serve a root `index.html` for any route that does not match a static file or a proxy rule, enabling direct URL navigation to any client-side route.
- **FR-006**: The Cloud Run service MUST refuse to start and emit a clear error if any required Schwab OAuth environment variable is absent.
- **FR-007**: The Cloud Run service MUST be configured to run as a single instance at all times to preserve session state across requests.
- **FR-008**: The Cloud Run service MUST be configured to scale to zero when idle.
- **FR-009**: Deploy scripts MUST print the live Cloud Run URL and Firebase Hosting URL upon successful completion.
- **FR-010**: The backend deployment package MUST exclude development-only files (tests, specs, local environment files, and local credential files) to minimise deployment size and prevent credential leakage.

### Key Entities

- **Cloud Run Service**: The deployed backend, identified by GCP project, region (`us-central1`), and service name. Exposes `/api/**`, `/auth/**`, and `/health`.
- **Firebase Hosting Site**: The CDN-hosted frontend, identified by Firebase project and site name. Serves static files and proxies `/api/**` and `/auth/**` to the Cloud Run service.
- **Deploy Configuration**: The set of environment variables required by deploy scripts and the Cloud Run container (`GCP_PROJECT_ID`, `CLOUD_RUN_SERVICE_NAME`, `FIREBASE_PROJECT_ID`, and all `SCHWAB_*` variables).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator with GCP and Firebase credentials can deploy both backend and frontend from a clean checkout in under 10 minutes.
- **SC-002**: The backend service responds to requests within 3 seconds of a cold start (no pre-warmed instance).
- **SC-003**: The full OAuth login flow (login page → Schwab authorization → callback → dashboard) completes successfully when accessed via the Firebase Hosting URL.
- **SC-004**: Positions refresh and screener refresh return correct data when the frontend is accessed from the Firebase Hosting URL.
- **SC-005**: Every application route (e.g., `/`, `/screener`) is directly navigable without a 404 error.
- **SC-006**: Deploy scripts complete with zero manual steps after initial GCP/Firebase credential configuration.

---

## Assumptions

- The operator has a GCP project with billing enabled and the Cloud Run and Firebase Hosting APIs activated.
- Firebase Hosting and Cloud Run are deployed to the same GCP project.
- `SCHWAB_REDIRECT_URI` must be updated to the Firebase Hosting domain (e.g., `https://<project>.web.app/auth/callback`) and registered in the Schwab developer app before the OAuth flow will work in production.
- The current server-rendered templates are static enough (no per-request data injected into HTML; data is loaded by client-side JavaScript) to be pre-rendered to static HTML files at deploy time.
- Single-instance deployment is a firm constraint inherited from the existing session management mechanism.
- The dev-login route is excluded from production — no `schwab_token.json` is included in the container image.
- Deployment region is `us-central1` for both Cloud Run and Firebase Hosting.
- A custom domain is out of scope; the Firebase-generated `.web.app` domain is acceptable for v1.
