import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OptionType(str, enum.Enum):
    call = "call"
    put = "put"


class PositionStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class SourceEnum(str, enum.Enum):
    api = "api"
    calculated = "calculated"
    unavailable = "unavailable"


class PriceTargetDirection(str, enum.Enum):
    above = "above"
    below = "below"


class ThesisTemplateType(str, enum.Enum):
    iv_crush = "iv_crush"
    earnings_fade = "earnings_fade"
    directional_momentum = "directional_momentum"
    mean_reversion = "mean_reversion"
    custom = "custom"


class AlignmentRating(str, enum.Enum):
    aligned = "aligned"
    partially_aligned = "partially_aligned"
    misaligned = "misaligned"
    unrated = "unrated"


class ThesisStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class SpreadStrategyType(str, enum.Enum):
    put_credit_spread = "put_credit_spread"
    call_credit_spread = "call_credit_spread"
    iron_condor = "iron_condor"
    vertical = "vertical"
    custom = "custom"


class AlertType(str, enum.Enum):
    profit_target = "profit_target"
    expiry_14d = "expiry_14d"
    expiry_7d = "expiry_7d"
    expiry_3d = "expiry_3d"
    binary_event_exit = "binary_event_exit"


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    delivered = "delivered"
    failed = "failed"
    max_retries = "max_retries"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Thesis(Base):
    __tablename__ = "thesis"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_type: Mapped[ThesisTemplateType] = mapped_column(Enum(ThesisTemplateType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    alignment_rating: Mapped[AlignmentRating] = mapped_column(
        Enum(AlignmentRating), nullable=False, default=AlignmentRating.unrated
    )
    status: Mapped[ThesisStatus] = mapped_column(
        Enum(ThesisStatus), nullable=False, default=ThesisStatus.active
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    positions: Mapped[list["Position"]] = relationship("Position", back_populates="thesis")


class Spread(Base):
    __tablename__ = "spread"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[SpreadStrategyType] = mapped_column(Enum(SpreadStrategyType), nullable=False)
    net_credit_received: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    maximum_profit: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    maximum_loss: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    positions: Mapped[list["Position"]] = relationship("Position", back_populates="spread")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="spread")


class Position(Base):
    __tablename__ = "position"
    __table_args__ = (
        # Partial unique index: only one open position per symbol+account
        Index(
            "uq_position_open_symbol_account",
            "symbol",
            "schwab_account_id",
            unique=True,
            sqlite_where=text("status = 'open'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    schwab_account_id: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str] = mapped_column(String(21), nullable=False)
    underlying_symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    option_type: Mapped[OptionType] = mapped_column(Enum(OptionType), nullable=False)
    strike: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    opening_credit_debit: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    current_mark: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    unrealised_pnl: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    days_to_expiry: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[PositionStatus] = mapped_column(
        Enum(PositionStatus), nullable=False, default=PositionStatus.open
    )
    thesis_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("thesis.id", ondelete="SET NULL"), nullable=True)
    spread_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("spread.id"), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    thesis: Mapped["Thesis | None"] = relationship("Thesis", back_populates="positions")
    spread: Mapped["Spread | None"] = relationship("Spread", back_populates="positions")
    greeks: Mapped["Greeks | None"] = relationship("Greeks", back_populates="position", uselist=False)
    exit_goal: Mapped["ExitGoal | None"] = relationship("ExitGoal", back_populates="position", uselist=False)
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="position")
    health_snapshots: Mapped[list["ThesisHealthSnapshot"]] = relationship(
        "ThesisHealthSnapshot", back_populates="position", order_by="ThesisHealthSnapshot.snapshot_date"
    )


class Greeks(Base):
    __tablename__ = "greeks"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("position.id"), nullable=False, unique=True)
    delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta_source: Mapped[SourceEnum] = mapped_column(Enum(SourceEnum), nullable=False)
    gamma: Mapped[float | None] = mapped_column(Float, nullable=True)
    gamma_source: Mapped[SourceEnum] = mapped_column(Enum(SourceEnum), nullable=False)
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    theta_source: Mapped[SourceEnum] = mapped_column(Enum(SourceEnum), nullable=False)
    vega: Mapped[float | None] = mapped_column(Float, nullable=True)
    vega_source: Mapped[SourceEnum] = mapped_column(Enum(SourceEnum), nullable=False)
    implied_volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    iv_source: Mapped[SourceEnum] = mapped_column(Enum(SourceEnum), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    position: Mapped["Position"] = relationship("Position", back_populates="greeks")


class ExitGoal(Base):
    __tablename__ = "exit_goal"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("position.id"), nullable=False, unique=True)
    profit_target_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    dte_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    underlying_price_target: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_target_direction: Mapped[PriceTargetDirection | None] = mapped_column(
        Enum(PriceTargetDirection), nullable=True
    )
    exit_proximity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    position: Mapped["Position"] = relationship("Position", back_populates="exit_goal")


class Alert(Base):
    __tablename__ = "alert"
    __table_args__ = (
        UniqueConstraint("alert_type", "position_id", name="uq_alert_daily_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    position_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("position.id"), nullable=True)
    spread_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("spread.id"), nullable=True)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    trigger_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.pending
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    position: Mapped["Position | None"] = relationship("Position", back_populates="alerts")
    spread: Mapped["Spread | None"] = relationship("Spread", back_populates="alerts")


class ThesisHealthSnapshot(Base):
    __tablename__ = "thesis_health_snapshot"
    __table_args__ = (
        UniqueConstraint("position_id", "snapshot_date", name="uq_thesis_snapshot_pos_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("position.id", ondelete="CASCADE"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)

    position: Mapped["Position"] = relationship("Position", back_populates="health_snapshots")


class AuthToken(Base):
    __tablename__ = "auth_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    access_expiry: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_expiry: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    re_auth_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_refreshed: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class BinaryEventFlag(Base):
    __tablename__ = "binary_event_flag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
