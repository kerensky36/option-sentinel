# Research: Demo Mode Login (014)

## Decision Log

---

### D-001: Demo mode entry mechanism

**Decision**: Backend endpoint `/auth/demo-login` sets `demo_mode=true` in sessionStorage via an inline `<script nonce=…>` page, then redirects to `/`. No Schwab API call, no OAuth redirect.

**Rationale**: Mirrors the existing dev-login pattern; the inline script + CSP nonce approach is already established in `src/auth/router.py`. Keeps demo entry as a single round-trip HTTP request.

**Alternatives considered**:
- Pure client-side demo button that sets sessionStorage directly via a JS click handler in `login.html` → rejected because it requires an inline onclick handler which conflicts with the strict CSP (no `unsafe-inline` for scripts; only nonce-tagged `<script>` blocks are allowed)
- A separate `/demo` HTML page → unnecessary complexity; `/auth/demo-login` is a thin one-time redirect, same as the OAuth callback page

---

### D-002: Demo mode detection signal in sessionStorage

**Decision**: Store `demo_mode = 'true'` as a standalone sessionStorage key. No synthetic Bearer token.

**Rationale**: Using a sentinel Bearer token like `'DEMO'` would be misleading — the token-presence check in `auth.js` (`isAuthenticated()`) would consider demo users "authenticated", which muddies the semantics. A separate `demo_mode` key is semantically clear and decoupled from the token logic.

**Alternatives considered**:
- Synthetic Bearer `'DEMO_TOKEN'` in `schwab_access_token` key → rejected because `fetchWithAuth` currently erases all and redirects to login if no real token is found, and adding token-format checks would complicate `auth.js`
- `demo_account_hash` key only (no `demo_mode` flag) → too implicit; every consumer would need to guess from account hash prefix

---

### D-003: API call interception strategy

**Decision**: Modify `fetchWithAuth()` in `auth.js` to short-circuit when `isDemoMode()` is true, delegating to `demoResponse(url)` from `demo_data.js`. This intercepts all API calls transparently — no changes required in `account_picker.js`, `positions_ui.js`, or `screener_ui.js`.

**Rationale**: `fetchWithAuth` is the single choke point for all authenticated API calls in the app. Intercepting there achieves full isolation with minimal surface area.

**Alternatives considered**:
- Monkey-patch global `fetch` on demo entry → fragile, harder to reason about, hard to test, affects non-auth fetches
- Separate demo-aware wrapper functions in each consumer module → duplicates the check in every file; high maintenance overhead

---

### D-004: Synthetic Response construction

**Decision**: Use `new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } })` to return a real `Response` object from `demoResponse()`. This satisfies any consumer that calls `.ok`, `.json()`, or `.status` on the result.

**Rationale**: `Response` is part of the Fetch API spec, available in all modern browsers. The mock is structurally identical to a real network response, so all existing consumers work unchanged.

**Alternatives considered**:
- Return a plain JS object mimicking the Response interface → would require checking every `.ok` / `.json()` call pattern in consumers to ensure structural compatibility; risks subtle mismatches

---

### D-005: Demo data scope and realism

**Decision**: Two demo accounts:
- **Demo Spreads** (`demo-spreads-0001`): 6 option legs across 3 underlyings (AAPL put spread, SPY iron condor × 2 legs, TSLA call spread) with pre-computed Greeks
- **Demo Equity** (`demo-equity-0002`): 4 equity/ETF positions (AAPL 100, VOO 50, QQQ 30, MSFT 75 shares) with 2 open covered calls (AAPL and VOO CCs) in positions + 3 screener candidates

**Rationale**: Enough variety to showcase the UI without overwhelming a first-time user. Greeks are pre-computed with plausible values to avoid running the BS calculator against fictitious data.

**Alternatives considered**:
- Single demo account with mixed content → doesn't demonstrate the account-switching UX
- More than 2 accounts → adds complexity with diminishing UX value; the spec says "a few different accounts" but two is minimal viable

---

### D-006: Demo DEMO MODE indicator placement

**Decision**: A fixed yellow banner injected via a `<div id="demo-banner">` in `base.html` (hidden by default), shown via a one-line CSS class toggle in a `<script>` block on page load that reads `sessionStorage.getItem('demo_mode')`.

**Rationale**: `base.html` is the shared layout for all pages; placing the banner there guarantees it appears on every screen. The CSS toggle avoids a flash of unstyled content (the element is `hidden` by default and shown only after sessionStorage check).

**Alternatives considered**:
- Template variable `{% if demo_mode %}` → would require the server to know about demo mode, breaking the "no backend changes to API routes" principle
- JS-only appended element on each page → duplicates code; `base.html` is cleaner

---

### D-007: Demo positions data format

**Decision**: Demo positions conform to the exact `PositionView` Pydantic model shape (serialised via `model_dump(mode='json')`). Dates are ISO strings. All Greek fields present (not null). All `*_source` fields set to `"calculated"`.

**Rationale**: `positions_ui.js` expects the same shape it receives from the real API. Matching exactly means zero changes to the rendering layer.

**Demo option spreads positions (DEMO_SPREADS_HASH)**:
```json
[
  { "symbol": "AAPL 250718P00195000", "underlying_symbol": "AAPL", "option_type": "put",
    "strike": 195.00, "expiry_date": "2025-07-18", "quantity": -1, "cost": -3.85,
    "current_mark": -2.40, "unrealised_pnl": 145.00, "days_to_expiry": 57,
    "delta": -0.24, "gamma": 0.041, "theta": -0.09, "vega": 0.17,
    "implied_volatility": 0.30, "delta_source": "calculated", "gamma_source": "calculated",
    "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated" },
  { "symbol": "AAPL 250718P00185000", "underlying_symbol": "AAPL", "option_type": "put",
    "strike": 185.00, "expiry_date": "2025-07-18", "quantity": 1, "cost": 1.95,
    "current_mark": 1.10, "unrealised_pnl": -85.00, "days_to_expiry": 57,
    "delta": 0.13, "gamma": 0.028, "theta": 0.05, "vega": 0.10,
    "implied_volatility": 0.29, "delta_source": "calculated", "gamma_source": "calculated",
    "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated" },
  { "symbol": "SPY 250620P00520000", "underlying_symbol": "SPY", "option_type": "put",
    "strike": 520.00, "expiry_date": "2025-06-20", "quantity": -1, "cost": -4.20,
    "current_mark": -2.80, "unrealised_pnl": 140.00, "days_to_expiry": 29,
    "delta": -0.25, "gamma": 0.038, "theta": -0.12, "vega": 0.18,
    "implied_volatility": 0.20, "delta_source": "calculated", "gamma_source": "calculated",
    "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated" },
  { "symbol": "SPY 250620C00560000", "underlying_symbol": "SPY", "option_type": "call",
    "strike": 560.00, "expiry_date": "2025-06-20", "quantity": -1, "cost": -2.10,
    "current_mark": -1.30, "unrealised_pnl": 80.00, "days_to_expiry": 29,
    "delta": 0.22, "gamma": 0.034, "theta": -0.10, "vega": 0.16,
    "implied_volatility": 0.19, "delta_source": "calculated", "gamma_source": "calculated",
    "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated" },
  { "symbol": "TSLA 250718C00280000", "underlying_symbol": "TSLA", "option_type": "call",
    "strike": 280.00, "expiry_date": "2025-07-18", "quantity": -1, "cost": -6.50,
    "current_mark": -4.10, "unrealised_pnl": 240.00, "days_to_expiry": 57,
    "delta": 0.31, "gamma": 0.052, "theta": -0.15, "vega": 0.28,
    "implied_volatility": 0.48, "delta_source": "calculated", "gamma_source": "calculated",
    "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated" },
  { "symbol": "TSLA 250718C00295000", "underlying_symbol": "TSLA", "option_type": "call",
    "strike": 295.00, "expiry_date": "2025-07-18", "quantity": 1, "cost": 3.80,
    "current_mark": 2.25, "unrealised_pnl": -155.00, "days_to_expiry": 57,
    "delta": -0.19, "gamma": 0.038, "theta": 0.09, "vega": 0.21,
    "implied_volatility": 0.47, "delta_source": "calculated", "gamma_source": "calculated",
    "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated" }
]
```

**Demo equity positions (DEMO_EQUITY_HASH) — covered calls open**:
```json
[
  { "symbol": "AAPL 250620C00220000", "underlying_symbol": "AAPL", "option_type": "call",
    "strike": 220.00, "expiry_date": "2025-06-20", "quantity": -1, "cost": -3.20,
    "current_mark": -2.05, "unrealised_pnl": 115.00, "days_to_expiry": 29,
    "delta": 0.28, "gamma": 0.040, "theta": -0.11, "vega": 0.14,
    "implied_volatility": 0.29, "delta_source": "calculated", "gamma_source": "calculated",
    "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated" },
  { "symbol": "VOO 250620C00510000", "underlying_symbol": "VOO", "option_type": "call",
    "strike": 510.00, "expiry_date": "2025-06-20", "quantity": -1, "cost": -2.90,
    "current_mark": -1.70, "unrealised_pnl": 120.00, "days_to_expiry": 29,
    "delta": 0.25, "gamma": 0.032, "theta": -0.08, "vega": 0.12,
    "implied_volatility": 0.16, "delta_source": "calculated", "gamma_source": "calculated",
    "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated" }
]
```

**Demo screener results (DEMO_EQUITY_HASH)**:
```json
[
  { "ticker": "AAPL", "shares": 100, "contracts": 1, "stock_price": 213.50,
    "iv_rank": 42.0, "recommended_strike": 220.00, "recommended_expiry": "2025-06-20",
    "bid_premium": 3.20, "annualised_yield": 0.18, "call_delta": 0.28,
    "days_to_earnings": 45, "composite_score": 72.5, "recommendation_status": "recommended",
    "sort_order": 1, "candidates": [] },
  { "ticker": "VOO", "shares": 50, "contracts": 1, "stock_price": 504.80,
    "iv_rank": 28.0, "recommended_strike": 510.00, "recommended_expiry": "2025-06-20",
    "bid_premium": 2.90, "annualised_yield": 0.14, "call_delta": 0.25,
    "days_to_earnings": null, "composite_score": 61.0, "recommendation_status": "recommended",
    "sort_order": 2, "candidates": [] },
  { "ticker": "QQQ", "shares": 30, "contracts": 0, "stock_price": 448.20,
    "iv_rank": 18.0, "recommended_strike": null, "recommended_expiry": null,
    "bid_premium": null, "annualised_yield": null, "call_delta": null,
    "days_to_earnings": null, "composite_score": 34.0, "recommendation_status": "suppressed",
    "sort_order": 3, "candidates": [] },
  { "ticker": "MSFT", "shares": 75, "contracts": 0, "stock_price": 421.10,
    "iv_rank": 55.0, "recommended_strike": 430.00, "recommended_expiry": "2025-06-20",
    "bid_premium": 4.10, "annualised_yield": 0.23, "call_delta": 0.31,
    "days_to_earnings": 12, "composite_score": 58.0, "recommendation_status": "suppressed",
    "sort_order": 4, "candidates": [] }
]
```
*MSFT suppressed due to earnings proximity — shows suppression logic in the demo.*
