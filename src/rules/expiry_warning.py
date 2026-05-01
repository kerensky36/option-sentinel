"""FR-024–027: Escalating expiry warnings at 14, 7, and 3 DTE."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Alert, AlertSeverity, AlertType, DeliveryStatus, Position, PositionStatus

logger = logging.getLogger(__name__)

TIERS = {
    AlertType.expiry_14d: (14, AlertSeverity.info,    "14-Day Warning"),
    AlertType.expiry_7d:  (7,  AlertSeverity.warning, "7-Day Warning"),
    AlertType.expiry_3d:  (3,  AlertSeverity.critical, "3-Day URGENT"),
}

URGENCY = {
    AlertType.expiry_14d: "Begin evaluating whether to close or roll this position.",
    AlertType.expiry_7d:  "Time decay is accelerating. Consider closing or rolling soon.",
    AlertType.expiry_3d:  "URGENT: Position expires in 3 days. Assignment risk is elevated.",
}


async def check_expiry_warnings(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Position).where(Position.status == PositionStatus.open)
    )
    positions = result.scalars().all()
    fired: list[str] = []

    for pos in positions:
        dte = pos.days_to_expiry
        if dte is None:
            continue

        for alert_type, (threshold, severity, tier_label) in TIERS.items():
            if dte > threshold:
                continue

            # Already fired for this tier?
            existing = await session.execute(
                select(Alert).where(
                    Alert.alert_type == alert_type,
                    Alert.position_id == str(pos.id),
                )
            )
            if existing.scalar_one_or_none():
                continue

            alert = Alert(
                alert_type=alert_type,
                position_id=str(pos.id),
                severity=severity,
                trigger_timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                delivery_status=DeliveryStatus.pending,
            )
            session.add(alert)
            await session.flush()

            delivered = await _send(pos, dte, tier_label, alert_type)
            alert.delivery_status = DeliveryStatus.delivered if delivered else DeliveryStatus.failed
            fired.append(f"{pos.symbol}@{tier_label}")

    return fired


async def _send(pos: Position, dte: int, tier_label: str, alert_type: AlertType) -> bool:
    from pathlib import Path
    from src.notifications.email_client import send_alert

    tmpl = (Path(__file__).parent.parent / "notifications" / "templates" / "expiry_warning.txt").read_text()
    body = tmpl.format(
        tier=tier_label,
        symbol=pos.symbol,
        underlying=pos.underlying_symbol,
        option_type=pos.option_type.value.title(),
        strike=float(pos.strike),
        expiry=pos.expiry_date.strftime("%b %-d '%y"),
        dte=dte,
        pnl=float(pos.unrealised_pnl or 0),
        urgency_note=URGENCY[alert_type],
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    severity_tag = "⚠" if alert_type != AlertType.expiry_3d else "🚨"
    return await send_alert(
        f"[Option Sentinel] {severity_tag} Expiry {tier_label} — {pos.underlying_symbol}",
        body,
    )
