from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api._group_helpers import load_groups_and_theses, load_thesis_cards
from src.api.deps import get_session
from src.api.main import templates
from src.data.models import BinaryEventFlag
from src.services import poll_scheduler

router = APIRouter()


async def _get_binary_flag(session: AsyncSession) -> BinaryEventFlag | None:
    result = await session.execute(select(BinaryEventFlag).where(BinaryEventFlag.id == 1))
    return result.scalar_one_or_none()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    groups, theses = await load_groups_and_theses(session)
    thesis_cards = await load_thesis_cards(session)
    binary_flag = await _get_binary_flag(session)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "groups": groups,
            "theses": theses,
            "thesis_cards": thesis_cards,
            "binary_flag": binary_flag,
            "last_poll_at": poll_scheduler.last_poll_at,
            "current_page": "thesis_monitor",
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
