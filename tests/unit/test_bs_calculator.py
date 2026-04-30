import math
import pytest
from src.services.bs_calculator import bs_greeks, implied_volatility


def test_call_delta_atm():
    g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="call")
    assert 0.55 < g.delta < 0.65


def test_put_delta_atm():
    g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="put")
    assert -0.50 < g.delta < -0.35


def test_call_put_delta_sum():
    # call delta - put delta should equal 1 (put-call parity for delta)
    call = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="call")
    put = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="put")
    assert abs(call.delta - put.delta - 1.0) < 1e-6


def test_gamma_positive():
    g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="call")
    assert g.gamma > 0


def test_call_put_gamma_equal():
    call = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="call")
    put = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="put")
    assert abs(call.gamma - put.gamma) < 1e-10


def test_theta_negative():
    # theta should be negative (time decay costs the holder)
    call = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="call")
    assert call.theta < 0


def test_vega_positive():
    g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="call")
    assert g.vega > 0


def test_deep_itm_call_delta_near_one():
    g = bs_greeks(S=200, K=100, T=1.0, r=0.05, sigma=0.20, option_type="call")
    assert g.delta > 0.95


def test_deep_otm_call_delta_near_zero():
    g = bs_greeks(S=50, K=200, T=0.1, r=0.05, sigma=0.20, option_type="call")
    assert g.delta < 0.01


def test_zero_dte_returns_nan():
    g = bs_greeks(S=100, K=100, T=0, r=0.05, sigma=0.20, option_type="call")
    assert math.isnan(g.delta)


def test_zero_sigma_returns_nan():
    g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0, option_type="call")
    assert math.isnan(g.delta)


def test_implied_volatility_round_trip():
    sigma = 0.25
    g = bs_greeks(S=520, K=520, T=30 / 365, r=0.045, sigma=sigma, option_type="call")
    from src.services.bs_calculator import _bs_price
    price = _bs_price(520, 520, 30 / 365, 0.045, sigma, "call")
    iv = implied_volatility(S=520, K=520, T=30 / 365, r=0.045, option_price=price, option_type="call")
    assert iv is not None
    assert abs(iv - sigma) < 1e-4


def test_implied_volatility_put_round_trip():
    sigma = 0.30
    from src.services.bs_calculator import _bs_price
    price = _bs_price(100, 105, 60 / 365, 0.045, sigma, "put")
    iv = implied_volatility(S=100, K=105, T=60 / 365, r=0.045, option_price=price, option_type="put")
    assert iv is not None
    assert abs(iv - sigma) < 1e-4


def test_implied_volatility_zero_price_returns_none():
    iv = implied_volatility(S=100, K=100, T=1.0, r=0.05, option_price=0, option_type="call")
    assert iv is None


def test_implied_volatility_zero_dte_returns_none():
    iv = implied_volatility(S=100, K=100, T=0, r=0.05, option_price=5.0, option_type="call")
    assert iv is None
