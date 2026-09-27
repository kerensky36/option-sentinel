"""Greeks computation service.

build_greeks() accepts raw position parameters and a Greeks dict from the
Schwab option chain API, and returns a plain dict of Greek field values.
Falls back to Black-Scholes when API values are absent.
"""
from __future__ import annotations

import math
import os

from src.services.bs_calculator import bs_greeks

RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.045"))

# Valid ranges for Schwab chain values (specs/018 FR-106, research D-109). Anything
# outside — including placeholders such as -999 or NaN — is treated as missing.
_RANGES = {
    "delta": (-1.0, 1.0),
    "gamma": (0.0, 10.0),
    "theta": (-10_000.0, 10_000.0),
    "vega": (0.0, 10_000.0),
}
_IV_PERCENT_MAX = 1000.0
_PLACEHOLDERS = {-999.0}  # Schwab's "not available" value, which can fall inside a range


def _valid(value, lo: float, hi: float, *, exclusive_lo: bool = False) -> float | None:
    """Return value as a float if it is finite and in range, else None."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or v in _PLACEHOLDERS or v > hi or v < lo or (exclusive_lo and v == lo):
        return None
    return v


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

    delta = _valid(raw.get("delta"), *_RANGES["delta"])
    gamma = _valid(raw.get("gamma"), *_RANGES["gamma"])
    theta = _valid(raw.get("theta"), *_RANGES["theta"])
    vega = _valid(raw.get("vega"), *_RANGES["vega"])
    iv_raw = _valid(raw.get("implied_volatility"), 0.0, _IV_PERCENT_MAX, exclusive_lo=True)

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
    missing = any(v is None for v in (delta, gamma, theta, vega))  # a 0 is a real value (FR-107)
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
