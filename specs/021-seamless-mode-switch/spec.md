# Feature Specification: Seamless, Stateful Demo ↔ Live Mode Switch

**Feature Branch**: `021-seamless-mode-switch`
**Created**: 2026-09-29
**Status**: Draft
**Input**: User description: "Switching between demo mode and real api mode should be seamless and stateful"
**Amends**: spec 014 (demo mode login). Spec 014's isolation guarantees (US4, FR-008, FR-010, FR-011) still hold.

## Context

Today demo mode is a one-way door. Entering demo from the login page sets a
flag, and the only way back to live Schwab data is **Disconnect**, which wipes
every cache and the Schwab token. Going the other way, clicking "Try Demo"
while a live token is present puts demo data into the same sessionStorage
keys the live session uses (`schwab_selected_account`, `screener_profile`,
`quorum:v1:*`), so the two worlds can overwrite each other.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — One-click switch from anywhere in the app (Priority: P1)

A trader in the app flips a **DEMO | LIVE** switch in the top nav and lands on
the same page in the other mode, without signing out or going back to the
login page.

**Independent Test**: With a live token, click DEMO: the page reloads in demo
mode on the same path. Click LIVE: the page reloads in live mode on the same
path, with no Schwab login.

**Acceptance Scenarios**:

1. **Given** a live session, **When** the user clicks DEMO, **Then** demo mode is on, the Schwab token is kept, and the current page reloads in demo mode.
2. **Given** demo mode and a kept Schwab token, **When** the user clicks LIVE, **Then** demo mode is off and the current page reloads with live data — no OAuth redirect.
3. **Given** demo mode and no Schwab token, **When** the user clicks LIVE, **Then** the browser starts the Schwab OAuth flow (`/auth/start`); after the callback the app is in live mode.
4. **Given** either mode, **When** the page renders, **Then** the switch shows which mode is active, and the yellow DEMO MODE banner is shown only in demo mode.

---

### User Story 2 — Each mode keeps its own state (Priority: P1)

Switching away from a mode and back restores what the user left there: the
selected account, cached positions, screener results and profile, and saved
advice (quorum) results.

**Independent Test**: In live mode select account B and refresh positions.
Switch to demo, pick the equities demo account and change the screener
profile. Switch back to live: account B and its cached positions show at once,
the live screener profile is unchanged. Switch to demo: the equities account
and its screener profile are still selected.

**Acceptance Scenarios**:

1. **Given** state saved in one mode, **When** the user switches mode and back, **Then** the selected account, position cache, screener cache, screener profile and quorum cache for that mode are unchanged.
2. **Given** demo mode, **When** any of the above is saved, **Then** it is written under a key that live mode never reads, and vice versa — no demo value is ever shown in live mode.
3. **Given** a live session saved before this feature, **When** the page loads, **Then** its existing keys are still read (live keys keep their names).

---

### Edge Cases

- Real Schwab login (callback or dev login) while the demo flag is set → the app ends in live mode; demo state is kept for a later switch back.
- "Try Demo" on the login page with a live token already stored → demo mode, token kept.
- A 401 from Schwab in live mode still erases everything (spec 004/014 behaviour unchanged).
- Disconnect and Erase All Data still clear both modes' state (FR-010 of spec 014).
- Closing the tab still clears both modes' state (constitution Principle I).

## Requirements *(mandatory)*

- **FR-401**: The top nav MUST show a DEMO | LIVE switch on every app page, marking the active mode.
- **FR-402**: Switching to demo MUST set the demo flag, keep the Schwab token, and reload the current path.
- **FR-403**: Switching to live with a stored token MUST clear the demo flag and reload the current path without contacting Schwab OAuth.
- **FR-404**: Switching to live with no stored token MUST navigate to `/auth/start`.
- **FR-405**: `/auth/callback` and `/auth/dev-login` MUST clear the demo flag when they store a token. `/auth/demo-login` MUST NOT remove a stored token.
- **FR-406**: In demo mode, every client-side key for selected account, positions, screener results, screener profile and quorum results MUST carry a `demo:` prefix. Live keys MUST keep their current names.
- **FR-407**: All state stays in sessionStorage (constitution Principle I); Disconnect, Erase All Data and tab close clear both modes.
- **FR-408**: In demo mode no request carries the Bearer token (spec 014 US4-4 unchanged).
- **FR-409**: The data-use page MUST say that the Schwab token stays in sessionStorage while demo mode is on and that demo state is kept separately.

## Success Criteria

- **SC-401**: A switch with a stored token takes one click and one page reload, with no login page shown.
- **SC-402**: After live → demo → live, the live selected account and cached positions render from cache with no refresh request.
- **SC-403**: No sessionStorage key written in demo mode is read in live mode (verified by automated test).

## Assumptions

- A full page reload is an acceptable "seamless" switch: the page repaints from the mode's cache immediately.
- The Disconnect button still signs out of both modes.
