from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api._group_helpers import load_groups_and_theses
from src.api.deps import get_session
from src.api.main import templates

router = APIRouter(prefix="/partials")


@router.get("/positions", response_class=HTMLResponse)
async def positions_partial(request: Request, session: AsyncSession = Depends(get_session)):
    groups, theses = await load_groups_and_theses(session)
    return templates.TemplateResponse(
        request,
        "partials/positions_table.html",
        {"groups": groups, "theses": theses},
    )
