# Research: Account Picker Dropdown

**Feature**: 006-account-picker
**Date**: 2026-05-14

---

## Decision 1: Browser Storage for Selected Account

**Decision**: Store the selected account hash in `sessionStorage` under the key `schwab_selected_account`.

**Rationale**: The access token is already stored in `sessionStorage` (cleared when the tab closes). Storing the account selection in the same place keeps the two pieces of state lifecycle-identical — if the token is gone, the account selection is gone. `eraseAll()` calls `sessionStorage.clear()`, which already covers this key without any code change. Using `localStorage` would cause the account selection to outlive the token, creating a stale state on next login.

**Alternatives considered**:
- `localStorage`: Survives tab close; rejected because it outlives the token and requires explicit cleanup.
- `IndexedDB`: More complex with no benefit over sessionStorage for a single string value.

---

## Decision 2: How the Frontend Passes Account Hash to the Backend

**Decision**: Pass the selected account hash as a URL query parameter `?account_hash=<hash>` on account-specific API requests (`/api/screener/refresh`, `/api/positions/refresh`).

**Rationale**: The backend is stateless — there is no session or cookie to read. A query parameter is the simplest, most transparent mechanism that requires no new headers and is easy to inspect in browser devtools. The account hash is not a secret (it is already sent to Schwab by the backend on behalf of the authenticated token holder), so there is no security concern with it appearing in the URL.

**Alternatives considered**:
- Custom request header (e.g., `X-Account-Hash`): Slightly cleaner but requires changes to `fetchWithAuth` or a separate wrapper; no material benefit.
- Part of the request body (POST): Would require changing GET endpoints to POST; unnecessary complexity.

---

## Decision 3: Backend Fallback When `account_hash` Is Absent or Invalid

**Decision**: If `account_hash` is not provided, the backend uses the first account returned by `list_accounts()`. If the provided hash is not found in the account list, return `422 Unprocessable Entity` with a clear message rather than silently using a default.

**Rationale**: Silently falling back to a wrong account is worse than an error. A missing `account_hash` (e.g., single-account user, first page load before picker is ready) is handled gracefully by using the first account — consistent with current behaviour. An invalid hash means something went wrong client-side and should surface as an error.

**Alternatives considered**:
- Always require `account_hash`: Forces clients to always call `/api/accounts` first; adds a required round-trip even for single-account users.
- Always fall back silently: Masks bugs; rejected.

---

## Decision 4: Account Display Format

**Decision**: Display accounts as masked number: last 4 digits only, e.g. `...1234`. If multiple accounts share the same last 4 digits, show more digits to disambiguate.

**Rationale**: Schwab's `accountNumber` field is a raw numeric string. Showing only the last 4 digits is consistent with standard financial UI conventions (credit/debit card display). Full account numbers should not be displayed in a UI that may be screen-shared.

**Alternatives considered**:
- Account nickname: Schwab doesn't reliably provide nicknames via the API.
- Full account number: Privacy risk in a screen-share context.

---

## Decision 5: Account Picker Location in the UI

**Decision**: Add the picker to the **top navigation bar** (`base.html`) between the logo and the action buttons (Erase All / Disconnect). It is rendered as a `<select>` element styled to match the TOS/dark theme.

**Rationale**: The top nav is shared by all authenticated views and is the single place where global session context is displayed. The left sidebar is view-navigation only. Placing the picker in the top nav means it appears consistently without requiring changes to individual page templates.

**Alternatives considered**:
- Left sidebar: Would need to scroll on mobile and is meant for page navigation, not session context.
- Per-page header: Would require changes to each page template and risk inconsistency.

---

## Decision 6: When to Fetch the Account List

**Decision**: Fetch `/api/accounts` once on page load (in a new `account_picker.js` module imported by `base.html`). Cache the result in a module-level JS variable for the page lifetime. Repopulate the `<select>` with the fetched options and restore the previously stored selection from `sessionStorage`.

**Rationale**: One fetch per page load is cheap. Caching in a JS variable (not storage) is sufficient because the account list is only needed for the duration of the page session. If the fetch fails, show an error state in the picker and leave data views in their pre-fetch state (no auto-load).

**Alternatives considered**:
- Fetch on every Refresh click: Over-fetches; account list rarely changes mid-session.
- Cache in `sessionStorage`: Not needed; the list is fetched fresh each page load and the stored value is just the selected hash.
