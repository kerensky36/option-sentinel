# Quickstart: Fundamentals-First Quorum

GCP / Vertex AI setup is unchanged — see `specs/017-macro-quorum-agents/quickstart.md`.

## Automated checks

```bash
pytest tests/unit/test_fundamentals.py tests/unit/test_bs_calculator.py \
       tests/unit/test_schwab_client.py tests/unit/test_covered_call_screener.py \
       tests/unit/test_news_feeds.py tests/unit/test_quorum_agents.py \
       tests/unit/test_quorum_tally.py \
       tests/contract/test_quorum_api.py tests/contract/test_positions_api.py \
       tests/contract/test_screener_api.py tests/contract/test_data_use_page.py -q
pytest -q   # full suite must stay green
```

Expected: all pass. Key assertions per requirement:

| Check | Proves |
|---|---|
| `test_fundamentals.py` reference cases (long call, short put, vertical, iron condor, calendar, dte 0, no price) | FR-101, FR-104, FR-105, SC-103 |
| placeholder / zero Greek fixtures | FR-106, FR-107, SC-104 |
| chain request kwargs include `from_date`/`to_date`/`strike` | FR-108 |
| quorum route test asserts no `get_account`/`get_option_chain`/`get_price_history*` call | FR-110, SC-102 |
| extra field / out-of-range / stale / bad token cases never reach the fake model; 422 body has no submitted values | FR-111, SC-106 |
| seat 1–4 prompts contain no headline titles or brief; seat 5 prompt does | FR-114, FR-117, SC-105 |
| seats 1–4 start before a slow fake research agent finishes | FR-119 |
| `select_headlines` quota / 48 h / cap cases | FR-116 |
| privacy scan of every fake-model request (no account hash, token, IP) | FR-113, SC-107 |

## Browser verification (live Schwab + Vertex AI)

1. **Refresh positions** — Network tab: `/api/positions/refresh` items carry `as_of` and
   `fundamentals` (realised vol, IV/RV, moneyness, expected move, prob ITM, dollar Greeks).
2. **Quorum on a single leg** — Request body contains `as_of` and `legs[]` with no
   `account_hash` and no OCC `symbol`. Panel shows "Data as of HH:MM".
3. **Lenses** — Cards read Greeks & Exposure, Volatility & Pricing, Time Decay & P&L,
   Strike & Assignment, Macro & News Overlay. Cards 1–4 cite figures; card 5 cites news.
4. **Headlines** — ≤ 12 listed, none older than 48 h, underlying's own news first when present.
5. **Spread** — Quorum on a spread summary row sends every leg; result's breakevens and
   max profit match the payoff graph at expiry.
6. **Stale** — Wait > 15 min without refreshing (or edit the cached `as_of` in DevTools),
   click Quorum → "Position data is more than 15 minutes old — refresh positions".
7. **Bad token** — Replace the sessionStorage token with junk, click Quorum → 401 handling
   (redirect to login) and no quorum run.
8. **Speed** — Compare time-to-verdict with the pre-018 build on the same position: expect
   several seconds faster (SC-101).
9. **Screener** — "IV/RV" column shows e.g. `1.42×`; rows sort by the new score.
10. **Demo mode** — Canned quorum uses the new lenses and shows "Data as of"; no server call.
11. **Data use page** — Vertex AI row lists the new fundamentals fields; a row covers the
    price-history fetch for realised volatility (FR-120).
