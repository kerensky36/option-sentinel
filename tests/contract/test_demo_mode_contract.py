"""Contract tests: demo data payloads match PositionView and ScreenerResultView schemas.

These tests validate that the static demo data embedded in demo_data.js is
schema-compatible with the Pydantic models used by the real API, ensuring the
positions UI and screener UI render correctly in demo mode.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.data.models import PositionView, ScreenerResultView

# ---------------------------------------------------------------------------
# Demo positions — Options Spreads account (DEMO_SPREADS_HASH)
# Mirror of DEMO_POSITIONS_SPREADS in frontend/static/js/demo_data.js
# ---------------------------------------------------------------------------

_DEMO_POSITIONS_SPREADS = [
    {
        "symbol": "AAPL 250718P00195000",
        "underlying_symbol": "AAPL",
        "option_type": "put",
        "strike": "195.00",
        "expiry_date": "2025-07-18",
        "quantity": -1,
        "cost": "-3.85",
        "current_mark": "-2.40",
        "unrealised_pnl": "145.00",
        "days_to_expiry": 57,
        "delta": -0.24, "gamma": 0.041, "theta": -0.09, "vega": 0.17,
        "implied_volatility": 0.30,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated",
        "iv_source": "calculated",
    },
    {
        "symbol": "AAPL 250718P00185000",
        "underlying_symbol": "AAPL",
        "option_type": "put",
        "strike": "185.00",
        "expiry_date": "2025-07-18",
        "quantity": 1,
        "cost": "1.95",
        "current_mark": "1.10",
        "unrealised_pnl": "-85.00",
        "days_to_expiry": 57,
        "delta": 0.13, "gamma": 0.028, "theta": 0.05, "vega": 0.10,
        "implied_volatility": 0.29,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated",
        "iv_source": "calculated",
    },
    {
        "symbol": "SPY 250620P00520000",
        "underlying_symbol": "SPY",
        "option_type": "put",
        "strike": "520.00",
        "expiry_date": "2025-06-20",
        "quantity": -1,
        "cost": "-4.20",
        "current_mark": "-2.80",
        "unrealised_pnl": "140.00",
        "days_to_expiry": 29,
        "delta": -0.25, "gamma": 0.038, "theta": -0.12, "vega": 0.18,
        "implied_volatility": 0.20,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated",
        "iv_source": "calculated",
    },
    {
        "symbol": "SPY 250620C00560000",
        "underlying_symbol": "SPY",
        "option_type": "call",
        "strike": "560.00",
        "expiry_date": "2025-06-20",
        "quantity": -1,
        "cost": "-2.10",
        "current_mark": "-1.30",
        "unrealised_pnl": "80.00",
        "days_to_expiry": 29,
        "delta": 0.22, "gamma": 0.034, "theta": -0.10, "vega": 0.16,
        "implied_volatility": 0.19,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated",
        "iv_source": "calculated",
    },
    {
        "symbol": "TSLA 250718C00280000",
        "underlying_symbol": "TSLA",
        "option_type": "call",
        "strike": "280.00",
        "expiry_date": "2025-07-18",
        "quantity": -1,
        "cost": "-6.50",
        "current_mark": "-4.10",
        "unrealised_pnl": "240.00",
        "days_to_expiry": 57,
        "delta": 0.31, "gamma": 0.052, "theta": -0.15, "vega": 0.28,
        "implied_volatility": 0.48,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated",
        "iv_source": "calculated",
    },
    {
        "symbol": "TSLA 250718C00295000",
        "underlying_symbol": "TSLA",
        "option_type": "call",
        "strike": "295.00",
        "expiry_date": "2025-07-18",
        "quantity": 1,
        "cost": "3.80",
        "current_mark": "2.25",
        "unrealised_pnl": "-155.00",
        "days_to_expiry": 57,
        "delta": -0.19, "gamma": 0.038, "theta": 0.09, "vega": 0.21,
        "implied_volatility": 0.47,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated",
        "iv_source": "calculated",
    },
]

# ---------------------------------------------------------------------------
# Demo positions — Equities & ETFs account (DEMO_EQUITY_HASH)
# Mirror of DEMO_POSITIONS_EQUITY in frontend/static/js/demo_data.js
# ---------------------------------------------------------------------------

_DEMO_POSITIONS_EQUITY = [
    {
        "symbol": "AAPL 250620C00220000", "underlying_symbol": "AAPL", "option_type": "call",
        "strike": "220.00", "expiry_date": "2025-06-20", "quantity": -1,
        "cost": "-3.20", "current_mark": "-2.05", "unrealised_pnl": "115.00", "days_to_expiry": 29,
        "delta": 0.28, "gamma": 0.040, "theta": -0.11, "vega": 0.14, "implied_volatility": 0.29,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated",
    },
    {
        "symbol": "NVDA 250620C00135000", "underlying_symbol": "NVDA", "option_type": "call",
        "strike": "135.00", "expiry_date": "2025-06-20", "quantity": -1,
        "cost": "-2.45", "current_mark": "-1.60", "unrealised_pnl": "85.00", "days_to_expiry": 29,
        "delta": 0.30, "gamma": 0.058, "theta": -0.14, "vega": 0.19, "implied_volatility": 0.42,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated",
    },
    {
        "symbol": "VOO 250620C00510000", "underlying_symbol": "VOO", "option_type": "call",
        "strike": "510.00", "expiry_date": "2025-06-20", "quantity": -1,
        "cost": "-2.90", "current_mark": "-1.70", "unrealised_pnl": "120.00", "days_to_expiry": 29,
        "delta": 0.25, "gamma": 0.032, "theta": -0.08, "vega": 0.12, "implied_volatility": 0.16,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated",
    },
    {
        "symbol": "SPY 250620C00570000", "underlying_symbol": "SPY", "option_type": "call",
        "strike": "570.00", "expiry_date": "2025-06-20", "quantity": -2,
        "cost": "-3.50", "current_mark": "-2.20", "unrealised_pnl": "260.00", "days_to_expiry": 29,
        "delta": 0.27, "gamma": 0.035, "theta": -0.10, "vega": 0.16, "implied_volatility": 0.18,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated",
    },
    {
        "symbol": "AMD 250620C00175000", "underlying_symbol": "AMD", "option_type": "call",
        "strike": "175.00", "expiry_date": "2025-06-20", "quantity": -2,
        "cost": "-4.80", "current_mark": "-3.10", "unrealised_pnl": "340.00", "days_to_expiry": 29,
        "delta": 0.32, "gamma": 0.062, "theta": -0.16, "vega": 0.22, "implied_volatility": 0.51,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated",
    },
    {
        "symbol": "META 250620C00620000", "underlying_symbol": "META", "option_type": "call",
        "strike": "620.00", "expiry_date": "2025-06-20", "quantity": -1,
        "cost": "-8.20", "current_mark": "-5.40", "unrealised_pnl": "280.00", "days_to_expiry": 29,
        "delta": 0.29, "gamma": 0.028, "theta": -0.13, "vega": 0.24, "implied_volatility": 0.34,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated", "iv_source": "calculated",
    },
]

# ---------------------------------------------------------------------------
# Demo screener results — Equities & ETFs account
# Mirror of DEMO_SCREENER_RESULTS in frontend/static/js/demo_data.js
# ---------------------------------------------------------------------------

def _make_candidates(rows):
    return [{"dte": r[0], "delta": r[1], "bid": r[2], "strike": r[3], "expiry": r[4], "open_interest": r[5]} for r in rows]

_AAPL_CANDIDATES = _make_candidates([
    (21, 0.31, 2.60, 220.0, "2026-06-12", 2400), (21, 0.20, 1.90, 225.0, "2026-06-12", 1800),
    (35, 0.27, 3.30, 220.0, "2026-06-26", 1900), (35, 0.18, 2.50, 225.0, "2026-06-26", 1400),
    (56, 0.24, 3.90, 220.0, "2026-07-17", 1200), (56, 0.15, 2.80, 225.0, "2026-07-17", 900),
])
_AMD_CANDIDATES = _make_candidates([
    (21, 0.34, 3.40, 163.0, "2026-06-12", 3100), (21, 0.22, 2.20, 168.0, "2026-06-12", 2200),
    (35, 0.28, 4.90, 163.0, "2026-06-26", 2000), (35, 0.17, 3.30, 168.0, "2026-06-26", 1500),
    (56, 0.25, 5.80, 163.0, "2026-07-17", 1400), (56, 0.14, 3.80, 170.0, "2026-07-17", 900),
])
_NVDA_CANDIDATES = _make_candidates([
    (21, 0.33, 2.20, 132.0, "2026-06-12", 4200), (21, 0.21, 1.60, 135.0, "2026-06-12", 3100),
    (35, 0.27, 2.50, 132.0, "2026-06-26", 3000), (35, 0.17, 1.80, 135.0, "2026-06-26", 2100),
    (56, 0.23, 2.90, 132.0, "2026-07-17", 2000), (56, 0.14, 2.00, 137.0, "2026-07-17", 1200),
])
_META_CANDIDATES = _make_candidates([
    (21, 0.32, 7.80, 610.0, "2026-06-12", 1100), (21, 0.22, 5.60, 620.0, "2026-06-12", 800),
    (35, 0.26, 8.40, 610.0, "2026-06-26", 900),  (35, 0.17, 6.20, 625.0, "2026-06-26", 650),
    (56, 0.22, 9.60, 615.0, "2026-07-17", 700),  (56, 0.14, 7.10, 630.0, "2026-07-17", 500),
])
_SPY_CANDIDATES = _make_candidates([
    (21, 0.30, 2.90, 568.0, "2026-06-12", 9200), (21, 0.20, 1.90, 574.0, "2026-06-12", 7100),
    (35, 0.25, 3.60, 568.0, "2026-06-26", 6500), (35, 0.16, 2.50, 574.0, "2026-06-26", 5000),
    (56, 0.22, 4.20, 568.0, "2026-07-17", 4500), (56, 0.14, 3.00, 576.0, "2026-07-17", 3200),
])
_VOO_CANDIDATES = _make_candidates([
    (21, 0.28, 2.30, 514.0, "2026-06-12", 900), (21, 0.18, 1.60, 520.0, "2026-06-12", 680),
    (35, 0.23, 3.00, 514.0, "2026-06-26", 720), (35, 0.15, 2.10, 520.0, "2026-06-26", 540),
    (56, 0.20, 3.50, 514.0, "2026-07-17", 480), (56, 0.13, 2.40, 522.0, "2026-07-17", 350),
])

_DEMO_SCREENER_RESULTS = [
    {
        "ticker": "AAPL", "shares": 150, "contracts": 1, "stock_price": 213.50,
        "iv_rank": 42.0, "recommended_strike": 220.00, "recommended_expiry": "2026-06-26",
        "bid_premium": 3.30, "annualised_yield": 0.18, "call_delta": 0.27,
        "days_to_earnings": 45, "composite_score": 78.5,
        "recommendation_status": "recommended", "sort_order": 1, "candidates": _AAPL_CANDIDATES,
    },
    {
        "ticker": "AMD", "shares": 300, "contracts": 2, "stock_price": 158.40,
        "iv_rank": 61.0, "recommended_strike": 163.00, "recommended_expiry": "2026-06-26",
        "bid_premium": 4.90, "annualised_yield": 0.34, "call_delta": 0.28,
        "days_to_earnings": 38, "composite_score": 76.2,
        "recommendation_status": "recommended", "sort_order": 2, "candidates": _AMD_CANDIDATES,
    },
    {
        "ticker": "NVDA", "shares": 200, "contracts": 1, "stock_price": 127.60,
        "iv_rank": 58.0, "recommended_strike": 132.00, "recommended_expiry": "2026-06-26",
        "bid_premium": 2.50, "annualised_yield": 0.21, "call_delta": 0.27,
        "days_to_earnings": 52, "composite_score": 74.8,
        "recommendation_status": "recommended", "sort_order": 3, "candidates": _NVDA_CANDIDATES,
    },
    {
        "ticker": "META", "shares": 175, "contracts": 1, "stock_price": 592.30,
        "iv_rank": 46.0, "recommended_strike": 610.00, "recommended_expiry": "2026-06-26",
        "bid_premium": 8.40, "annualised_yield": 0.17, "call_delta": 0.26,
        "days_to_earnings": 41, "composite_score": 71.3,
        "recommendation_status": "recommended", "sort_order": 4, "candidates": _META_CANDIDATES,
    },
    {
        "ticker": "SPY", "shares": 250, "contracts": 2, "stock_price": 558.70,
        "iv_rank": 31.0, "recommended_strike": 568.00, "recommended_expiry": "2026-06-26",
        "bid_premium": 3.60, "annualised_yield": 0.14, "call_delta": 0.25,
        "days_to_earnings": None, "composite_score": 64.1,
        "recommendation_status": "recommended", "sort_order": 5, "candidates": _SPY_CANDIDATES,
    },
    {
        "ticker": "VOO", "shares": 150, "contracts": 1, "stock_price": 504.80,
        "iv_rank": 28.0, "recommended_strike": 514.00, "recommended_expiry": "2026-06-26",
        "bid_premium": 3.00, "annualised_yield": 0.13, "call_delta": 0.23,
        "days_to_earnings": None, "composite_score": 61.0,
        "recommendation_status": "recommended", "sort_order": 6, "candidates": _VOO_CANDIDATES,
    },
    {
        "ticker": "AMZN", "shares": 120, "contracts": 0, "stock_price": 218.90,
        "iv_rank": 39.0, "recommended_strike": 225.00, "recommended_expiry": "2026-06-26",
        "bid_premium": 3.10, "annualised_yield": 0.17, "call_delta": 0.30,
        "days_to_earnings": 8, "composite_score": 52.4,
        "recommendation_status": "suppressed", "sort_order": 7, "candidates": [],
    },
    {
        "ticker": "MSFT", "shares": 125, "contracts": 0, "stock_price": 421.10,
        "iv_rank": 55.0, "recommended_strike": 430.00, "recommended_expiry": "2026-06-26",
        "bid_premium": 4.10, "annualised_yield": 0.12, "call_delta": 0.31,
        "days_to_earnings": 12, "composite_score": 49.8,
        "recommendation_status": "suppressed", "sort_order": 8, "candidates": [],
    },
    {
        "ticker": "QQQ", "shares": 200, "contracts": 0, "stock_price": 448.20,
        "iv_rank": 18.0, "recommended_strike": None, "recommended_expiry": None,
        "bid_premium": None, "annualised_yield": None, "call_delta": None,
        "days_to_earnings": None, "composite_score": 34.0,
        "recommendation_status": "suppressed", "sort_order": 9, "candidates": [],
    },
    {
        "ticker": "GOOGL", "shares": 110, "contracts": 0, "stock_price": 174.50,
        "iv_rank": 22.0, "recommended_strike": None, "recommended_expiry": None,
        "bid_premium": None, "annualised_yield": None, "call_delta": None,
        "days_to_earnings": None, "composite_score": 29.5,
        "recommendation_status": "suppressed", "sort_order": 10, "candidates": [],
    },
]


class TestDemoPositionsSpreadsSchema:
    def test_count(self):
        assert len(_DEMO_POSITIONS_SPREADS) == 6

    @pytest.mark.parametrize("raw", _DEMO_POSITIONS_SPREADS)
    def test_each_entry_parses_as_position_view(self, raw):
        pos = PositionView(**raw)
        assert pos.symbol
        assert pos.underlying_symbol
        assert pos.option_type in ("call", "put")

    @pytest.mark.parametrize("raw", _DEMO_POSITIONS_SPREADS)
    def test_no_null_greeks(self, raw):
        pos = PositionView(**raw)
        assert pos.delta is not None
        assert pos.gamma is not None
        assert pos.theta is not None
        assert pos.vega is not None
        assert pos.implied_volatility is not None

    @pytest.mark.parametrize("raw", _DEMO_POSITIONS_SPREADS)
    def test_greek_sources_are_calculated(self, raw):
        pos = PositionView(**raw)
        assert pos.delta_source == "calculated"
        assert pos.gamma_source == "calculated"
        assert pos.theta_source == "calculated"
        assert pos.vega_source == "calculated"
        assert pos.iv_source == "calculated"


class TestDemoPositionsEquitySchema:
    def test_count(self):
        assert len(_DEMO_POSITIONS_EQUITY) == 6

    @pytest.mark.parametrize("raw", _DEMO_POSITIONS_EQUITY)
    def test_each_entry_parses_as_position_view(self, raw):
        pos = PositionView(**raw)
        assert pos.underlying_symbol in ("AAPL", "NVDA", "VOO", "SPY", "AMD", "META")
        assert pos.option_type == "call"

    @pytest.mark.parametrize("raw", _DEMO_POSITIONS_EQUITY)
    def test_no_null_greeks(self, raw):
        pos = PositionView(**raw)
        assert pos.delta is not None
        assert pos.theta is not None


class TestDemoScreenerResultsSchema:
    def test_count(self):
        assert len(_DEMO_SCREENER_RESULTS) == 10

    @pytest.mark.parametrize("raw", _DEMO_SCREENER_RESULTS)
    def test_each_entry_parses_as_screener_result(self, raw):
        result = ScreenerResultView(**raw)
        assert result.ticker in ("AAPL", "AMD", "NVDA", "META", "SPY", "VOO", "AMZN", "MSFT", "QQQ", "GOOGL")

    def test_all_shares_over_100(self):
        for r in _DEMO_SCREENER_RESULTS:
            assert r["shares"] > 100, f"{r['ticker']} has shares={r['shares']}, expected >100"

    def test_six_recommended(self):
        results = [ScreenerResultView(**r) for r in _DEMO_SCREENER_RESULTS]
        recommended = [r for r in results if r.recommendation_status == "recommended"]
        assert len(recommended) == 6

    def test_four_suppressed(self):
        results = [ScreenerResultView(**r) for r in _DEMO_SCREENER_RESULTS]
        suppressed = [r for r in results if r.recommendation_status == "suppressed"]
        assert len(suppressed) == 4

    def test_near_earnings_tickers_suppressed(self):
        results = {ScreenerResultView(**r).ticker: ScreenerResultView(**r) for r in _DEMO_SCREENER_RESULTS}
        assert results["AMZN"].days_to_earnings <= 14
        assert results["MSFT"].days_to_earnings <= 14

    def test_recommended_tickers_have_candidates(self):
        for r in _DEMO_SCREENER_RESULTS:
            if r["recommendation_status"] == "recommended":
                assert len(r["candidates"]) > 0, f"{r['ticker']} recommended but has no candidates"

    def test_candidates_cover_all_dte_buckets(self):
        # Each risk profile needs at least one candidate in its DTE window:
        #   aggressive: 7–30, balanced: 30–45, conservative: 30–60
        for r in _DEMO_SCREENER_RESULTS:
            if r["recommendation_status"] != "recommended":
                continue
            dtes = [c["dte"] for c in r["candidates"]]
            assert any(7 <= d <= 30 for d in dtes), f"{r['ticker']} missing aggressive-bucket candidate (7–30 DTE)"
            assert any(30 <= d <= 45 for d in dtes), f"{r['ticker']} missing balanced-bucket candidate (30–45 DTE)"
            assert any(30 <= d <= 60 for d in dtes), f"{r['ticker']} missing conservative-bucket candidate (30–60 DTE)"

    def test_candidate_fields_present(self):
        required = {"dte", "delta", "bid", "strike", "expiry", "open_interest"}
        for r in _DEMO_SCREENER_RESULTS:
            for c in r["candidates"]:
                missing = required - c.keys()
                assert not missing, f"{r['ticker']} candidate missing fields: {missing}"
