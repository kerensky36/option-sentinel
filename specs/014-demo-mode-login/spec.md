# Feature Specification: Demo Mode Login

**Feature Branch**: `014-demo-mode-login`
**Created**: 2026-05-22
**Status**: Draft
**Input**: User description: "I want to add a new login flow for demo mode with a yellow demo login button that allows users to login without the Schwab login flow and just go straight into the app. The app should display some dummy account data for a few different accounts. One account should be option spreads only and the other account should be equities and ETFs. The demo world should never overlap with the real Schwab flow"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Demo Entry via Yellow Button (Priority: P1)

A prospective user or developer visits the login page and wants to explore the app
without connecting a real Schwab account. They click the yellow "Try Demo" button,
bypass OAuth entirely, and land directly on the dashboard in demo mode.

**Why this priority**: Core value of the feature — everything else builds on entering demo mode.

**Independent Test**: Click "Try Demo" on the login page. Verify the user reaches the
dashboard with a visible "DEMO MODE" banner and no Schwab API call was made.

**Acceptance Scenarios**:

1. **Given** the login page, **When** the user clicks "Try Demo", **Then** the user lands on the dashboard without any OAuth redirect occurring
2. **Given** demo mode is active, **When** the dashboard loads, **Then** a clearly visible yellow "DEMO MODE" banner is displayed at all times
3. **Given** demo mode, **When** the user inspects network traffic, **Then** no requests are made to any Schwab endpoint
4. **Given** demo mode, **When** the app encounters any code path that would normally call the Schwab API, **Then** static demo data is returned instead

---

### User Story 2 — Option Spreads Demo Account (Priority: P2)

The user is in demo mode and selects the first demo account, which contains realistic
option spread positions (vertical spreads, iron condors, or similar multi-leg structures).
They can view positions and P&L without connecting real data.

**Why this priority**: Demonstrates the app's core options-tracking capability to new users.

**Independent Test**: Enter demo mode, select the spreads account, verify the positions
table shows multi-leg option positions with realistic P&L data.

**Acceptance Scenarios**:

1. **Given** demo mode is active, **When** the user selects "Demo Spreads Account", **Then** the positions table renders option spread positions with strike, expiry, quantity, cost, mark, and unrealised P&L columns populated
2. **Given** the spreads demo account, **When** positions are displayed, **Then** at least 3 distinct option spread legs are shown across at least 2 different underlyings
3. **Given** the spreads demo account, **When** the user views positions, **Then** Greeks (delta, theta) are displayed for each position

---

### User Story 3 — Equities & ETFs Demo Account (Priority: P2)

The user switches to the second demo account, which contains equity and ETF long
positions. They can view stock holdings and P&L to see how that view works.

**Why this priority**: Covers the covered-call screener demo use case (long stock needed for screener).

**Independent Test**: Enter demo mode, select the equities/ETFs account, verify the
positions table shows stock/ETF positions with share counts and P&L.

**Acceptance Scenarios**:

1. **Given** demo mode is active, **When** the user selects "Demo Equities & ETFs Account", **Then** the positions table renders equity/ETF positions with symbol, shares, cost basis, current mark, and unrealised P&L populated
2. **Given** the equities/ETFs account, **When** positions are displayed, **Then** at least 4 distinct equity or ETF positions are shown
3. **Given** the equities/ETFs account, **When** the user navigates to the screener tab, **Then** the screener can use the demo equity holdings as candidates

---

### User Story 4 — Complete Isolation from Schwab Flow (Priority: P1)

Demo mode must never contaminate a real Schwab session and vice versa. Entering demo
mode does not persist any state that could interfere with a subsequent real login.

**Why this priority**: Prevents data integrity and security issues.

**Independent Test**: Complete a demo session (enter demo, browse, exit). Then perform a
real Schwab login. Verify no demo artefacts remain and the real session works normally.

**Acceptance Scenarios**:

1. **Given** a user has completed a demo session, **When** they open a new tab and log in with Schwab, **Then** no demo data appears and the session behaves as a normal Schwab session
2. **Given** demo mode is active, **When** the user logs out or closes the tab, **Then** all demo data is cleared from browser storage
3. **Given** a real Schwab session is active in another tab, **When** a user opens a new tab and enters demo mode, **Then** the real session is unaffected (sessionStorage is tab-scoped by default)
4. **Given** demo mode, **When** any API endpoint would normally be called with a real Bearer token, **Then** the demo data path is taken and no Bearer token is generated or sent

---

### Edge Cases

- What happens when the user opens browser DevTools and manually sets `demo_mode` in a real session? *(Out of scope — demo mode is for legitimate UX purposes, not security isolation)*
- What happens if the user refreshes the page during demo mode? → Demo mode persists within the same tab via sessionStorage
- What if demo data doesn't match the exact schema expected by the UI? → Demo data must conform to the same shape as real API responses to avoid rendering errors

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The login page MUST display a yellow "Try Demo" button alongside the Schwab login button
- **FR-002**: Clicking "Try Demo" MUST bypass Schwab OAuth and immediately navigate to the app dashboard
- **FR-003**: Demo mode MUST be marked in browser sessionStorage so the frontend can detect it throughout the session
- **FR-004**: The dashboard MUST display a persistent yellow "DEMO MODE" banner when demo mode is active
- **FR-005**: Demo mode MUST provide at least two selectable demo accounts in the account picker
- **FR-006**: Demo Account A MUST contain only option spread positions (multi-leg options)
- **FR-007**: Demo Account B MUST contain only equity and ETF long positions (no options)
- **FR-008**: Demo data MUST be static, client-side-only; no server-side persistence or Schwab API calls MUST occur during demo mode
- **FR-009**: All app features that normally require a live Schwab API call MUST use pre-seeded demo data when demo mode is active
- **FR-010**: Logging out from demo mode or closing the tab MUST clear all demo data from browser storage
- **FR-011**: The real Schwab login flow MUST remain entirely unchanged and fully functional
- **FR-012**: Demo mode MUST be visually distinct at all times so users cannot confuse demo data for real account data

### Key Entities

- **DemoSession**: A browser sessionStorage marker indicating demo mode is active. Contains: `demo_mode: true`, selected `demo_account_hash`.
- **DemoAccount**: A pre-defined fake account with a synthetic hash, display name, account type (`spreads` | `equities_etfs`), and a static list of positions.
- **DemoPosition**: A static position record conforming to the same shape as a real API position response. For options: symbol, underlying, option type, strike, expiry, quantity, cost, mark, unrealised P&L, Greeks. For equities: symbol, shares, cost basis, current mark, unrealised P&L.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can enter demo mode from the login page in under 3 seconds (button click to dashboard render)
- **SC-002**: 100% of demo sessions produce zero requests to Schwab API endpoints (verifiable via network inspection)
- **SC-003**: Demo mode indicator (yellow banner) is visible on every page while demo mode is active
- **SC-004**: Switching between the two demo accounts takes under 1 second and displays distinct position data for each
- **SC-005**: After a demo session ends (logout or tab close), zero demo artefacts remain in any browser storage
- **SC-006**: The real Schwab OAuth login flow completes successfully and produces correct position data after a prior demo session in the same browser (different tab)

## Assumptions

- Demo data is entirely static and hardcoded in the frontend — no server-side demo data API is needed
- The existing `account_picker.js` UI can be reused to display demo accounts with synthetic hashes
- Demo mode uses the same dashboard, positions table, and screener UI as the real app — no separate demo-only UI is needed
- The demo accounts use synthetic account hash values that cannot collide with real Schwab account hashes
- Demo mode is available to all visitors (no paywall, no authentication requirement beyond clicking the button)
- The app currently supports multiple accounts via the account picker; demo mode reuses this mechanism
- `sessionStorage` isolation (tab-scoped) is sufficient to prevent demo/real data overlap — no additional server-side isolation is required
- Greeks for demo option positions will be pre-computed and embedded in demo data (no live BS calculation needed)
