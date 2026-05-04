import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.main import templates
from src.services.covered_call_screener import load_screener_results, refresh_and_cache

router = APIRouter()


@router.get("/screener", response_class=HTMLResponse)
async def screener(request: Request, session: AsyncSession = Depends(get_db)):
    setup_required = not bool(os.environ.get("SCHWAB_CC_ACCOUNT_ID"))
    candidates = []
    screener_error: str | None = None
    last_refreshed_at = None
    if not setup_required:
        try:
            candidates, last_refreshed_at = await load_screener_results(session)
        except Exception as exc:
            screener_error = str(exc)
    return templates.TemplateResponse(
        request,
        "screener.html",
        {
            "current_page": "covered_call_screener",
            "setup_required": setup_required,
            "candidates": candidates,
            "screener_error": screener_error,
            "last_refreshed_at": last_refreshed_at,
        },
    )


@router.post("/screener/refresh", response_class=HTMLResponse)
async def screener_refresh(request: Request, session: AsyncSession = Depends(get_db)):
    error: str | None = None
    candidates = []
    last_refreshed_at = None
    try:
        candidates, last_refreshed_at = await refresh_and_cache(session)
    except Exception as exc:
        error = str(exc)
    return templates.TemplateResponse(
        request,
        "partials/screener_table.html",
        {
            "candidates": candidates,
            "screener_error": error,
            "last_refreshed_at": last_refreshed_at,
        },
    )
