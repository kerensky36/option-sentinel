from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session
from src.api.main import templates
from src.data.models import Position, PositionStatus, Thesis, ThesisTemplateType

router = APIRouter()


@router.post("/thesis", response_class=HTMLResponse)
async def create_thesis(
    request: Request,
    name: str = Form(...),
    template_type: str = Form(...),
    description: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    thesis = Thesis(
        name=name.strip(),
        template_type=ThesisTemplateType(template_type),
        description=description.strip() or None,
    )
    session.add(thesis)
    await session.commit()
    return RedirectResponse("/", status_code=303)


@router.post("/partials/assign-thesis", response_class=HTMLResponse)
async def assign_thesis(
    request: Request,
    position_ids: str = Form(...),
    thesis_id: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """Assign a thesis to all legs in a group (comma-separated position IDs)."""
    ids = [pid.strip() for pid in position_ids.split(",") if pid.strip()]
    tid = thesis_id if thesis_id != "__none__" else None

    for pid in ids:
        result = await session.execute(select(Position).where(Position.id == pid))
        pos = result.scalar_one_or_none()
        if pos:
            pos.thesis_id = tid
    await session.commit()

    # Return refreshed positions partial
    from src.services.position_groups import group_positions
    from src.data.models import PositionStatus
    from sqlalchemy.orm import selectinload

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
