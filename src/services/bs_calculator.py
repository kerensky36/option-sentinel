import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


@dataclass
class BSGreeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    implied_volatility: float | None


def bs_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str,
) -> BSGreeks:
    """
    Compute Black-Scholes Greeks for a European option.

    S: underlying price
    K: strike price
    T: time to expiry in years
    r: risk-free rate (e.g. 0.045)
    sigma: implied volatility (e.g. 0.30)
    option_type: 'call' or 'put'
    """
    if T <= 0 or sigma <= 0:
        nan = float("nan")
        return BSGreeks(delta=nan, gamma=nan, theta=nan, vega=nan, implied_volatility=None)

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        delta = float(norm.cdf(d1))
        theta = (
            -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * norm.cdf(d2)
        ) / 365
    else:
        delta = float(norm.cdf(d1) - 1)
        theta = (
            -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T) * norm.cdf(-d2)
        ) / 365

    gamma = float(norm.pdf(d1) / (S * sigma * math.sqrt(T)))
    vega = float(S * norm.pdf(d1) * math.sqrt(T) / 100)  # per 1% IV change

    return BSGreeks(delta=delta, gamma=gamma, theta=float(theta), vega=vega, implied_volatility=sigma)


def implied_volatility(
    S: float,
    K: float,
    T: float,
    r: float,
    option_price: float,
    option_type: str,
) -> float | None:
    """
    Compute implied volatility via Brent's method.
    Returns None if the solver fails to converge.
    """
    if T <= 0 or option_price <= 0:
        return None

    def objective(sigma: float) -> float:
        greeks = bs_greeks(S, K, T, r, sigma, option_type)
        theoretical = _bs_price(S, K, T, r, sigma, option_type)
        return theoretical - option_price

    try:
        iv = brentq(objective, 1e-6, 10.0, xtol=1e-6, maxiter=200)
        return float(iv)
    except ValueError:
        return None


def _bs_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
