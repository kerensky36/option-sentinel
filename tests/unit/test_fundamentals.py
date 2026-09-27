"""Unit tests for src/services/fundamentals.py (specs/018 FR-101, FR-104, FR-105, SC-103).

Written RED-first (Principle IV). Reference values are hand-worked or computed
independently here with scipy, per research D-102 – D-104.
"""
from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.stats import norm

from src.data.models import LegFundamentals
from src.services.fundamentals import (
    leg_fundamentals,
    position_fundamentals,
    realised_volatility,
)

R = 0.045
EXPIRY = date(2026, 10, 16)


def approx(x):
    return pytest.approx(x, rel=1e-3, abs=1e-3)


# ---------------------------------------------------------------------------
# T002 — realised_volatility (D-102)
# ---------------------------------------------------------------------------

def _closes_from_returns(returns, start=100.0):
    closes = [start]
    for ret in returns:
        closes.append(closes[-1] * math.exp(ret))
    return closes


def test_realised_volatility_matches_sample_stdev_annualised():
    rng = np.random.default_rng(7)
    returns = rng.normal(0, 0.01, 30)
    closes = _closes_from_returns(returns)
    expected = float(np.std(returns, ddof=1) * math.sqrt(252))
    assert realised_volatility(closes) == pytest.approx(expected, rel=1e-9)


def test_realised_volatility_uses_only_last_window_plus_one_closes():
    rng = np.random.default_rng(11)
    early = rng.normal(0, 0.05, 40)  # very volatile history that must be ignored
    recent = rng.normal(0, 0.01, 30)
    closes = _closes_from_returns(list(early) + list(recent))
    expected = float(np.std(recent, ddof=1) * math.sqrt(252))
    assert realised_volatility(closes) == pytest.approx(expected, rel=1e-9)


def test_realised_volatility_too_few_returns_is_none():
    closes = _closes_from_returns([0.01] * 19)  # 19 returns
    assert realised_volatility(closes) is None


def test_realised_volatility_non_positive_close_is_none():
    closes = _closes_from_returns([0.01, -0.01] * 15)
    closes[5] = 0.0
    assert realised_volatility(closes) is None


# ---------------------------------------------------------------------------
# T003 — leg_fundamentals (D-103)
# ---------------------------------------------------------------------------

def _leg(**kw):
    base = dict(
        underlying_symbol="SPY",
        option_type="put",
        strike=Decimal("95"),
        expiry_date=EXPIRY,
        days_to_expiry=30,
        quantity=-2,
        cost=Decimal("3.00"),
        current_mark=Decimal("1.00"),
        unrealised_pnl=Decimal("400"),
        delta=-0.2,
        gamma=0.03,
        theta=-0.04,
        vega=0.1,
        implied_volatility=0.2,
        underlying_price=Decimal("100"),
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _d2(S, K, T, r, sigma):
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return d1 - sigma * math.sqrt(T)


def test_leg_fundamentals_put_reference_values():
    f = leg_fundamentals(_leg(), 0.16, r=R)
    T = 30 / 365
    assert f.moneyness_pct == approx((95 - 100) / 100 * 100)
    assert f.expected_move == approx(100 * 0.2 * math.sqrt(T))
    assert f.prob_itm == approx(norm.cdf(-_d2(100, 95, T, R, 0.2)))
    assert f.position_delta == approx(-0.2 * -2 * 100)
    assert f.dollar_delta == approx(-0.2 * -2 * 100 * 100)
    assert f.position_gamma == approx(0.03 * -2 * 100)
    assert f.dollar_theta == approx(-0.04 * -2 * 100)
    assert f.dollar_vega == approx(0.1 * -2 * 100)
    assert f.realised_volatility == approx(0.16)
    assert f.iv_rv_ratio == approx(0.2 / 0.16)


def test_leg_fundamentals_call_moneyness_and_prob_itm():
    f = leg_fundamentals(_leg(option_type="call", strike=Decimal("90"), quantity=1, delta=0.8), None, r=R)
    T = 30 / 365
    assert f.moneyness_pct == approx((100 - 90) / 100 * 100)
    assert f.prob_itm == approx(norm.cdf(_d2(100, 90, T, R, 0.2)))


def test_leg_fundamentals_iv_rv_ratio_unavailable_without_rv():
    assert leg_fundamentals(_leg(), None, r=R).iv_rv_ratio is None
    assert leg_fundamentals(_leg(), 0.0, r=R).iv_rv_ratio is None


def test_leg_fundamentals_missing_underlying_price():
    f = leg_fundamentals(_leg(underlying_price=None), 0.16, r=R)
    assert f.moneyness_pct is None
    assert f.expected_move is None
    assert f.prob_itm is None
    assert f.dollar_delta is None
    assert f.position_delta == approx(40.0)  # still available


def test_leg_fundamentals_missing_iv():
    f = leg_fundamentals(_leg(implied_volatility=None), 0.16, r=R)
    assert f.expected_move is None
    assert f.prob_itm is None
    assert f.iv_rv_ratio is None
    assert f.moneyness_pct == approx(-5.0)


def test_leg_fundamentals_missing_greek_is_none_not_zero():
    f = leg_fundamentals(_leg(gamma=None), 0.16, r=R)
    assert f.position_gamma is None


def test_leg_fundamentals_zero_dte_uses_one_day_floor():
    f = leg_fundamentals(_leg(days_to_expiry=0), 0.16, r=R)
    assert f.expected_move == approx(100 * 0.2 * math.sqrt(1 / 365))
    assert f.prob_itm is not None


# ---------------------------------------------------------------------------
# T004 — position_fundamentals (D-104)
# ---------------------------------------------------------------------------

def _pleg(option_type, strike, quantity, cost, mark=1.0, expiry=EXPIRY, greeks=True):
    leg = SimpleNamespace(
        option_type=option_type,
        strike=Decimal(str(strike)),
        expiry_date=expiry,
        quantity=quantity,
        cost=Decimal(str(cost)),
        current_mark=Decimal(str(mark)),
    )
    if greeks:
        leg.fundamentals = LegFundamentals(
            position_delta=10.0 * quantity,
            dollar_delta=1000.0 * quantity,
            position_gamma=1.0 * quantity,
            dollar_theta=-5.0 * quantity,
            dollar_vega=20.0 * quantity,
        )
    else:
        leg.fundamentals = LegFundamentals()
    return leg


def test_long_call_unbounded_profit():
    pf = position_fundamentals([_pleg("call", 100, 1, 5)], Decimal("0"))
    assert pf.single_expiry is True
    assert pf.breakevens == [approx(105)]
    assert pf.max_profit is None and pf.max_profit_unbounded is True
    assert pf.max_loss == approx(500) and pf.max_loss_unbounded is False
    assert pf.pct_max_profit_captured is None


def test_short_put():
    pf = position_fundamentals([_pleg("put", 100, -1, 3)], Decimal("150"))
    assert pf.breakevens == [approx(97)]
    assert pf.max_profit == approx(300)
    assert pf.max_loss == approx(9700)
    assert pf.pct_max_profit_captured == approx(50.0)


def test_bull_call_vertical():
    legs = [_pleg("call", 100, 1, 5), _pleg("call", 110, -1, 2)]
    pf = position_fundamentals(legs, Decimal("350"))
    assert pf.breakevens == [approx(103)]
    assert pf.max_profit == approx(700)
    assert pf.max_loss == approx(300)
    assert pf.max_profit_unbounded is False and pf.max_loss_unbounded is False
    assert pf.pct_max_profit_captured == approx(50.0)


def test_iron_condor():
    legs = [
        _pleg("put", 90, 1, 0.5),
        _pleg("put", 95, -1, 1.5),
        _pleg("call", 105, -1, 1.5),
        _pleg("call", 110, 1, 0.5),
    ]
    pf = position_fundamentals(legs, Decimal("100"))
    assert pf.breakevens == [approx(93), approx(107)]
    assert pf.max_profit == approx(200)
    assert pf.max_loss == approx(300)


def test_short_strangle_unbounded_loss():
    legs = [_pleg("put", 95, -1, 2), _pleg("call", 105, -1, 2)]
    pf = position_fundamentals(legs, Decimal("0"))
    assert pf.breakevens == [approx(91), approx(109)]
    assert pf.max_profit == approx(400)
    assert pf.max_loss is None and pf.max_loss_unbounded is True


def test_calendar_has_no_expiry_payoff_figures():
    legs = [
        _pleg("call", 100, -1, 2, expiry=date(2026, 10, 16)),
        _pleg("call", 100, 1, 4, expiry=date(2026, 11, 20)),
    ]
    pf = position_fundamentals(legs, Decimal("0"))
    assert pf.single_expiry is False
    assert pf.breakevens == []
    assert pf.max_profit is None and pf.max_loss is None
    assert pf.max_profit_unbounded is False and pf.max_loss_unbounded is False
    assert pf.pct_max_profit_captured is None
    # Greeks are still summed for a calendar
    assert pf.net_position_delta == approx(0.0)


def test_net_greeks_sum_and_missing_leg_greek_is_none():
    legs = [_pleg("put", 95, -1, 2), _pleg("call", 105, -1, 2)]
    pf = position_fundamentals(legs, Decimal("0"))
    assert pf.net_position_delta == approx(-20.0)
    assert pf.net_dollar_theta == approx(10.0)

    legs = [_pleg("put", 95, -1, 2), _pleg("call", 105, -1, 2, greeks=False)]
    pf = position_fundamentals(legs, Decimal("0"))
    assert pf.net_position_delta is None
    assert pf.net_dollar_theta is None
    assert pf.theta_pct_of_remaining is None


def test_theta_pct_of_remaining():
    legs = [_pleg("put", 95, -1, 2, mark=0.5)]
    pf = position_fundamentals(legs, Decimal("150"))
    # dollar theta +5/day over |−1×100×0.5| = 50 remaining premium → 10%/day
    assert pf.theta_pct_of_remaining == approx(10.0)


def test_theta_pct_of_remaining_none_when_no_premium_left():
    legs = [_pleg("put", 95, -1, 2, mark=0.0)]
    pf = position_fundamentals(legs, Decimal("200"))
    assert pf.theta_pct_of_remaining is None
