# Quickstart: Screener Risk Tolerance — Verification Protocol

**Feature**: 013-screener-risk-tolerance  
**Date**: 2026-05-17

## Prerequisites

- Dev server running (`uvicorn src.api.main:app --reload`)
- Valid Schwab Bearer token
- Portfolio with at least 2 stock positions ≥ 100 shares, liquid options available

---

## Scenario 1 — Balanced profile matches current server output (regression baseline)

1. Before this feature is deployed, record the current screener JSON:
   ```
   curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/screener/refresh | jq '[.[] | del(.candidates)]' > /tmp/before.json
   ```
2. After implementation, call again with Balanced profile active:
   ```
   curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/screener/refresh | jq '[.[] | del(.candidates)]' > /tmp/after.json
   ```
3. Diff: `diff /tmp/before.json /tmp/after.json`

**Expected**: No diff on any field except `candidates` (which is new and not present in before).

---

## Scenario 2 — `candidates` field is present and populated

```
curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/screener/refresh \
  | jq '.[] | {ticker, candidate_count: (.candidates | length)}'
```

**Expected**: Each ticker with a `recommended` status has `candidate_count ≥ 1`. Tickers with `insufficient_data` have `candidate_count = 0`.

---

## Scenario 3 — Candidates span the full 7–60 DTE window

```
curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/screener/refresh \
  | jq '.[] | .candidates | map(.dte) | {min: min, max: max}'
```

**Expected**: At least one ticker shows candidates with DTE < 30 and at least one with DTE > 45 (if such options exist in the market).

---

## Scenario 4 — Profile toggle appears and switches instantly

1. Open the screener in a browser, note the ranking under Balanced.
2. Click **Conservative** — results should re-rank within one animation frame with no network request (observe in DevTools Network tab: no new XHR/fetch to `/api/screener`).
3. Click **Aggressive** — results re-rank again with no network request.

**Expected**: Network tab shows zero screener API calls after the initial load.

---

## Scenario 5 — Conservative favours OTM options

1. With Conservative active, note the Strike and Delta columns.
2. Switch to Aggressive, note Strike and Delta.

**Expected**: Conservative shows lower delta values (further OTM strikes) ranked first. Aggressive shows higher delta values (nearer-money strikes) ranked first.

---

## Scenario 6 — Aggressive surfaces short-DTE options

1. With Aggressive active, note the Expiry column for the top-ranked ticker.
2. Switch to Balanced, note the same ticker's Expiry.

**Expected**: Aggressive shows a nearer expiry (shorter DTE) than Balanced for the same ticker, if short-DTE candidates exist.

---

## Scenario 7 — Profile persists across navigation

1. Select **Aggressive**.
2. Navigate to Positions tab.
3. Navigate back to Screener.

**Expected**: Aggressive is still selected; results are already re-ranked without a new API call.

---

## Scenario 8 — Fine-grained sliders re-rank without network call (P2)

1. Open the Advanced panel.
2. Move the Safety ↔ Yield slider toward Yield.
3. Observe DevTools Network tab.

**Expected**: No new API call; results re-rank within one animation frame.

---

## Scenario 9 — Full test suite

```
pytest tests/ -v
```

**Expected**: All tests pass including new screener unit and contract tests.

---

## Scenario 10 — Mobile viewport

Open screener at 375px width (Chrome DevTools responsive mode).

**Expected**: Profile toggle is visible and tappable without horizontal scroll. Advanced sliders panel is collapsed by default.
