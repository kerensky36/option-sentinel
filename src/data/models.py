"""In-memory Pydantic models — no database, no ORM."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class LegFundamentals(BaseModel):
    """Per-leg calculated figures (specs/018 FR-101, research D-103).

    None always means unavailable — never substituted with zero (FR-105).
    """

    realised_volatility: float | None = None
    iv_rv_ratio: float | None = None
    moneyness_pct: float | None = None
    expected_move: float | None = None
    prob_itm: float | None = None
    position_delta: float | None = None
    dollar_delta: float | None = None
    position_gamma: float | None = None
    dollar_theta: float | None = None
    dollar_vega: float | None = None


class PositionFundamentals(BaseModel):
    """Position-level figures calculated from the legs at quorum time (specs/018 FR-104, D-104)."""

    net_position_delta: float | None = None
    net_dollar_delta: float | None = None
    net_position_gamma: float | None = None
    net_dollar_theta: float | None = None
    net_dollar_vega: float | None = None
    breakevens: list[float] = []
    max_profit: float | None = None
    max_loss: float | None = None
    max_profit_unbounded: bool = False
    max_loss_unbounded: bool = False
    pct_max_profit_captured: float | None = None
    theta_pct_of_remaining: float | None = None
    single_expiry: bool = True


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
    underlying_price: Decimal | None = None

    delta_source: Literal["api", "calculated"] | None = None
    gamma_source: Literal["api", "calculated"] | None = None
    theta_source: Literal["api", "calculated"] | None = None
    vega_source: Literal["api", "calculated"] | None = None
    iv_source: Literal["api", "calculated"] | None = None

    as_of: datetime | None = None
    fundamentals: LegFundamentals = LegFundamentals()


class ScreenerResultView(BaseModel):
    """A single covered-call recommendation for a long stock position.

    Exists only for the duration of a screener refresh request.
    """

    ticker: str
    shares: int
    contracts: int = 0
    stock_price: float
    implied_volatility: float | None = None
    realised_volatility: float | None = None
    iv_rv_ratio: float | None = None
    vol_score: float | None = None
    recommended_strike: float | None = None
    recommended_expiry: str | None = None
    bid_premium: float | None = None
    annualised_yield: float | None = None
    call_delta: float | None = None
    days_to_earnings: int | None = None
    composite_score: float = 0.0
    recommendation_status: Literal["recommended", "suppressed", "insufficient_data"] = "insufficient_data"
    sort_order: int = 0
    candidates: list[dict] = []


# ── Macro news voting quorum (specs/017) ──────────────────────────────────────

QuorumAction = Literal["CLOSE", "HOLD", "ROLL"]
QuorumVerdict = Literal["CLOSE", "HOLD", "ROLL", "NO_CONSENSUS", "NO_QUORUM"]
RollDirection = Literal["out", "up_and_out", "down_and_out"]

QUORUM_DISCLAIMER = (
    "Informational only — not financial advice. Option Sentinel never places trades."
)


_TICKER_PATTERN = r"^\$?[A-Z0-9./^-]{1,10}$"


class QuorumLegIn(BaseModel):
    """One leg of a quorum request, as held by the browser (specs/018 FR-110, FR-111).

    Strict: unknown fields, non-finite numbers and out-of-range values are rejected.
    No free-text fields — the only string is a ticker-shaped symbol.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    underlying_symbol: str = Field(pattern=_TICKER_PATTERN)
    option_type: Literal["call", "put"]
    strike: Decimal = Field(gt=0, le=1_000_000)
    expiry_date: date
    days_to_expiry: int = Field(ge=0, le=1500)
    quantity: int = Field(ge=-100_000, le=100_000)
    cost: Decimal = Field(ge=0, le=1_000_000)
    current_mark: Decimal = Field(ge=0, le=1_000_000)
    unrealised_pnl: Decimal = Field(ge=-1_000_000_000, le=1_000_000_000)
    delta: float | None = Field(default=None, ge=-1, le=1)
    gamma: float | None = Field(default=None, ge=0, le=10)
    theta: float | None = Field(default=None, ge=-10_000, le=10_000)
    vega: float | None = Field(default=None, ge=0, le=10_000)
    implied_volatility: float | None = Field(default=None, gt=0, le=10)
    underlying_price: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    realised_volatility: float | None = Field(default=None, ge=0, le=10)

    @field_validator("quantity")
    @classmethod
    def _non_zero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("quantity must be non-zero")
        return v

    @field_validator("expiry_date")
    @classmethod
    def _plausible_expiry(cls, v: date) -> date:
        today = date.today()
        if not today - timedelta(days=1) <= v <= today + timedelta(days=4 * 365):
            raise ValueError("expiry_date out of range")
        return v


class QuorumRequest(BaseModel):
    """Request body for POST /api/quorum/vote v2 (specs/018 FR-110, FR-111).

    No account identifier and no leg symbol are accepted.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    as_of: AwareDatetime
    legs: list[QuorumLegIn] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def _one_underlying(self) -> "QuorumRequest":
        if len({leg.underlying_symbol for leg in self.legs}) != 1:
            raise ValueError("all legs must share one underlying")
        return self


class PositionLegContext(BaseModel):
    """Allow-list of leg fields that may be sent to Vertex AI (FR-011, Constitution I).

    Adding a field here sends it to the model — it MUST NOT identify the user.
    """

    underlying_symbol: str
    option_type: Literal["call", "put"]
    strike: Decimal
    expiry_date: date
    days_to_expiry: int
    quantity: int
    cost: Decimal
    current_mark: Decimal
    unrealised_pnl: Decimal
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    implied_volatility: float | None = None
    underlying_price: Decimal | None = None
    fundamentals: LegFundamentals = LegFundamentals()


class PositionContext(BaseModel):
    """De-identified description of one position evaluated by the quorum."""

    underlying_symbol: str
    legs: list[PositionLegContext]
    net_unrealised_pnl: Decimal
    min_days_to_expiry: int
    position_fundamentals: PositionFundamentals = PositionFundamentals()
    as_of: datetime


class Headline(BaseModel):
    """One news item from a public financial news feed."""

    publisher: Literal["CNBC", "Yahoo Finance", "Bloomberg"]
    title: str
    link: str
    published: datetime | None = None
    summary: str = ""


class AnalystBallot(BaseModel):
    """Structured output schema each ADK analyst seat must return (FR-005)."""

    action: QuorumAction
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    roll_direction: RollDirection | None = None
    cited: list[str] = []  # figure-catalog names the seat relied on (specs/020 FR-315)

    @field_validator("rationale")
    @classmethod
    def _truncate(cls, v: str) -> str:
        return v.strip()[:600]

    @field_validator("cited")
    @classmethod
    def _cap_cited(cls, v: list[str]) -> list[str]:
        return [str(n)[:40] for n in v[:5]]

    @model_validator(mode="after")
    def _roll_needs_direction(self) -> "AnalystBallot":
        if self.action == "ROLL" and self.roll_direction is None:
            raise ValueError("ROLL vote requires roll_direction")
        if self.action != "ROLL":
            self.roll_direction = None
        return self


class CitedFigure(BaseModel):
    """A figure-catalog entry a seat cited; label and display come from the server (specs/020 FR-315)."""

    name: str
    label: str
    display: str


class AnalystVote(BaseModel):
    """One seat's outcome as returned to the client; action None = abstained."""

    seat: str
    lens: str
    action: QuorumAction | None = None
    confidence: float | None = None
    rationale: str = ""
    roll_direction: RollDirection | None = None
    abstained: bool = False
    cited_figures: list[CitedFigure] = []


class TallyEntry(BaseModel):
    action: QuorumAction
    votes: int
    mean_confidence: float | None = None


class QuorumResult(BaseModel):
    """Full quorum outcome. Never persisted (FR-015)."""

    verdict: QuorumVerdict
    quorum_met: bool
    seats: int
    valid_votes: int
    tally: list[TallyEntry]
    votes: list[AnalystVote]
    macro_brief: str | None = None
    headlines: list[Headline] = []
    underlying_symbol: str
    model: str
    generated_at: datetime
    as_of: datetime
    position_fundamentals: PositionFundamentals = PositionFundamentals()
    disclaimer: str = QUORUM_DISCLAIMER
    # Opaque, HMAC-signed summariser input (specs/020 D-302); None for NO_QUORUM or no seal key.
    summary_token: str | None = None
