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

## Verifying Security Controls (Constitution v3.1.0)

### Content Security Policy

```bash
curl -s -o /dev/null -D - http://localhost:8000/ | grep -i content-security-policy
```

Expected: `Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.tailwindcss.com 'nonce-<...>'; ...`

Verify the nonce value changes on each request (run curl twice and compare).

### Security Response Headers

```bash
curl -s -o /dev/null -D - http://localhost:8000/ | grep -iE 'x-frame-options|x-content-type-options|referrer-policy|strict-transport-security|cache-control'
```

Expected headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production only, requires `HTTPS_ONLY=true`)
- `Cache-Control: no-store` (on API routes)

### CORS

```bash
curl -s -o /dev/null -D - -H "Origin: https://evil.example.com" http://localhost:8000/api/accounts
```

Expected: No `Access-Control-Allow-Origin` header returned for unauthorized origins.

### Rate Limiting

```bash
for i in {1..65}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/screener/refresh -H "Authorization: Bearer test"; done
```

Expected: First 60 return `401` (unauthenticated), subsequent requests within the same minute return `429 Too Many Requests`.

### pip-audit

```bash
bash scripts/audit.sh
```

Expected: `No known vulnerabilities found` or a list of CVEs that must be resolved before release.

---

## Running Tests

```bash
pytest tests/ -v
```

Test files:
- `tests/contract/test_accounts_api.py` — contract tests for `GET /api/accounts` and account_hash validation
- `tests/unit/test_account_hash.py` — unit tests for `account_hash` resolution logic
- `tests/contract/test_security_headers.py` — contract tests for CSP, X-Frame-Options, CORS, rate limiting
- `tests/unit/test_security_middleware.py` — unit tests for nonce generation, header values, error handler

---

## Key Files Changed

| File | Change |
|------|--------|
| `src/api/routes/accounts.py` | New — `GET /api/accounts` endpoint |
| `src/api/routes/screener.py` | Add `account_hash` query param |
| `src/api/main.py` | Register accounts router; add CSP, security headers, CORS, rate limiting, error handler |
| `src/services/schwab_client.py` | Accept `account_hash` in `_fetch_positions` |
| `src/services/covered_call_screener.py` | Accept `account_hash`, pass to client |
| `frontend/static/js/account_picker.js` | New — picker init, storage, helper exports |
| `frontend/static/js/screener_ui.js` | Use `withAccountHash()` on refresh URL |
| `frontend/static/js/positions_ui.js` | Use `withAccountHash()` on refresh URL |
| `frontend/templates/base.html` | Add account picker to nav; add `nonce="{{ csp_nonce }}"` to inline scripts |
| `scripts/audit.sh` | New — pip-audit dependency CVE scan |
| `requirements.txt` | Add `slowapi`, `limits`; confirm all deps exact-versioned |
| `tests/contract/test_accounts_api.py` | New — contract tests (account picker) |
| `tests/unit/test_account_hash.py` | New — unit tests (account hash) |
| `tests/contract/test_security_headers.py` | New — security header contract tests |
| `tests/unit/test_security_middleware.py` | New — security middleware unit tests |
