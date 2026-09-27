"""Unit tests for build_greeks placeholder handling (specs/018 FR-106, FR-107, SC-104)."""
from __future__ import annotations

import math

import pytest

from src.services.greeks_service import build_greeks

_GOOD = {"delta": -0.3, "gamma": 0.02, "theta": -0.05, "vega": 0.15, "implied_volatility": 25.3, "underlying_price": 100.0}


def _build(**overrides):
    raw = {**_GOOD, **overrides}
    return build_greeks(strike=95.0, option_type="put", days_to_expiry=30, raw=raw)


@pytest.mark.parametrize("field", ["delta", "gamma", "theta", "vega"])
@pytest.mark.parametrize("bad", [-999.0, float("nan"), float("inf"), float("-inf")])
def test_placeholder_greek_is_recalculated(field, bad):
    g = _build(**{field: bad})
    assert g[f"{field}_source"] == "calculated"
    assert g[field] is not None and math.isfinite(g[field])
    assert g[field] != bad


@pytest.mark.parametrize("field,bad", [("delta", 1.5), ("delta", -1.01), ("gamma", -0.1), ("gamma", 11.0),
                                       ("theta", 20_000.0), ("vega", -1.0), ("vega", 20_000.0)])
def test_out_of_range_greek_is_recalculated(field, bad):
    g = _build(**{field: bad})
    assert g[f"{field}_source"] == "calculated"


def test_zero_greek_is_kept_as_api_and_no_fallback():
    g = _build(gamma=0.0)
    assert g["gamma"] == 0.0
    assert g["gamma_source"] == "api"
    assert all(g[f"{k}_source"] == "api" for k in ("delta", "theta", "vega"))


def test_iv_percent_converted():
    assert _build()["implied_volatility"] == pytest.approx(0.253)


@pytest.mark.parametrize("bad_iv", [-999.0, 0.0, float("nan"), 5000.0])
def test_placeholder_iv_is_missing_and_fallback_uses_default_sigma(bad_iv):
    g = _build(implied_volatility=bad_iv, delta=None)
    assert g["implied_volatility"] is None
    assert g["iv_source"] is None
    assert g["delta_source"] == "calculated"
    assert math.isfinite(g["delta"])


def test_non_numeric_value_is_missing():
    g = _build(delta="NaN")
    assert g["delta_source"] == "calculated"
