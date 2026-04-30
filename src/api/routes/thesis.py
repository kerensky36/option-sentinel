from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api._group_helpers import load_groups_and_theses
from src.api.deps import get_session
from src.api.main import templates
from src.data.models import Position, Thesis, ThesisTemplateType
from src.services.thesis_health import upsert_snapshot

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
    ids = [pid.strip() for pid in position_ids.split(",") if pid.strip()]
    tid = thesis_id if thesis_id != "__none__" else None

    for pid in ids:
        result = await session.execute(select(Position).where(Position.id == pid))
        pos = result.scalar_one_or_none()
        if pos:
            pos.thesis_id = tid
            await session.flush()
            if tid:
                await upsert_snapshot(session, pos)

    await session.commit()

    groups, theses = await load_groups_and_theses(session)
    return templates.TemplateResponse(
        request,
        "partials/positions_table.html",
        {"groups": groups, "theses": theses},
    )
