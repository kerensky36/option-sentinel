from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session
from src.data.models import Position, PositionStatus
from src.services import poll_scheduler
from src.services.schwab_client import sync_positions_and_greeks

router = APIRouter(prefix="/admin")


@router.post("/poll")
async def force_poll(session: AsyncSession = Depends(get_session)):
    """Force an immediate position + Greeks sync regardless of market hours."""
    try:
        await sync_positions_and_greeks(session)
        result = await session.execute(
            select(func.count()).where(Position.status == PositionStatus.open)
        )
        count = result.scalar() or 0
        poll_scheduler.last_poll_at = datetime.now(timezone.utc)
        poll_scheduler.last_poll_count = count

        from src.api.routes.sse import notify_refresh
        await notify_refresh(poll_scheduler.last_poll_at, count)

        return JSONResponse({"status": "ok", "open_positions": count})
    except Exception as exc:
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=500)
