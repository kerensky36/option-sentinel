from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session
from src.data.models import BinaryEventFlag

router = APIRouter()


@router.post("/binary-event/raise")
async def raise_binary_event(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(BinaryEventFlag).where(BinaryEventFlag.id == 1))
    flag = result.scalar_one_or_none()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if flag is None:
        flag = BinaryEventFlag(id=1, is_active=True, activated_at=now)
        session.add(flag)
    else:
        flag.is_active = True
        flag.activated_at = now
        flag.cleared_at = None

    await session.commit()

    # Fire immediate consolidated exit alert (FR-028)
    from src.rules.binary_event import fire_binary_event_alert
    from src.data.database import AsyncSessionLocal
    async with AsyncSessionLocal() as alert_session:
        await fire_binary_event_alert(alert_session)

    return RedirectResponse("/", status_code=303)


@router.post("/binary-event/clear")
async def clear_binary_event(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(BinaryEventFlag).where(BinaryEventFlag.id == 1))
    flag = result.scalar_one_or_none()
    if flag:
        flag.is_active = False
        flag.cleared_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()
    return RedirectResponse("/", status_code=303)
