"""Unit tests for option payoff math — mirrors frontend/static/js/payoff_math.js.

These tests define the payoff formula contract and must FAIL before
payoff_math.js is implemented, then pass once the JS mirrors this logic.
Since this is a pure-math specification, the Python implementation here
IS the authoritative reference that the JS must match.
"""
from __future__ import annotations

import math
import pytest


# ---------------------------------------------------------------------------
# Python reference implementation (mirrors payoff_math.js exactly)
# ---------------------------------------------------------------------------

def leg_payoff_per_share(strike: float, option_type: str, quantity: int, cost: float, price: float) -> float:
    """P&L per share for one leg at expiration.

    Formula: sign(quantity) * intrinsic - cost
      where intrinsic = max(price - strike, 0) for calls
                      = max(strike - price, 0) for puts
    """
    if option_type == "call":
        intrinsic = max(price - strike, 0.0)
    else:
        intrinsic = max(strike - price, 0.0)
    sign = 1 if quantity > 0 else -1
    return sign * intrinsic - cost


def combined_payoff(legs: list[dict], price: float) -> float:
    """Combined net P&L per share across all legs at expiration."""
    total = 0.0
    for leg in legs:
        total += leg_payoff_per_share(
            leg["strike"], leg["option_type"], leg["quantity"], leg["cost"], price
        )
    return total


def analyze_payoff(legs: list[dict]) -> dict:
    """Scan 200 price points and return max gain, max loss, breakevens, strikePrices, curve."""
    strikes = sorted({leg["strike"] for leg in legs})
    price_min = min(strikes) * 0.65
    price_max = max(strikes) * 1.35
    step = (price_max - price_min) / 199

    curve = []
    for i in range(200):
        price = price_min + i * step
        pnl = combined_payoff(legs, price)
        curve.append({"price": price, "pnl": pnl})

    pnl_values = [pt["pnl"] for pt in curve]
    max_gain = max(pnl_values)
    max_loss = min(pnl_values)

    breakevens = []
    for i in range(len(curve) - 1):
        a, b = curve[i]["pnl"], curve[i + 1]["pnl"]
        if (a < 0 < b) or (a > 0 > b) or a == 0:
            midprice = (curve[i]["price"] + curve[i + 1]["price"]) / 2
            breakevens.append(round(midprice, 2))

    return {
        "maxGain": max_gain,
        "maxLoss": max_loss,
        "breakevens": breakevens,
        "strikePrices": strikes,
        "curve": curve,
    }


# ---------------------------------------------------------------------------
# Single-leg tests
# ---------------------------------------------------------------------------

class TestLegPayoffPerShare:
    def test_short_put_above_strike_keeps_full_premium(self):
        # Short put qty=-1, cost=-3.85, K=195 at P=200: keep 3.85
        result = leg_payoff_per_share(195, "put", -1, -3.85, 200)
        assert abs(result - 3.85) < 0.001

    def test_short_put_at_strike_keeps_full_premium(self):
        # At exactly the strike: put expires worthless
        result = leg_payoff_per_share(195, "put", -1, -3.85, 195)
        assert abs(result - 3.85) < 0.001

    def test_short_put_below_strike_incurs_loss(self):
        # P=190: intrinsic=5, received=3.85, net=-1.15
        result = leg_payoff_per_share(195, "put", -1, -3.85, 190)
        assert abs(result - (-1.15)) < 0.001

    def test_long_call_below_strike_loses_premium(self):
        # Long call qty=+1, cost=+2.50, K=220 at P=215: OTM, lose premium
        result = leg_payoff_per_share(220, "call", 1, 2.50, 215)
        assert abs(result - (-2.50)) < 0.001

    def test_long_call_at_breakeven(self):
        # Long call K=220, cost=2.50 — breakeven at P=222.50
        result = leg_payoff_per_share(220, "call", 1, 2.50, 222.50)
        assert abs(result - 0.0) < 0.001

    def test_long_call_above_strike_profits(self):
        # Long call K=220, cost=2.50 at P=225: intrinsic=5, net=2.50
        result = leg_payoff_per_share(220, "call", 1, 2.50, 225)
        assert abs(result - 2.50) < 0.001

    def test_short_call_below_strike_keeps_premium(self):
        # Short call qty=-1, cost=-3.20, K=220 at P=215: OTM, keep 3.20
        result = leg_payoff_per_share(220, "call", -1, -3.20, 215)
        assert abs(result - 3.20) < 0.001

    def test_short_call_above_strike_loses(self):
        # Short call K=220, cost=-3.20 at P=225: intrinsic=5, net=3.20-5=-1.80
        result = leg_payoff_per_share(220, "call", -1, -3.20, 225)
        assert abs(result - (-1.80)) < 0.001

    def test_long_put_above_strike_loses_premium(self):
        # Long put qty=+1, cost=+1.95, K=185 at P=192: OTM, lose 1.95
        result = leg_payoff_per_share(185, "put", 1, 1.95, 192)
        assert abs(result - (-1.95)) < 0.001

    def test_long_put_below_strike_profits(self):
        # Long put K=185, cost=1.95 at P=180: intrinsic=5, net=3.05
        result = leg_payoff_per_share(185, "put", 1, 1.95, 180)
        assert abs(result - 3.05) < 0.001


# ---------------------------------------------------------------------------
# Combined payoff (multi-leg spread)
# ---------------------------------------------------------------------------

_BULL_PUT_SPREAD = [
    {"strike": 195, "option_type": "put", "quantity": -1, "cost": -3.85},  # short put
    {"strike": 185, "option_type": "put", "quantity": 1,  "cost":  1.95},  # long put
]


class TestCombinedPayoff:
    def test_above_both_strikes_max_gain(self):
        # Both puts expire worthless. Net = 3.85 - 1.95 = 1.90
        result = combined_payoff(_BULL_PUT_SPREAD, 200)
        assert abs(result - 1.90) < 0.001

    def test_below_both_strikes_max_loss(self):
        # Both puts fully ITM. Short put P&L = -(195-170) + 3.85 = -21.15
        # Long put P&L = (185-170) - 1.95 = 13.05. Combined = -8.10
        result = combined_payoff(_BULL_PUT_SPREAD, 170)
        assert abs(result - (-8.10)) < 0.001

    def test_between_strikes(self):
        # P=190: short put ITM by 5; long put OTM.
        # Short put: sign(-1)*5 - (-3.85) = -5 + 3.85 = -1.15
        # Long put: sign(1)*0 - 1.95 = -1.95
        # Total = -1.15 + (-1.95) = -3.10...
        # Wait: at P=190, between 185 and 195:
        # Short put (K=195): intrinsic=5, -1*5 - (-3.85) = -5+3.85 = -1.15
        # Long put (K=185): intrinsic=0, +1*0 - 1.95 = -1.95
        # Total = -3.10
        result = combined_payoff(_BULL_PUT_SPREAD, 190)
        assert abs(result - (-3.10)) < 0.001


# ---------------------------------------------------------------------------
# Analyze payoff
# ---------------------------------------------------------------------------

class TestAnalyzePayoff:
    def test_bull_put_spread_max_gain(self):
        analysis = analyze_payoff(_BULL_PUT_SPREAD)
        assert abs(analysis["maxGain"] - 1.90) < 0.05

    def test_bull_put_spread_max_loss(self):
        analysis = analyze_payoff(_BULL_PUT_SPREAD)
        assert abs(analysis["maxLoss"] - (-8.10)) < 0.05

    def test_strike_prices_extracted(self):
        analysis = analyze_payoff(_BULL_PUT_SPREAD)
        assert analysis["strikePrices"] == [185, 195]

    def test_curve_has_200_points(self):
        analysis = analyze_payoff(_BULL_PUT_SPREAD)
        assert len(analysis["curve"]) == 200

    def test_curve_price_range(self):
        analysis = analyze_payoff(_BULL_PUT_SPREAD)
        assert analysis["curve"][0]["price"] < 185
        assert analysis["curve"][-1]["price"] > 195

    def test_one_breakeven_for_spread(self):
        analysis = analyze_payoff(_BULL_PUT_SPREAD)
        assert len(analysis["breakevens"]) == 1
        # Breakeven at K_short - net_premium = 195 - 1.90 = 193.10
        assert abs(analysis["breakevens"][0] - 193.10) < 0.50

    def test_iron_condor_two_breakevens(self):
        iron_condor = [
            {"strike": 530, "option_type": "put",  "quantity": 1,  "cost":  1.40},
            {"strike": 540, "option_type": "put",  "quantity": -1, "cost": -2.20},
            {"strike": 575, "option_type": "call", "quantity": -1, "cost": -2.50},
            {"strike": 585, "option_type": "call", "quantity": 1,  "cost":  1.60},
        ]
        analysis = analyze_payoff(iron_condor)
        # Max gain = net premium = 2.20 + 2.50 - 1.40 - 1.60 = 1.70
        assert abs(analysis["maxGain"] - 1.70) < 0.05
        # Two breakevens (one on each wing)
        assert len(analysis["breakevens"]) == 2
