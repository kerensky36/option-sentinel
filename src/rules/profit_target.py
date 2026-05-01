"""FR-021–023: Fire once when a position captures ≥50% of its max profit."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Alert, AlertSeverity, AlertType, DeliveryStatus, Position, PositionStatus

logger = logging.getLogger(__name__)

PROFIT_TARGET_PCT = 0.50


async def check_profit_targets(session: AsyncSession) -> list[str]:
    """Evaluate all open positions; fire alert if 50% profit captured and not already fired."""
    result = await session.execute(
        select(Position).where(Position.status == PositionStatus.open)
    )
    positions = result.scalars().all()
    fired: list[str] = []

    for pos in positions:
        cost = float(pos.opening_credit_debit or 0)
        qty = pos.quantity
        pnl = float(pos.unrealised_pnl or 0)
        mark = float(pos.current_mark or 0)

        # Max profit = full credit received (short positions: cost > 0, qty < 0)
        max_profit = abs(cost * abs(qty) * 100)
        if max_profit <= 0:
            continue

        pnl_pct = pnl / max_profit
        if pnl_pct < PROFIT_TARGET_PCT:
            continue

        # Check if alert already fired for this position (and not been re-armed)
        existing = await session.execute(
            select(Alert).where(
                Alert.alert_type == AlertType.profit_target,
                Alert.position_id == str(pos.id),
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Fire alert
        alert = Alert(
            alert_type=AlertType.profit_target,
            position_id=str(pos.id),
            severity=AlertSeverity.info,
            trigger_timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            delivery_status=DeliveryStatus.pending,
        )
        session.add(alert)
        await session.flush()

        delivered = await _send(pos, pnl, pnl_pct, mark, cost)
        alert.delivery_status = DeliveryStatus.delivered if delivered else DeliveryStatus.failed
        fired.append(pos.symbol)

    return fired


async def _send(pos: Position, pnl: float, pnl_pct: float, mark: float, cost: float) -> bool:
    from pathlib import Path
    from src.notifications.email_client import send_alert
    from datetime import date

    tmpl = (Path(__file__).parent.parent / "notifications" / "templates" / "profit_target.txt").read_text()
    body = tmpl.format(
        symbol=pos.symbol,
        underlying=pos.underlying_symbol,
        option_type=pos.option_type.value.title(),
        strike=float(pos.strike),
        expiry=pos.expiry_date.strftime("%b %-d '%y"),
        quantity=pos.quantity,
        mark=mark,
        cost=cost,
        pnl=pnl,
        pnl_pct=pnl_pct * 100,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    return await send_alert(f"[Option Sentinel] Profit Target Reached — {pos.underlying_symbol}", body)
