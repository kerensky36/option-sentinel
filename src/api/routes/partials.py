"""Partials routes — stateless shell renders for HTMX fragments.

These routes are now minimal since all data fetching is done client-side
via /api/positions/refresh and /api/screener/refresh.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.api.main import templates

router = APIRouter(prefix="/partials")


@router.get("/positions", response_class=HTMLResponse)
async def positions_partial(request: Request):
    """Empty positions table partial — data is loaded via client-side JS."""
    return templates.TemplateResponse(
        request,
        "partials/positions_table.html",
        {},
    )
