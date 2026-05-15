# Data Model: Account Picker Dropdown

**Feature**: 006-account-picker
**Date**: 2026-05-14

---

## Overview

This feature introduces no server-side storage. All state is ephemeral per-request on the backend and per-session in the browser. Two logical entities are defined.

---

## Entity 1: Account (API response shape)

Returned by `GET /api/accounts`. Sourced live from the Schwab API on each call; never persisted server-side.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `accountNumber` | `string` | Schwab API | Raw account number (e.g., `"12345678"`). Masked to `"...5678"` for display. |
| `hashValue` | `string` | Schwab API | Encrypted hash used by all Schwab API calls that require an account identifier. 40+ chars, alphanumeric. Never displayed to the user. |
| `displayName` | `string` | Derived | `"..." + accountNumber[-4:]`. Computed server-side before returning to client. Disambiguated with more digits if last-4 are non-unique. |

**Uniqueness**: Each account in a response is unique by `hashValue`. A single OAuth token may grant access to 1–10 accounts.

---

## Entity 2: Selected Account (browser session state)

Stored in `sessionStorage` on the client. Never sent to or stored by the server.

| Key | Storage | Type | Value |
|-----|---------|------|-------|
| `schwab_selected_account` | `sessionStorage` | `string` | The `hashValue` of the currently selected account. |

**Lifecycle**:
- Written: when the user picks an account from the dropdown, or auto-written (first account) if only one account is available.
- Read: on every page load to restore the picker selection; on every authenticated API call to append `?account_hash=`.
- Cleared: by `eraseAll()` via `sessionStorage.clear()` — no additional code required.
- Stale guard: on page load, if the stored `hashValue` is not present in the freshly fetched account list, it is discarded and the first available account is selected.

---

## Backend Parameter

The `account_hash` query parameter is passed by the frontend on account-specific API requests. It is not persisted or cached server-side.

| Parameter | Endpoints | Required | Behaviour when absent |
|-----------|-----------|----------|-----------------------|
| `account_hash` | `GET /api/positions/refresh`, `GET /api/screener/refresh` | No | Falls back to `accounts[0]["hashValue"]` |
| `account_hash` | `GET /api/positions/refresh`, `GET /api/screener/refresh` | — | If provided but not found in account list: `422 Unprocessable Entity` |
