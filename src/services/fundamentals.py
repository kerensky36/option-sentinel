"""Deterministic option fundamentals (specs/018 FR-101, FR-104, FR-105).

Pure functions — no I/O. The same code runs at positions refresh and again at
quorum time, so the figures the analysts see always agree with the legs
(research D-101, D-105). None always means unavailable, never zero.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Sequence

from src.data.models import LegFundamentals, PositionFundamentals
from src.services.bs_calculator import prob_itm

TRADING_DAYS = 252
MIN_RETURNS = 20
MULTIPLIER = 100


def realised_volatility(closes: Sequence[float], *, window: int = 30) -> float | None:
    """Annualised close-to-close volatility over the last `window` returns (D-102)."""
    recent = [float(c) for c in closes[-(window + 1):]]
    if any(c <= 0 for c in recent):
        return None
    returns = [math.log(b / a) for a, b in zip(recent, recent[1:])]
    if len(returns) < MIN_RETURNS:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(TRADING_DAYS)


def _scaled(greek: float | None, quantity: int) -> float | None:
    return None if greek is None else greek * quantity * MULTIPLIER


def leg_fundamentals(leg: Any, realised_vol: float | None, *, r: float) -> LegFundamentals:
    """Per-leg figures (D-103). `leg` exposes the PositionLegContext fields."""
    S = float(leg.underlying_price) if leg.underlying_price is not None else None
    K = float(leg.strike)
    sigma = leg.implied_volatility
    T = max(leg.days_to_expiry, 1) / 365
    q = leg.quantity

    moneyness = None
    if S:
        moneyness = ((S - K) if leg.option_type == "call" else (K - S)) / S * 100

    position_delta = _scaled(leg.delta, q)
    return LegFundamentals(
        realised_volatility=realised_vol,
        iv_rv_ratio=sigma / realised_vol if sigma and realised_vol else None,
        moneyness_pct=moneyness,
        expected_move=S * sigma * math.sqrt(T) if S and sigma else None,
        prob_itm=prob_itm(S, K, T, r, sigma, leg.option_type) if S and sigma else None,
        position_delta=position_delta,
        dollar_delta=position_delta * S if position_delta is not None and S else None,
        position_gamma=_scaled(leg.gamma, q),
        dollar_theta=_scaled(leg.theta, q),
        dollar_vega=_scaled(leg.vega, q),
    )


def _net(legs: Sequence[Any], field: str) -> float | None:
    values = [getattr(leg.fundamentals, field) for leg in legs]
    return None if any(v is None for v in values) else sum(values)


def _payoff(legs: Sequence[Any], price: float) -> float:
    total = 0.0
    for leg in legs:
        K = float(leg.strike)
        intrinsic = max(price - K, 0.0) if leg.option_type == "call" else max(K - price, 0.0)
        total += leg.quantity * MULTIPLIER * (intrinsic - float(leg.cost))
    return total


def _breakevens(points: list[tuple[float, float]], tail_slope: float) -> list[float]:
    found: list[float] = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y1 == 0 and x1 > 0:
            found.append(x1)
        elif y0 * y1 < 0:
            found.append(x0 + (x1 - x0) * (-y0) / (y1 - y0))
    x_last, y_last = points[-1]
    if y_last != 0 and tail_slope != 0 and (y_last > 0) != (tail_slope > 0):
        found.append(x_last - y_last / tail_slope)
    return [round(b, 4) for b in found]


def position_fundamentals(legs: Sequence[Any], net_unrealised_pnl: Decimal) -> PositionFundamentals:
    """Position-level figures from 1–4 legs on one underlying (D-104)."""
    theta = _net(legs, "dollar_theta")
    remaining = abs(sum(leg.quantity * MULTIPLIER * float(leg.current_mark) for leg in legs))
    result = PositionFundamentals(
        net_position_delta=_net(legs, "position_delta"),
        net_dollar_delta=_net(legs, "dollar_delta"),
        net_position_gamma=_net(legs, "position_gamma"),
        net_dollar_theta=theta,
        net_dollar_vega=_net(legs, "dollar_vega"),
        theta_pct_of_remaining=theta / remaining * 100 if theta is not None and remaining else None,
        single_expiry=len({leg.expiry_date for leg in legs}) == 1,
    )
    if not result.single_expiry:
        return result

    xs = [0.0] + sorted({float(leg.strike) for leg in legs})
    points = [(x, _payoff(legs, x)) for x in xs]
    tail_slope = sum(leg.quantity * MULTIPLIER for leg in legs if leg.option_type == "call")
    highest = max(y for _, y in points)
    lowest = min(y for _, y in points)

    result.breakevens = _breakevens(points, tail_slope)
    result.max_profit_unbounded = tail_slope > 0
    result.max_loss_unbounded = tail_slope < 0
    result.max_profit = None if tail_slope > 0 else max(highest, 0.0)
    result.max_loss = None if tail_slope < 0 else max(-lowest, 0.0)
    if result.max_profit:
        result.pct_max_profit_captured = float(net_unrealised_pnl) / result.max_profit * 100
    return result
