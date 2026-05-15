# Feature Specification: Account Picker Dropdown

**Feature Branch**: `006-account-picker`
**Created**: 2026-05-14
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select Active Account After Login (Priority: P1)

After connecting their Schwab token, a user with multiple brokerage accounts sees a dropdown in the navigation area listing all available accounts. They select the account they want to trade from and all subsequent data views reflect that account.

**Why this priority**: The entire feature depends on account selection being available. Without it, multi-account users cannot use the screener or positions views correctly (currently defaults to first account).

**Independent Test**: A user with two Schwab accounts logs in, sees both in the dropdown, selects the second, then navigates to Positions — the positions displayed belong to the second account.

**Acceptance Scenarios**:

1. **Given** a user has authenticated and has 2+ Schwab accounts, **When** any view loads, **Then** the nav area shows an account picker dropdown listing all accounts by masked number (e.g., `...1234`)
2. **Given** the account picker is visible, **When** the user selects a different account, **Then** the active data view refreshes using the newly selected account
3. **Given** a user has only one Schwab account, **When** any view loads, **Then** the account picker is still shown (pre-selected, not interactive or shown as static label)

---

### User Story 2 - Account Selection Persists During Session (Priority: P2)

A user selects an account, navigates between the screener and positions views, and does not have to re-select their account on each page.

**Why this priority**: Without session persistence, the feature is unusable for any multi-page workflow.

**Independent Test**: Select account `...5678` on the screener page, navigate to positions — account picker still shows `...5678` as selected.

**Acceptance Scenarios**:

1. **Given** the user selected account `A` on the screener, **When** they navigate to positions, **Then** account `A` is still selected in the picker
2. **Given** the user refreshes the page, **When** the page reloads, **Then** the previously selected account is restored (persisted in browser storage alongside the token)
3. **Given** the user clears their stored token ("Erase All"), **When** the page reloads, **Then** the account selection is also cleared

---

### User Story 3 - Single-Account Users See No Friction (Priority: P3)

A user with exactly one Schwab account experiences no change to their existing workflow — the account picker auto-selects their sole account without requiring any interaction.

**Why this priority**: The majority of current users may have one account; they must not be disrupted.

**Independent Test**: A single-account user logs in and navigates to screener — positions and screener data load without any account-selection interaction required.

**Acceptance Scenarios**:

1. **Given** a user has exactly one Schwab account, **When** any view loads, **Then** data loads automatically using that account
2. **Given** a user has exactly one account, **When** the picker is rendered, **Then** it is pre-selected and either hidden or rendered as a non-interactive label

---

### Edge Cases

- What happens when the account list API call fails (network error or expired token)? → Show error state in picker; do not silently use a default.
- What happens if the previously stored account hash is no longer in the account list (e.g., account closed)? → Fall back to first available account and update stored selection.
- What happens when an account has no positions or no screener-eligible underlyings? → Existing empty-state handling applies; no account-picker-specific behaviour needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose an API endpoint that returns all Schwab accounts accessible via the current Bearer token, including masked account number and account hash.
- **FR-002**: The frontend MUST display an account picker dropdown in the shared navigation area of all authenticated views (screener, positions).
- **FR-003**: The picker MUST list each account by its masked number (last 4 digits, e.g., `...1234`) or nickname when available.
- **FR-004**: All account-specific API requests (positions fetch, screener refresh) MUST include the selected account hash so the backend uses the correct account.
- **FR-005**: The selected account MUST be persisted in browser storage so it survives page navigation and browser refresh within the same session.
- **FR-006**: When the user clears their stored token ("Erase All"), the stored account selection MUST also be cleared.
- **FR-007**: If only one account is available, the system MUST auto-select it without requiring user interaction.
- **FR-008**: If the stored account hash is no longer present in the fetched account list, the system MUST fall back to the first available account.
- **FR-009**: If the accounts API call fails, the picker MUST display an error state; data views MUST NOT silently fall back to a hardcoded default account.

### Key Entities

- **Account**: A Schwab brokerage account accessible via the current OAuth token. Attributes: `accountNumber` (raw, masked for display), `hashValue` (used for all API calls).
- **Selected Account**: The account currently chosen by the user. Stored in browser storage as `hashValue`. Cleared alongside the token on "Erase All".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with multiple accounts can switch between accounts and see correct data within 2 user interactions (open picker → select account).
- **SC-002**: Account selection survives page navigation 100% of the time within the same browser session.
- **SC-003**: Single-account users require zero additional interactions compared to pre-feature behaviour.
- **SC-004**: Account list loads and populates the picker within 2 seconds of page load on a normal connection.
- **SC-005**: "Erase All" clears account selection alongside the token in 100% of cases.

## Assumptions

- Schwab tokens can access 1–10 accounts; no pagination of account list is needed.
- The app is already stateless (no server-side session); account selection state lives in browser storage alongside the token, consistent with the existing architecture.
- Account nicknames are not reliably available via the Schwab API; masked account number (`...NNNN`) is the safe display default.
- The login view does not need the account picker (user has not authenticated yet); the picker appears only after a valid token is present.
- Mobile/responsive layout is out of scope for v1; the picker is designed for desktop.
- The backend `account_hash` parameter will be passed by the frontend as a query parameter on relevant API endpoints.
