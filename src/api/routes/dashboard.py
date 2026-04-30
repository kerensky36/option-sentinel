from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_session
from src.api.main import templates
from src.data.models import BinaryEventFlag, Position, PositionStatus, Thesis
from src.services import poll_scheduler
from src.services.position_groups import group_positions

router = APIRouter()


async def _get_open_positions(session: AsyncSession) -> list[Position]:
    result = await session.execute(
        select(Position)
        .where(Position.status == PositionStatus.open)
        .options(
            selectinload(Position.greeks),
            selectinload(Position.exit_goal),
            selectinload(Position.thesis),
        )
        .order_by(Position.created_at)
    )
    return list(result.scalars().all())


async def _get_binary_flag(session: AsyncSession) -> BinaryEventFlag | None:
    result = await session.execute(select(BinaryEventFlag).where(BinaryEventFlag.id == 1))
    return result.scalar_one_or_none()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    positions = await _get_open_positions(session)
    binary_flag = await _get_binary_flag(session)
    theses_result = await session.execute(select(Thesis).order_by(Thesis.name))
    theses = list(theses_result.scalars().all())
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "groups": group_positions(positions),
            "theses": theses,
            "binary_flag": binary_flag,
            "last_poll_at": poll_scheduler.last_poll_at,
        },
    )


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    db_status = "ok"
    try:
        await session.execute(select(1))
    except Exception:
        db_status = "error"

    return JSONResponse({
        "status": "ok",
        "last_poll": poll_scheduler.last_poll_at.isoformat() if poll_scheduler.last_poll_at else None,
        "db": db_status,
        "schwab_auth": "ok",
    })
