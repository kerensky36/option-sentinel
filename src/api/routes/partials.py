from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api._group_helpers import load_groups_and_theses, load_thesis_cards
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


@router.get("/thesis-cards", response_class=HTMLResponse)
async def thesis_cards_partial(request: Request, session: AsyncSession = Depends(get_session)):
    thesis_cards = await load_thesis_cards(session)
    return templates.TemplateResponse(
        request,
        "partials/thesis_cards.html",
        {"thesis_cards": thesis_cards},
    )
