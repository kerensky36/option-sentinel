"""Positions routes — stateless, no DB."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.deps import get_schwab_client
from src.services.schwab_client import fetch_positions_and_greeks

router = APIRouter(prefix="/api")


@router.get("/positions/refresh")
async def refresh_positions(schwab_client=Depends(get_schwab_client)):
    """Fetch live positions + Greeks from Schwab and return as JSON array.

    The client sends Authorization: Bearer <token> with each request.
    This endpoint never logs the Authorization header value.

    Returns:
        JSON array of PositionView objects.
    """
    positions = await fetch_positions_and_greeks(schwab_client)
    # Serialise Pydantic models to JSON-safe dicts
    return JSONResponse(content=[p.model_dump(mode="json") for p in positions])
