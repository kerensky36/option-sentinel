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

_DEMO_SCREENER_RESULTS = [
    {
        "ticker": "AAPL", "shares": 150, "contracts": 1, "stock_price": 213.50,
        "iv_rank": 42.0, "recommended_strike": 220.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 3.20, "annualised_yield": 0.18, "call_delta": 0.28,
        "days_to_earnings": 45, "composite_score": 78.5,
        "recommendation_status": "recommended", "sort_order": 1, "candidates": [],
    },
    {
        "ticker": "AMD", "shares": 300, "contracts": 2, "stock_price": 158.40,
        "iv_rank": 61.0, "recommended_strike": 175.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 4.80, "annualised_yield": 0.36, "call_delta": 0.32,
        "days_to_earnings": 38, "composite_score": 76.2,
        "recommendation_status": "recommended", "sort_order": 2, "candidates": [],
    },
    {
        "ticker": "NVDA", "shares": 200, "contracts": 1, "stock_price": 127.60,
        "iv_rank": 58.0, "recommended_strike": 135.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 2.45, "annualised_yield": 0.23, "call_delta": 0.30,
        "days_to_earnings": 52, "composite_score": 74.8,
        "recommendation_status": "recommended", "sort_order": 3, "candidates": [],
    },
    {
        "ticker": "META", "shares": 175, "contracts": 1, "stock_price": 592.30,
        "iv_rank": 46.0, "recommended_strike": 620.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 8.20, "annualised_yield": 0.17, "call_delta": 0.29,
        "days_to_earnings": 41, "composite_score": 71.3,
        "recommendation_status": "recommended", "sort_order": 4, "candidates": [],
    },
    {
        "ticker": "SPY", "shares": 250, "contracts": 2, "stock_price": 558.70,
        "iv_rank": 31.0, "recommended_strike": 570.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 3.50, "annualised_yield": 0.15, "call_delta": 0.27,
        "days_to_earnings": None, "composite_score": 64.1,
        "recommendation_status": "recommended", "sort_order": 5, "candidates": [],
    },
    {
        "ticker": "VOO", "shares": 150, "contracts": 1, "stock_price": 504.80,
        "iv_rank": 28.0, "recommended_strike": 510.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 2.90, "annualised_yield": 0.14, "call_delta": 0.25,
        "days_to_earnings": None, "composite_score": 61.0,
        "recommendation_status": "recommended", "sort_order": 6, "candidates": [],
    },
    {
        "ticker": "AMZN", "shares": 120, "contracts": 0, "stock_price": 218.90,
        "iv_rank": 39.0, "recommended_strike": 225.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 3.10, "annualised_yield": 0.17, "call_delta": 0.30,
        "days_to_earnings": 8, "composite_score": 52.4,
        "recommendation_status": "suppressed", "sort_order": 7, "candidates": [],
    },
    {
        "ticker": "MSFT", "shares": 125, "contracts": 0, "stock_price": 421.10,
        "iv_rank": 55.0, "recommended_strike": 430.00, "recommended_expiry": "2025-06-20",
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
