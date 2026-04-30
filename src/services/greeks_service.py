import os
from datetime import date

from src.data.models import Position, SourceEnum
from src.services.bs_calculator import bs_greeks, implied_volatility

RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.045"))


def build_greeks(position: Position, raw: dict) -> dict:
    dte = position.days_to_expiry or 0
    T = dte / 365.0
    K = float(position.strike)
    option_type = position.option_type.value if hasattr(position.option_type, "value") else position.option_type
    # Use underlying price from chain response; fall back to strike as last resort
    underlying_price = float(raw.get("underlying_price") or 0) or K

    def _src(val) -> SourceEnum:
        return SourceEnum.api if val is not None else SourceEnum.unavailable

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
                result["delta_source"] = SourceEnum.calculated
            if result["gamma"] is None:
                result["gamma"] = bs.gamma
                result["gamma_source"] = SourceEnum.calculated
            if result["theta"] is None:
                result["theta"] = bs.theta
                result["theta_source"] = SourceEnum.calculated
            if result["vega"] is None:
                result["vega"] = bs.vega
                result["vega_source"] = SourceEnum.calculated
        except Exception:
            pass

    return result
