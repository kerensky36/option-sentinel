"""FR-028–029: Immediate consolidated exit alert when binary event flag is raised."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import BinaryEventFlag, Position, PositionStatus

logger = logging.getLogger(__name__)


async def fire_binary_event_alert(session: AsyncSession) -> bool:
    """Send consolidated exit alert for all open positions. Returns True if sent."""
    result = await session.execute(
        select(Position).where(Position.status == PositionStatus.open)
    )
    positions = list(result.scalars().all())

    if not positions:
        logger.info("Binary event raised but no open positions — skipping alert")
        return False

    lines = []
    for pos in positions:
        pnl = float(pos.unrealised_pnl or 0)
        sign = "+" if pnl >= 0 else ""
        lines.append(
            f"  {pos.underlying_symbol:6s}  {pos.option_type.value.upper():4s}  "
            f"${float(pos.strike):.0f}  exp {pos.expiry_date.strftime('%b %-d')}"
            f"  qty {pos.quantity:+d}  P&L {sign}${pnl:.2f}"
        )

    tmpl = (Path(__file__).parent.parent / "notifications" / "templates" / "binary_event.txt").read_text()
    body = tmpl.format(
        count=len(positions),
        position_lines="\n".join(lines),
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    from src.notifications.email_client import send_alert
    return await send_alert("[Option Sentinel] 🚨 BINARY EVENT — EXIT ALL POSITIONS", body)
