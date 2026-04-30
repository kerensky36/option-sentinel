from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_session
from src.api.main import templates
from src.data.models import Position, PositionStatus, Thesis
from src.services.position_groups import group_positions

router = APIRouter(prefix="/partials")


@router.get("/positions", response_class=HTMLResponse)
async def positions_partial(request: Request, session: AsyncSession = Depends(get_session)):
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
    positions = list(result.scalars().all())
    theses_result = await session.execute(select(Thesis).order_by(Thesis.name))
    theses = list(theses_result.scalars().all())
    return templates.TemplateResponse(
        request,
        "partials/positions_table.html",
        {"groups": group_positions(positions), "theses": theses},
    )
