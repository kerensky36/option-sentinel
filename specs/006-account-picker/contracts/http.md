# HTTP API Contracts: Account Picker Dropdown

**Feature**: 006-account-picker
**Date**: 2026-05-14
**Base URL**: `/`
**Auth**: All routes require `Authorization: Bearer <access_token>` unless noted.

---

## New Endpoint

### GET /api/accounts

Returns all Schwab brokerage accounts accessible via the current Bearer token.

**Auth required**: Yes  
**Query params**: None

**Success response**: `200 OK`
```json
[
  { "accountNumber": "...5678", "hashValue": "a3b9c2..." },
  { "accountNumber": "...1234", "hashValue": "f7e4d1..." }
]
```

**Fields**:
| Field | Type | Notes |
|-------|------|-------|
| `accountNumber` | string | Masked: `"..." + last 4 digits`. Disambiguated with more digits if last-4 are non-unique across accounts on the same token. |
| `hashValue` | string | Schwab API hash — opaque to the client; used as the `account_hash` param on subsequent requests. |

**Error responses**:
- `401 {"detail": "Missing or invalid token"}` — Bearer header absent or malformed
- `502 {"detail": "Failed to fetch accounts"}` — Schwab API call failed

**Notes**:
- Response is ordered consistently with what Schwab returns (no guaranteed sort order).
- Not cached server-side; each call fetches live from Schwab.
- The server MUST NOT log the `hashValue` values.

---

## Modified Endpoints

### GET /api/positions/refresh

Existing endpoint. Adds optional `account_hash` query parameter.

**Auth required**: Yes

**Query params**:
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `account_hash` | string | No | Hash of the target account. If absent, uses first account returned by Schwab. If provided but not found: `422`. |

**Success response**: Unchanged — JSON array of position objects.

**New error responses**:
- `422 {"detail": "Account hash not found on this token"}` — `account_hash` provided but not in the account list.

---

### GET /api/screener/refresh

Existing endpoint. Adds optional `account_hash` query parameter.

**Auth required**: Yes

**Query params**:
| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `account_hash` | string | No | Hash of the target account. If absent, uses first account returned by Schwab. If provided but not found: `422`. |

**Success response**: Unchanged — JSON array of screener result objects.

**New error responses**:
- `422 {"detail": "Account hash not found on this token"}` — `account_hash` provided but not in the account list.

---

## Frontend Contract

The account picker module (`account_picker.js`) exposes:

```js
// Returns the currently selected account hash from sessionStorage, or null.
export function getSelectedAccountHash(): string | null

// Appends ?account_hash=<hash> to a URL string if a selection exists.
export function withAccountHash(url: string): string
```

`screener_ui.js` and `positions_ui.js` call `withAccountHash('/api/.../refresh')` before each fetch.
