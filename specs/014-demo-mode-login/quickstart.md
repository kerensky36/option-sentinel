# Quickstart: Demo Mode Login (014) — 10-Scenario Verification Protocol

Run these scenarios in order after implementation is complete. Each scenario must pass
before the feature is considered shippable.

---

## Scenario 1 — Yellow "Try Demo" button visible on login page

**Setup**: Navigate to `/auth/login` (or `http://localhost:8000/auth/login`).

**Steps**:
1. Observe the login card

**Expected**:
- A yellow button labelled "Try Demo" (or "Try Demo Mode") is visible below the "Connect Schwab Account" button
- The yellow button is visually distinct (yellow/amber background, not indigo)
- The real "Connect Schwab Account" button is unchanged

**Pass criteria**: Yellow demo button present; Schwab button unaffected.

---

## Scenario 2 — Demo entry bypasses OAuth

**Setup**: Login page loaded.

**Steps**:
1. Open browser DevTools → Network tab
2. Click "Try Demo"

**Expected**:
- Browser navigates directly to `/` (dashboard) with no redirect to Schwab auth URL
- No request to any `schwab.com` or `schwab-labs.com` domain appears in the Network tab
- Navigation completes in under 3 seconds

**Pass criteria**: No Schwab redirect; dashboard loads within 3 s.

---

## Scenario 3 — DEMO MODE banner displayed

**Setup**: Arrived at dashboard via "Try Demo" (Scenario 2).

**Steps**:
1. Observe the top of the dashboard page

**Expected**:
- A persistent yellow/amber "DEMO MODE" banner is visible at the top of every page
- The banner is not dismissible and persists across page navigation within the tab

**Pass criteria**: Yellow DEMO MODE banner present on dashboard.

---

## Scenario 4 — Account picker shows two demo accounts

**Setup**: Dashboard loaded in demo mode.

**Steps**:
1. Find the account picker `<select>` in the navigation bar
2. Open the dropdown

**Expected**:
- Exactly two options: "DEMO — Options Spreads" and "DEMO — Equities & ETFs"
- No real Schwab account numbers visible
- No "Error loading accounts" message

**Pass criteria**: 2 demo accounts shown; no errors.

---

## Scenario 5 — Spreads account shows option positions

**Setup**: Demo mode active, account picker visible.

**Steps**:
1. Select "DEMO — Options Spreads"
2. Navigate to the Positions tab (or refresh positions)

**Expected**:
- Positions table renders 6 option legs across 3 underlyings (AAPL, SPY, TSLA)
- Each row shows: symbol, strike, expiry, quantity, cost, mark, unrealised P&L
- Greek columns (delta, theta) populated with non-null values

**Pass criteria**: 6 positions rendered; no null/blank Greek values.

---

## Scenario 6 — Equity account shows equity positions

**Setup**: Demo mode active.

**Steps**:
1. Select "DEMO — Equities & ETFs"
2. Navigate to the Positions tab

**Expected**:
- Positions table shows 2 covered call positions (AAPL CC, VOO CC)
- Each row has symbol, strike, expiry, quantity, cost, mark, unrealised P&L, Greeks

**Pass criteria**: 2 positions rendered for equity account.

---

## Scenario 7 — Screener shows equity holdings for demo equity account

**Setup**: Demo mode active, "DEMO — Equities & ETFs" selected.

**Steps**:
1. Navigate to `/screener`
2. Click "Refresh" (or wait for auto-load)

**Expected**:
- Screener table shows 4 rows: AAPL, VOO, QQQ, MSFT
- AAPL and VOO show `recommended` status
- MSFT shows `suppressed` status (earnings proximity)
- QQQ shows `suppressed` status (low IV rank)

**Pass criteria**: 4 screener rows; status column correct for each.

---

## Scenario 8 — No Schwab API calls during demo session

**Setup**: DevTools Network tab open.

**Steps**:
1. Enter demo mode (Scenario 2)
2. Switch between both demo accounts
3. Refresh positions for each account
4. Run screener for equity account
5. Inspect all network requests

**Expected**:
- Zero requests to any external domain (`api.schwab.com`, etc.)
- All `/api/…` requests go to `localhost:8000` only
- The server does NOT call any Schwab SDK / HTTP client internally (verifiable by server logs showing no outbound requests)

**Pass criteria**: Zero external domain requests observed.

---

## Scenario 9 — Demo session cleared on logout

**Setup**: Demo mode active.

**Steps**:
1. Click "Logout" (or navigate to `/auth/logout`)
2. After redirect to login page, open DevTools → Application → sessionStorage

**Expected**:
- `demo_mode` key absent from sessionStorage
- `schwab_access_token` key absent
- `schwab_selected_account` key absent
- No other demo artefacts remain in any storage

**Pass criteria**: sessionStorage empty after logout.

---

## Scenario 10 — Real Schwab login unaffected after demo session

**Setup**: Schwab credentials available; a previous demo session was completed in a different tab (same browser).

**Steps**:
1. Open a fresh tab
2. Navigate to `/auth/login`
3. Click "Connect Schwab Account"
4. Complete Schwab OAuth flow

**Expected**:
- OAuth flow completes normally (no demo data injected)
- Real account positions load correctly
- No DEMO MODE banner visible
- No demo account entries in the account picker

**Pass criteria**: Real Schwab session fully functional; zero demo contamination.
