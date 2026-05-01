from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api._group_helpers import load_groups_and_theses
from src.api.deps import get_session
from src.api.main import templates
from src.data.models import ExitGoal, Position

router = APIRouter()


@router.post("/positions/{position_id}/exit-goal", response_class=HTMLResponse)
async def upsert_exit_goal(
    request: Request,
    position_id: str,
    profit_target_pct: str = Form(""),
    dte_threshold: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Position).where(Position.id == position_id))
    pos = result.scalar_one_or_none()
    if not pos:
        return HTMLResponse("Position not found", status_code=404)

    goal_result = await session.execute(
        select(ExitGoal).where(ExitGoal.position_id == position_id)
    )
    goal = goal_result.scalar_one_or_none()

    ptp = float(profit_target_pct) / 100.0 if profit_target_pct.strip() else None
    dte = int(dte_threshold) if dte_threshold.strip() else None

    if goal is None:
        goal = ExitGoal(position_id=position_id, profit_target_pct=ptp, dte_threshold=dte)
        session.add(goal)
    else:
        goal.profit_target_pct = ptp
        goal.dte_threshold = dte

    await session.commit()

    groups, theses = await load_groups_and_theses(session)
    return templates.TemplateResponse(
        request,
        "partials/positions_table.html",
        {"groups": groups, "theses": theses},
    )
