"""In-memory Pydantic models — no database, no ORM."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class PositionView(BaseModel):
    """A single open options position enriched with computed Greeks.

    Exists only for the duration of a positions refresh request.
    """

    symbol: str
    underlying_symbol: str
    option_type: Literal["call", "put"]
    strike: Decimal
    expiry_date: date
    quantity: int
    cost: Decimal
    current_mark: Decimal
    unrealised_pnl: Decimal
    days_to_expiry: int

    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    implied_volatility: float | None = None

    delta_source: Literal["api", "calculated"] | None = None
    gamma_source: Literal["api", "calculated"] | None = None
    theta_source: Literal["api", "calculated"] | None = None
    vega_source: Literal["api", "calculated"] | None = None
    iv_source: Literal["api", "calculated"] | None = None


class ScreenerResultView(BaseModel):
    """A single covered-call recommendation for a long stock position.

    Exists only for the duration of a screener refresh request.
    """

    ticker: str
    shares: int
    contracts: int = 0
    stock_price: float
    iv_rank: float | None = None
    recommended_strike: float | None = None
    recommended_expiry: str | None = None
    bid_premium: float | None = None
    annualised_yield: float | None = None
    call_delta: float | None = None
    days_to_earnings: int | None = None
    composite_score: float = 0.0
    recommendation_status: Literal["recommended", "suppressed", "insufficient_data"] = "insufficient_data"
    sort_order: int = 0
