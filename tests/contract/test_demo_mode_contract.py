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
        "symbol": "AAPL 250620C00220000",
        "underlying_symbol": "AAPL",
        "option_type": "call",
        "strike": "220.00",
        "expiry_date": "2025-06-20",
        "quantity": -1,
        "cost": "-3.20",
        "current_mark": "-2.05",
        "unrealised_pnl": "115.00",
        "days_to_expiry": 29,
        "delta": 0.28, "gamma": 0.040, "theta": -0.11, "vega": 0.14,
        "implied_volatility": 0.29,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated",
        "iv_source": "calculated",
    },
    {
        "symbol": "VOO 250620C00510000",
        "underlying_symbol": "VOO",
        "option_type": "call",
        "strike": "510.00",
        "expiry_date": "2025-06-20",
        "quantity": -1,
        "cost": "-2.90",
        "current_mark": "-1.70",
        "unrealised_pnl": "120.00",
        "days_to_expiry": 29,
        "delta": 0.25, "gamma": 0.032, "theta": -0.08, "vega": 0.12,
        "implied_volatility": 0.16,
        "delta_source": "calculated", "gamma_source": "calculated",
        "theta_source": "calculated", "vega_source": "calculated",
        "iv_source": "calculated",
    },
]

# ---------------------------------------------------------------------------
# Demo screener results — Equities & ETFs account
# Mirror of DEMO_SCREENER_RESULTS in frontend/static/js/demo_data.js
# ---------------------------------------------------------------------------

_DEMO_SCREENER_RESULTS = [
    {
        "ticker": "AAPL", "shares": 100, "contracts": 1, "stock_price": 213.50,
        "iv_rank": 42.0, "recommended_strike": 220.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 3.20, "annualised_yield": 0.18, "call_delta": 0.28,
        "days_to_earnings": 45, "composite_score": 72.5,
        "recommendation_status": "recommended", "sort_order": 1, "candidates": [],
    },
    {
        "ticker": "VOO", "shares": 50, "contracts": 1, "stock_price": 504.80,
        "iv_rank": 28.0, "recommended_strike": 510.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 2.90, "annualised_yield": 0.14, "call_delta": 0.25,
        "days_to_earnings": None, "composite_score": 61.0,
        "recommendation_status": "recommended", "sort_order": 2, "candidates": [],
    },
    {
        "ticker": "QQQ", "shares": 30, "contracts": 0, "stock_price": 448.20,
        "iv_rank": 18.0, "recommended_strike": None, "recommended_expiry": None,
        "bid_premium": None, "annualised_yield": None, "call_delta": None,
        "days_to_earnings": None, "composite_score": 34.0,
        "recommendation_status": "suppressed", "sort_order": 3, "candidates": [],
    },
    {
        "ticker": "MSFT", "shares": 75, "contracts": 0, "stock_price": 421.10,
        "iv_rank": 55.0, "recommended_strike": 430.00, "recommended_expiry": "2025-06-20",
        "bid_premium": 4.10, "annualised_yield": 0.23, "call_delta": 0.31,
        "days_to_earnings": 12, "composite_score": 58.0,
        "recommendation_status": "suppressed", "sort_order": 4, "candidates": [],
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
        assert len(_DEMO_POSITIONS_EQUITY) == 2

    @pytest.mark.parametrize("raw", _DEMO_POSITIONS_EQUITY)
    def test_each_entry_parses_as_position_view(self, raw):
        pos = PositionView(**raw)
        assert pos.underlying_symbol in ("AAPL", "VOO")
        assert pos.option_type == "call"

    @pytest.mark.parametrize("raw", _DEMO_POSITIONS_EQUITY)
    def test_no_null_greeks(self, raw):
        pos = PositionView(**raw)
        assert pos.delta is not None
        assert pos.theta is not None


class TestDemoScreenerResultsSchema:
    def test_count(self):
        assert len(_DEMO_SCREENER_RESULTS) == 4

    @pytest.mark.parametrize("raw", _DEMO_SCREENER_RESULTS)
    def test_each_entry_parses_as_screener_result(self, raw):
        result = ScreenerResultView(**raw)
        assert result.ticker in ("AAPL", "VOO", "QQQ", "MSFT")

    def test_two_recommended(self):
        results = [ScreenerResultView(**r) for r in _DEMO_SCREENER_RESULTS]
        recommended = [r for r in results if r.recommendation_status == "recommended"]
        assert len(recommended) == 2

    def test_two_suppressed(self):
        results = [ScreenerResultView(**r) for r in _DEMO_SCREENER_RESULTS]
        suppressed = [r for r in results if r.recommendation_status == "suppressed"]
        assert len(suppressed) == 2

    def test_msft_suppressed_has_near_earnings(self):
        msft = next(ScreenerResultView(**r) for r in _DEMO_SCREENER_RESULTS if r["ticker"] == "MSFT")
        assert msft.days_to_earnings is not None
        assert msft.days_to_earnings <= 14
