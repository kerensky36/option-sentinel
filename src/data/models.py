"""In-memory Pydantic models — no database, no ORM."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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
    candidates: list[dict] = []


# ── Macro news voting quorum (specs/017) ──────────────────────────────────────

QuorumAction = Literal["CLOSE", "HOLD", "ROLL"]
QuorumVerdict = Literal["CLOSE", "HOLD", "ROLL", "NO_CONSENSUS", "NO_QUORUM"]
RollDirection = Literal["out", "up_and_out", "down_and_out"]

QUORUM_DISCLAIMER = (
    "Informational only — not financial advice. Option Sentinel never places trades."
)


class QuorumRequest(BaseModel):
    """Request body for POST /api/quorum/vote — leg symbols only (FR-002)."""

    symbols: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(
        min_length=1, max_length=4
    )
    account_hash: str | None = Field(default=None, max_length=256)

    @field_validator("symbols")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("symbols must be unique")
        return v


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


class PositionContext(BaseModel):
    """De-identified description of one position evaluated by the quorum."""

    underlying_symbol: str
    legs: list[PositionLegContext]
    net_unrealised_pnl: Decimal
    min_days_to_expiry: int


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

    @field_validator("rationale")
    @classmethod
    def _truncate(cls, v: str) -> str:
        return v.strip()[:600]

    @model_validator(mode="after")
    def _roll_needs_direction(self) -> "AnalystBallot":
        if self.action == "ROLL" and self.roll_direction is None:
            raise ValueError("ROLL vote requires roll_direction")
        if self.action != "ROLL":
            self.roll_direction = None
        return self


class AnalystVote(BaseModel):
    """One seat's outcome as returned to the client; action None = abstained."""

    seat: str
    lens: str
    action: QuorumAction | None = None
    confidence: float | None = None
    rationale: str = ""
    roll_direction: RollDirection | None = None
    abstained: bool = False


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
    disclaimer: str = QUORUM_DISCLAIMER
