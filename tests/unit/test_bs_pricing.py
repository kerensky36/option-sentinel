"""Unit tests for the T+0 payoff overlay's theoretical pricing —
mirrors frontend/static/js/payoff_theoretical.js.

These tests define the checkpoint/theoretical-pricing contract and must FAIL
before payoff_theoretical.js is implemented, then pass once the JS mirrors
this logic. Unlike test_payoff_math.py (which wrote its own reference
formula), the pricing formula here already exists in production
(bs_calculator.py::_bs_price) — that IS the authoritative reference the JS
must match, so it is imported directly rather than re-derived.
"""
from __future__ import annotations

import pytest

from src.services.bs_calculator import _bs_price
from tests.unit.test_payoff_math import combined_payoff


# ---------------------------------------------------------------------------
# Python reference implementation for the parts with no prior Python source
# (mirrors payoff_theoretical.js exactly)
# ---------------------------------------------------------------------------

RISK_FREE_RATE = 0.045

CHECKPOINTS = [
    {"id": "today", "label": "Today", "offset_days": 0},
    {"id": "plus1wk", "label": "+1 week", "offset_days": 7},
    {"id": "plus2wk", "label": "+2 weeks", "offset_days": 14},
    {"id": "expiration", "label": "Expiration", "offset_days": None},
]


def available_checkpoints(days_to_expiry: int) -> list[dict]:
    """A checkpoint is available if offset_days is None (Expiration) or
    strictly less than days_to_expiry — see research.md D-005."""
    return [
        c for c in CHECKPOINTS
        if c["offset_days"] is None or c["offset_days"] < days_to_expiry
    ]


def is_eligible_for_overlay(legs: list[dict]) -> bool:
    """False if any leg lacks usable IV, or if days_to_expiry <= 0."""
    if not legs:
        return False
    days_to_expiry = legs[0]["days_to_expiry"]
    if days_to_expiry <= 0:
        return False
    return all(leg.get("implied_volatility") and leg["implied_volatility"] > 0 for leg in legs)


def theoretical_payoff_per_share(leg: dict, price: float, days_to_expiry: float) -> float:
    """Parallel to leg_payoff_per_share, substituting bs_price for intrinsic value."""
    T = days_to_expiry / 365
    theoretical = _bs_price(price, leg["strike"], T, RISK_FREE_RATE, leg["implied_volatility"], leg["option_type"])
    sign = 1 if leg["quantity"] > 0 else -1
    return sign * theoretical - leg["cost"]


def combined_theoretical_payoff(legs: list[dict], price: float, days_to_expiry: float) -> float:
    return sum(theoretical_payoff_per_share(leg, price, days_to_expiry) for leg in legs)


def compute_checkpoint_pnl(legs: list[dict], checkpoint: dict, price: float) -> float:
    """Mirrors computeCheckpointCurve's per-point dispatch: null offset routes
    through the existing intrinsic formula; everything else through
    theoretical pricing at the checkpoint's implied days_to_expiry."""
    if checkpoint["offset_days"] is None:
        return combined_payoff(legs, price)
    days_to_expiry = legs[0]["days_to_expiry"] - checkpoint["offset_days"]
    return combined_theoretical_payoff(legs, price, days_to_expiry)


# ---------------------------------------------------------------------------
# bsPrice — must match bs_calculator.py::_bs_price exactly (it's the same
# function; this documents the contract values from
# contracts/payoff-theoretical-contract.md)
# ---------------------------------------------------------------------------

class TestBsPriceContractValues:
    def test_short_put_57dte(self):
        price = _bs_price(190.0, 195.0, 57 / 365, 0.045, 0.30, "put")
        assert abs(price - 10.9995) < 0.001

    def test_call_57dte(self):
        price = _bs_price(288.0, 280.0, 57 / 365, 0.045, 0.48, "call")
        assert abs(price - 26.7313) < 0.001

    def test_put_converges_to_intrinsic_near_expiry(self):
        # T -> 0: theoretical value approaches intrinsic value (5.00)
        price = _bs_price(190.0, 195.0, 0.5 / 365, 0.045, 0.30, "put")
        assert abs(price - 5.00) < 0.01


# ---------------------------------------------------------------------------
# theoreticalPayoffPerShare / combinedTheoreticalPayoff
# ---------------------------------------------------------------------------

_AAPL_PUT_SPREAD = [
    {"strike": 195, "option_type": "put", "quantity": -1, "cost": -3.85,
     "implied_volatility": 0.30, "days_to_expiry": 57},
    {"strike": 185, "option_type": "put", "quantity": 1, "cost": 1.95,
     "implied_volatility": 0.29, "days_to_expiry": 57},
]


class TestTheoreticalPayoff:
    def test_extrinsic_value_present_away_from_expiry(self):
        # At P=190 (between strikes), the theoretical value should differ
        # from the intrinsic (expiration) value — extrinsic time value present.
        price = 190.0
        theoretical = combined_theoretical_payoff(_AAPL_PUT_SPREAD, price, days_to_expiry=57)
        intrinsic = combined_payoff(_AAPL_PUT_SPREAD, price)
        assert abs(theoretical - intrinsic) > 0.01

    def test_theoretical_moves_toward_intrinsic_as_expiry_nears(self):
        price = 190.0
        far = combined_theoretical_payoff(_AAPL_PUT_SPREAD, price, days_to_expiry=57)
        near = combined_theoretical_payoff(_AAPL_PUT_SPREAD, price, days_to_expiry=1)
        intrinsic = combined_payoff(_AAPL_PUT_SPREAD, price)
        assert abs(near - intrinsic) < abs(far - intrinsic)


# ---------------------------------------------------------------------------
# Checkpoint availability (FR-004)
# ---------------------------------------------------------------------------

class TestAvailableCheckpoints:
    def test_thirty_dte_all_available(self):
        ids = [c["id"] for c in available_checkpoints(30)]
        assert ids == ["today", "plus1wk", "plus2wk", "expiration"]

    def test_ten_dte_excludes_plus2wk(self):
        ids = [c["id"] for c in available_checkpoints(10)]
        assert ids == ["today", "plus1wk", "expiration"]

    def test_five_dte_excludes_plus1wk_and_plus2wk(self):
        ids = [c["id"] for c in available_checkpoints(5)]
        assert ids == ["today", "expiration"]

    def test_zero_dte_only_expiration(self):
        ids = [c["id"] for c in available_checkpoints(0)]
        assert ids == ["expiration"]


# ---------------------------------------------------------------------------
# Eligibility (FR-001, FR-008, and the zero-DTE edge case)
# ---------------------------------------------------------------------------

class TestIsEligibleForOverlay:
    def test_eligible_with_valid_iv_and_positive_dte(self):
        assert is_eligible_for_overlay(_AAPL_PUT_SPREAD) is True

    def test_ineligible_when_any_leg_missing_iv(self):
        legs = [dict(_AAPL_PUT_SPREAD[0]), dict(_AAPL_PUT_SPREAD[1])]
        legs[1]["implied_volatility"] = None
        assert is_eligible_for_overlay(legs) is False

    def test_ineligible_when_iv_is_zero(self):
        legs = [dict(_AAPL_PUT_SPREAD[0]), dict(_AAPL_PUT_SPREAD[1])]
        legs[1]["implied_volatility"] = 0.0
        assert is_eligible_for_overlay(legs) is False

    def test_ineligible_when_zero_days_to_expiry(self):
        legs = [dict(leg, days_to_expiry=0) for leg in _AAPL_PUT_SPREAD]
        assert is_eligible_for_overlay(legs) is False


# ---------------------------------------------------------------------------
# The "Expiration" checkpoint collapse (FR-005 / research.md D-006)
# ---------------------------------------------------------------------------

class TestExpirationCheckpointCollapse:
    @pytest.mark.parametrize("price", [170, 185, 190, 195, 200])
    def test_expiration_checkpoint_matches_intrinsic_formula_exactly(self, price):
        expiration_checkpoint = next(c for c in CHECKPOINTS if c["id"] == "expiration")
        checkpoint_value = compute_checkpoint_pnl(_AAPL_PUT_SPREAD, expiration_checkpoint, price)
        assert checkpoint_value == combined_payoff(_AAPL_PUT_SPREAD, price)

    def test_non_expiration_checkpoint_differs_from_intrinsic_between_strikes(self):
        # Sanity check that the dispatch actually branches: "today" must NOT
        # collapse onto the intrinsic formula the way "expiration" does.
        today_checkpoint = next(c for c in CHECKPOINTS if c["id"] == "today")
        checkpoint_value = compute_checkpoint_pnl(_AAPL_PUT_SPREAD, today_checkpoint, 190.0)
        assert abs(checkpoint_value - combined_payoff(_AAPL_PUT_SPREAD, 190.0)) > 0.01
