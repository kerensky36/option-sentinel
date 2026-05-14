# Feature Specification: Stateless Ephemeral Refactor

**Feature Branch**: `004-stateless-ephemeral-refactor`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "Stateless ephemeral refactor: remove the database entirely and make Option Sentinel a zero-persistence server. All live data fetched on-demand from Schwab API. User metadata stored in browser localStorage. Schwab OAuth token stored in browser sessionStorage — never persisted server-side. Position data cached in browser IndexedDB. Trader has a one-click Erase All button to wipe all browser-stored data. Cloud Run is a transparent API forwarder only — it never stores or logs the token. No background polling. Alerts deferred. Deploy to GCP Cloud Run scale-to-zero."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Schwab OAuth Login (Priority: P1)

A trader navigates to Option Sentinel and is prompted to connect their Schwab account. They are redirected to the Schwab OAuth login page, authorise the app, and are returned to the dashboard. The Schwab token is delivered to the browser and stored in sessionStorage — it never exists in a server-side session, cookie, database, or log.

**Why this priority**: Without authentication, no data can be fetched. All other features depend on a valid Schwab token being present in the browser.

**Independent Test**: Open the app, complete the OAuth flow, verify the dashboard loads. Open DevTools → Application → sessionStorage and confirm the token is present there. Open DevTools → Network and confirm no response sets a token-carrying cookie. Open Cloud Run logs and confirm the token value does not appear.

**Acceptance Scenarios**:

1. **Given** the trader visits the app with no token in sessionStorage, **When** they click "Connect Schwab Account", **Then** they are redirected to the Schwab OAuth authorisation page.
2. **Given** the trader has authorised the app on Schwab's page, **When** they are redirected back to the callback URL, **Then** the token is written to browser sessionStorage by client-side JavaScript and the trader lands on the dashboard; the token MUST NOT appear in the URL, any cookie, or any server log.
3. **Given** the trader's sessionStorage token is absent (tab closed and reopened, or manually cleared), **When** they attempt to use the app, **Then** the dashboard prompts them to reconnect their Schwab account.
4. **Given** the trader clicks "Disconnect / Log Out", **When** the action completes, **Then** sessionStorage, IndexedDB position cache, and all localStorage entries are cleared and they are returned to the login page.

---

### User Story 2 - Live Positions Dashboard (Priority: P1)

A trader opens the dashboard and sees their current open options positions with real-time market data, fetched directly from Schwab on demand. They can click a Refresh button at any time to pull the latest data. There is no automatic polling.

**Why this priority**: The position dashboard is the core value of the app. All other features are secondary to seeing live position data.

**Independent Test**: After login, the dashboard loads and a Refresh button fetches positions from Schwab and renders them. Delivers full standalone value as a position viewer.

**Acceptance Scenarios**:

1. **Given** the trader is logged in, **When** they click Refresh on the dashboard, **Then** all open options positions are displayed with symbol, strike, expiry, quantity, current mark, unrealised P&L, days to expiry, and Greeks.
2. **Given** the dashboard is displaying positions, **When** the trader clicks Refresh again, **Then** the app fetches updated data from Schwab and re-renders the table with the latest values.
3. **Given** the market is closed, **When** the trader loads the dashboard, **Then** positions are displayed with the last available Schwab data and a visible "Market Closed" indicator.
4. **Given** Schwab does not return a Greek value for a position, **When** the dashboard renders that position, **Then** the Greek is calculated via Black-Scholes and shown with a "calculated" indicator.

---

### User Story 3 - Browser-Persisted Thesis Groups (Priority: P2)

A trader creates thesis group labels and assigns positions to them. These thesis groups are stored in the trader's browser (localStorage) and applied client-side when the dashboard renders. The server has no knowledge of thesis data.

**Why this priority**: Thesis groupings add meaningful organisation to position data but are not required for baseline functionality.

**Independent Test**: Create a thesis group, assign a position, reload the page — the assignment persists from localStorage. The server receives no thesis data.

**Acceptance Scenarios**:

1. **Given** the trader is on the dashboard, **When** they create a new thesis group with a name and template type, **Then** the group is saved to browser localStorage and appears in the thesis selector.
2. **Given** a thesis group exists in localStorage, **When** the page is reloaded, **Then** the thesis groups and their position assignments are restored without any server round-trip.
3. **Given** the trader assigns a position to a thesis group, **When** the dashboard re-renders, **Then** the position row shows the thesis group name from the localStorage mapping.
4. **Given** the trader clears browser data or uses a different browser, **When** they log in, **Then** thesis groups are absent — this is expected behaviour since localStorage is device-local.

---

### User Story 4 - Erase All Data (Priority: P2)

A trader wants to completely wipe all of their data from the browser with a single button click — their Schwab token, cached positions, thesis groups, spread definitions, and exit goals. After erasing, the app returns to the login screen as if it were a fresh install.

**Why this priority**: Traders must have full, immediate control over their data. This is the escape hatch that makes the privacy model trustworthy.

**Independent Test**: Log in, refresh positions, create a thesis group. Click "Erase All Data". Confirm browser DevTools shows sessionStorage, IndexedDB, and localStorage all empty. Confirm the app shows the login page.

**Acceptance Scenarios**:

1. **Given** the trader has active session data (token, cached positions, thesis groups), **When** they click "Erase All Data" and confirm the prompt, **Then** sessionStorage is cleared, the IndexedDB `option-sentinel` database is deleted, and all localStorage keys are removed.
2. **Given** all data has been erased, **When** the page redirects, **Then** the trader lands on the login page with no session token present anywhere in the browser.
3. **Given** the trader erases all data, **When** they inspect the browser storage in DevTools, **Then** no Schwab token, position data, thesis groups, or any other app data is present.
4. **Given** the trader clicks "Erase All Data" accidentally, **When** a confirmation prompt appears, **Then** they can cancel and all data is preserved intact.

---

### User Story 5 - Covered Call Screener (Priority: P2)

A trader navigates to the Covered Call Screener page and clicks Refresh. The app fetches their long stock positions from their second Schwab account and computes covered call recommendations in real time, using the token from sessionStorage. The server never stores or logs the token used for this request.

**Why this priority**: The screener delivers direct trading value but is secondary to the positions dashboard.

**Independent Test**: Navigate to the screener page, click Refresh, verify ranked covered call recommendations appear for long stock positions.

**Acceptance Scenarios**:

1. **Given** the trader is on the Screener page, **When** they click Refresh, **Then** the app fetches long stock positions from the configured second Schwab account and computes covered call rankings.
2. **Given** screener results are displayed, **When** the trader views a row, **Then** it shows ticker, shares, IV rank, recommended strike and expiry, bid premium, annualised yield, call delta, days to earnings, and composite score.
3. **Given** a position has an earnings event within 7 days, **When** the screener computes its ranking, **Then** it is flagged as suppressed for covered call recommendations.

---

### User Story 6 - Cloud Run Cold Start (Priority: P3)

A trader opens the app after it has scaled to zero on Cloud Run. The app starts, the login page is rendered within 3 seconds of the container becoming reachable.

**Why this priority**: Scale-to-zero cold starts are unavoidable; the experience must remain acceptable.

**Independent Test**: Stop the container, wait, open the URL — measure time from first byte to interactive login page.

**Acceptance Scenarios**:

1. **Given** the Cloud Run instance has scaled to zero, **When** a trader navigates to the app URL, **Then** the login page is rendered within 3 seconds of the container starting.
2. **Given** the app has cold-started, **When** the trader logs in, **Then** no session data from any previous user's session is present.

---

### Edge Cases

- What happens when the Schwab API returns a rate-limit error during a manual refresh?
- How does the app behave if localStorage is unavailable in the browser?
- What happens if the Schwab OAuth token expires mid-session while the trader is viewing the dashboard?
- What happens when the screener account has no long stock positions?
- What happens if the user opens the app in two browser tabs simultaneously?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The server MUST NOT connect to or depend on any external or embedded database.
- **FR-002**: The Schwab OAuth token MUST be stored exclusively in browser `sessionStorage` by client-side JavaScript; the server MUST NOT store the token in any session, cookie, database, or file at any point.
- **FR-003**: The server MUST implement a Schwab OAuth 2.0 authorisation code flow; the `/auth/callback` endpoint MUST deliver the token to the browser via an inline JavaScript snippet in the callback HTML page, which writes it to `sessionStorage` before redirecting to the dashboard.
- **FR-004**: On logout and on "Erase All Data", the client MUST clear `sessionStorage`, delete the `option-sentinel` IndexedDB database, and remove all `localStorage` keys; the server has no session state to clear.
- **FR-005**: The server MUST NOT perform any background polling or run any scheduled jobs; all data fetches MUST be triggered by explicit user action.
- **FR-006**: The server MUST expose a positions refresh endpoint; the client MUST send the token as an `Authorization: Bearer <token>` header; the server MUST forward this header to Schwab and return raw JSON; the server MUST NOT log the value of the `Authorization` header.
- **FR-007**: The server MUST expose a screener refresh endpoint using the same `Authorization` header forwarding pattern as FR-006.
- **FR-008**: The client MUST cache the raw positions JSON response in browser IndexedDB after each successful refresh, keyed by fetch timestamp, so positions are available on page reload without a new network request.
- **FR-009**: Thesis group definitions, position-to-thesis assignments, spread parameters, and exit goals MUST be stored exclusively in browser `localStorage`; the server MUST NOT persist or receive this data.
- **FR-010**: The client MUST read thesis assignments from `localStorage` and apply them when rendering the positions table, without a server round-trip.
- **FR-011**: The dashboard MUST display a clearly labelled "Erase All Data" button accessible from every page; clicking it MUST prompt for confirmation before executing FR-004.
- **FR-012**: All alert infrastructure — models, rules, delivery, deduplication, and email sending — MUST be removed from the codebase.
- **FR-013**: The background scheduler (APScheduler) and all scheduled jobs MUST be removed.
- **FR-014**: The SSE (Server-Sent Events) push endpoint MUST be removed; the UI uses pull-on-demand only.
- **FR-015**: The application MUST start with no database migration step.
- **FR-016**: The application MUST be deployable to GCP Cloud Run with `min-instances=0`, `max-instances=1`, and no persistent volume mounts.
- **FR-017**: The application container MUST reach a ready state (first successful health-check response) within 3 seconds of process start.

### Key Entities

- **Token** (sessionStorage): Schwab OAuth access + refresh token dict. Stored only in browser `sessionStorage` by client JS after OAuth callback. Cleared on tab close, logout, or "Erase All". Never touches a server log, cookie, or file.
- **PositionCache** (IndexedDB): Raw JSON positions array written to the `option-sentinel` IndexedDB database after each successful refresh. Survives page reloads. Cleared by "Erase All". Never sent back to the server.
- **Position** (in-memory, server): Live options position data assembled by the server per refresh request from raw Schwab API responses. Returned as JSON. Never stored server-side.
- **Greeks** (in-memory, server): Per-position Greek values from Schwab or Black-Scholes fallback. Returned as part of Position JSON. Never stored server-side.
- **ThesisGroup** (localStorage): User-defined named grouping with template type, stored as JSON in the browser.
- **ThesisAssignment** (localStorage): Mapping of position symbol to thesis group ID, stored as JSON in the browser.
- **ScreenerResult** (in-memory, server): Computed covered call ranking returned per screener refresh request. Never persisted anywhere.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The login page is interactive within 3 seconds of a Cloud Run cold start.
- **SC-002**: A manual positions refresh completes and renders within 5 seconds under normal Schwab API conditions.
- **SC-003**: Thesis group assignments created in one session persist across a full page reload in the same browser.
- **SC-004**: The server process uses under 256 MB RAM at idle.
- **SC-005**: Zero database connection strings, ORM imports, or migration files remain in the production code path after the refactor.
- **SC-006**: The screener refresh returns ranked results within 10 seconds of the button click.
- **SC-007**: After "Erase All Data" completes, browser DevTools confirms sessionStorage, IndexedDB, and localStorage are all empty.
- **SC-008**: Cloud Run access logs contain no Schwab token values; the Authorization header is excluded from all log sinks.
- **SC-009**: Cached positions are available for rendering immediately on page reload (from IndexedDB, no network request required).

## Assumptions

- The existing Schwab API client code can be reused as-is; only the persistence layer around it is removed.
- The Black-Scholes Greek fallback calculation is retained.
- Browser `sessionStorage`, `localStorage`, and `IndexedDB` are available; the app does not need to support environments where they are blocked.
- A single Cloud Run instance serving one user at a time is the intended deployment; horizontal scaling is out of scope.
- The second Schwab account number for the screener is configured via environment variable.
- Schwab's API does not support browser CORS; all Schwab API calls are proxied through Cloud Run. The token transits Cloud Run in-flight but is never logged or stored.
- HTTPS is provided by Cloud Run managed TLS; all cookies set by the app are `Secure`.
- Thesis and position cache data loss on "Erase All" or browser storage clear is expected behaviour; no export/import UI is required.
- Email alerting and all related infrastructure are deferred indefinitely and will not be implemented in this feature.
