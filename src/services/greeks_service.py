"""Greeks computation service.

build_greeks() accepts raw position parameters and a Greeks dict from the
Schwab option chain API, and returns a plain dict of Greek field values.
Falls back to Black-Scholes when API values are absent.
"""
from __future__ import annotations

import os

from src.services.bs_calculator import bs_greeks

RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.045"))


def build_greeks(
    strike: float,
    option_type: str,
    days_to_expiry: int,
    raw: dict,
) -> dict:
    """Build a Greeks dict from raw API data, falling back to Black-Scholes.

    Args:
        strike: Option strike price.
        option_type: "call" or "put".
        days_to_expiry: Days remaining until expiry.
        raw: Dict from Schwab option chain response containing delta, gamma,
             theta, vega, implied_volatility, underlying_price.

    Returns:
        Dict with keys: delta, delta_source, gamma, gamma_source, theta,
        theta_source, vega, vega_source, implied_volatility, iv_source.
        Source values are "api" or "calculated" (or None if unavailable).
    """
    T = days_to_expiry / 365.0
    K = float(strike)
    underlying_price = float(raw.get("underlying_price") or 0) or K

    def _src(val) -> str | None:
        return "api" if val is not None else None

    delta = raw.get("delta")
    gamma = raw.get("gamma")
    theta = raw.get("theta")
    vega = raw.get("vega")
    iv_raw = raw.get("implied_volatility")

    # Convert Schwab IV from percentage to decimal if needed
    if iv_raw is not None and iv_raw > 2:
        iv_raw = iv_raw / 100.0

    result = {
        "delta": delta,
        "delta_source": _src(delta),
        "gamma": gamma,
        "gamma_source": _src(gamma),
        "theta": theta,
        "theta_source": _src(theta),
        "vega": vega,
        "vega_source": _src(vega),
        "implied_volatility": iv_raw,
        "iv_source": _src(iv_raw),
    }

    # Fill missing fields via Black-Scholes if we have enough data
    missing = not all([delta, gamma, theta, vega])
    if missing and T > 0 and K > 0 and underlying_price > 0:
        sigma = iv_raw or 0.25  # use IV if available, else assume 25%
        try:
            bs = bs_greeks(S=underlying_price, K=K, T=T, r=RISK_FREE_RATE, sigma=sigma, option_type=option_type)
            if result["delta"] is None:
                result["delta"] = bs.delta
                result["delta_source"] = "calculated"
            if result["gamma"] is None:
                result["gamma"] = bs.gamma
                result["gamma_source"] = "calculated"
            if result["theta"] is None:
                result["theta"] = bs.theta
                result["theta_source"] = "calculated"
            if result["vega"] is None:
                result["vega"] = bs.vega
                result["vega_source"] = "calculated"
        except Exception:
            pass

    return result
