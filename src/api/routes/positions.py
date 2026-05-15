"""Positions routes — stateless, no DB."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.deps import get_schwab_client
from src.api.main import limiter, log_security_event
from src.services.schwab_client import fetch_positions_and_greeks

router = APIRouter(prefix="/api")


@router.get("/positions/refresh")
@limiter.limit("60/minute")
async def refresh_positions(
    request: Request,
    account_hash: str | None = None,
    schwab_client=Depends(get_schwab_client),
):
    """Fetch live positions + Greeks from Schwab and return as JSON array.

    The client sends Authorization: Bearer <token> with each request.
    This endpoint never logs the Authorization header value.

    Args:
        account_hash: Optional Schwab account hash to use. If absent, uses the first
            account on the token. Returns 422 if provided hash is not found.

    Returns:
        JSON array of PositionView objects.
    """
    try:
        positions = await fetch_positions_and_greeks(schwab_client, account_hash=account_hash)
    except ValueError as exc:
        log_security_event("422_invalid_account_hash", request)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse(content=[p.model_dump(mode="json") for p in positions])
