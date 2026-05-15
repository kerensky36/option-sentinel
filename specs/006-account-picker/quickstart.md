# Quickstart: Account Picker Dropdown

**Feature**: 006-account-picker
**Date**: 2026-05-14

---

## Prerequisites

- Dev environment from `specs/005-cloudrun-firebase-deploy/quickstart.md` is working.
- A Schwab OAuth token with access to at least one account (two recommended for full testing).

---

## Running Locally

```bash
uvicorn src.api.main:app --reload --port 8000
```

Open `http://localhost:8000`. After connecting your Schwab token, the account picker appears in the top nav.

---

## Testing the Account Picker

### Single-account token
1. Log in with a token that has access to one account.
2. Verify the picker is visible and pre-selected (or rendered as a static label).
3. Navigate between Positions and Screener — no account interaction required.

### Multi-account token
1. Log in with a token that has access to two or more accounts.
2. Verify the picker lists all accounts as `...NNNN`.
3. Select a non-default account.
4. Click Refresh on the Screener — verify the data reflects the selected account.
5. Navigate to Positions — verify the same account is still selected.
6. Refresh the page — verify the selection is restored from sessionStorage.

### Erase All
1. Select an account.
2. Inspect `sessionStorage` in DevTools — confirm `schwab_selected_account` is set.
3. Click "Erase All Data" and confirm.
4. Verify redirect to login and that `sessionStorage` is empty.

### Error state (network simulation)
1. In DevTools → Network, block requests to `/api/accounts`.
2. Reload the page.
3. Verify the picker shows an error state and data views do not auto-load.

---

## Running Tests

```bash
pytest tests/ -v
```

New tests are in:
- `tests/contract/test_accounts_api.py` — contract tests for `GET /api/accounts`
- `tests/unit/test_account_picker.py` — unit tests for `account_hash` resolution logic

---

## Key Files Changed

| File | Change |
|------|--------|
| `src/api/routes/accounts.py` | New — `GET /api/accounts` endpoint |
| `src/api/routes/screener.py` | Add `account_hash` query param |
| `src/api/main.py` | Register accounts router |
| `src/services/schwab_client.py` | Accept `account_hash` in `_fetch_positions` |
| `src/services/covered_call_screener.py` | Accept `account_hash`, pass to client |
| `frontend/static/js/account_picker.js` | New — picker init, storage, helper exports |
| `frontend/static/js/auth.js` | Add `ACCOUNT_HASH_KEY` export (or keep internal to account_picker.js) |
| `frontend/static/js/screener_ui.js` | Use `withAccountHash()` on refresh URL |
| `frontend/static/js/positions_ui.js` | Use `withAccountHash()` on refresh URL |
| `frontend/templates/base.html` | Add `<select id="account-picker">` to top nav |
| `tests/contract/test_accounts_api.py` | New — contract tests |
| `tests/unit/test_account_picker.py` | New — unit tests |
