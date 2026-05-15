"""Screener routes — stateless, no DB."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.api.deps import get_schwab_client
from src.api.main import templates
from src.services.covered_call_screener import run_screener

router = APIRouter()


@router.get("/screener", response_class=HTMLResponse)
async def screener(request: Request):
    """Render the screener shell page. Results loaded on demand via Refresh button."""
    return templates.TemplateResponse(
        request,
        "screener.html",
        {"current_page": "covered_call_screener"},
    )


@router.get("/api/screener/refresh")
async def screener_refresh(
    account_hash: str | None = None,
    schwab_client=Depends(get_schwab_client),
):
    """Fetch live covered-call recommendations and return as JSON array.

    The client sends Authorization: Bearer <token> with each request.
    This endpoint never logs the Authorization header value.

    Args:
        account_hash: Optional Schwab account hash to use. If absent, uses the first
            account on the token. Returns 422 if provided hash is not found.

    Returns:
        JSON array of ScreenerResultView objects.
    """
    try:
        results = await run_screener(schwab_client, account_hash=account_hash)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse(content=[r.model_dump(mode="json") for r in results])
