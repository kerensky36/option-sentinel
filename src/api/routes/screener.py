"""Screener routes — stateless, no DB."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.api.deps import get_schwab_client
from src.api.main import templates
from src.services.covered_call_screener import run_screener

router = APIRouter()


@router.get("/screener", response_class=HTMLResponse)
async def screener(request: Request):
    """Render the screener shell page. Results loaded on demand via Refresh button."""
    setup_required = not bool(os.environ.get("SCHWAB_CC_ACCOUNT_ID"))
    return templates.TemplateResponse(
        request,
        "screener.html",
        {
            "current_page": "covered_call_screener",
            "setup_required": setup_required,
        },
    )


@router.get("/api/screener/refresh")
async def screener_refresh(schwab_client=Depends(get_schwab_client)):
    """Fetch live covered-call recommendations and return as JSON array.

    The client sends Authorization: Bearer <token> with each request.
    This endpoint never logs the Authorization header value.

    Returns:
        JSON array of ScreenerResultView objects.
    """
    results = await run_screener(schwab_client)
    return JSONResponse(content=[r.model_dump(mode="json") for r in results])
