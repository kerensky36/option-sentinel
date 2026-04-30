import logging
from datetime import datetime, timezone

import holidays
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.data.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

last_poll_at: datetime | None = None
last_poll_count: int = 0


def _is_market_open() -> bool:
    from zoneinfo import ZoneInfo
    now = datetime.now(tz=timezone.utc).astimezone(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:
        return False
    if now.date() in holidays.US(years=now.year):
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


async def _poll_job() -> None:
    global last_poll_at, last_poll_count
    if not _is_market_open():
        return
    try:
        from src.services.schwab_client import sync_positions_and_greeks
        from sqlalchemy import func, select
        from src.data.models import Position, PositionStatus

        async with AsyncSessionLocal() as session:
            await sync_positions_and_greeks(session)
            result = await session.execute(
                select(func.count()).where(Position.status == PositionStatus.open)
            )
            last_poll_count = result.scalar() or 0

        last_poll_at = datetime.now(timezone.utc)
        logger.info("Poll complete — %d open positions", last_poll_count)

        from src.api.routes.sse import notify_refresh
        await notify_refresh(last_poll_at, last_poll_count)

    except Exception:
        logger.exception("Poll job failed")


async def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(_poll_job, CronTrigger(minute="*/5"), id="poll_positions")
    _scheduler.start()
    logger.info("Scheduler started")


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler
