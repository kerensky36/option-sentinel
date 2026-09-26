"""Macro news voting quorum route (specs/017, contracts/quorum-api-contract.md)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.deps import get_schwab_client
from src.api.main import limiter, log_security_event
from src.data.models import QuorumRequest
from src.services import quorum_agents
from src.services.news_feeds import fetch_headlines
from src.services.quorum_agents import build_position_context, quorum_configured, run_quorum
from src.services.schwab_client import fetch_positions_and_greeks

router = APIRouter(prefix="/api")

QUORUM_TIMEOUT_SECONDS = 60.0


@router.post("/quorum/vote")
@limiter.limit("5/minute")
async def quorum_vote(
    request: Request,
    body: QuorumRequest,
    schwab_client=Depends(get_schwab_client),
):
    """Ask the five-seat analyst quorum to vote CLOSE / HOLD / ROLL on one position.

    The position is re-fetched from Schwab with the caller's own token; client-supplied
    prices are never trusted (FR-002). Only allow-listed position and market fields reach
    the model — never the token or account hash (Constitution v3.3.0).
    """
    if not quorum_configured():
        raise HTTPException(status_code=503, detail="Quorum is not configured on this server")

    try:
        positions = await fetch_positions_and_greeks(schwab_client, account_hash=body.account_hash)
    except ValueError as exc:
        log_security_event("422_invalid_account_hash", request)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    by_symbol = {p.symbol: p for p in positions}
    if any(s not in by_symbol for s in body.symbols):
        raise HTTPException(
            status_code=404, detail="Position not found — refresh positions and try again"
        )

    try:
        ctx = build_position_context([by_symbol[s] for s in body.symbols])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    async def _run():
        headlines = await fetch_headlines(ctx.underlying_symbol)
        return await run_quorum(ctx, headlines, model=quorum_agents.default_model())

    try:
        result = await asyncio.wait_for(_run(), QUORUM_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Quorum timed out") from exc

    return JSONResponse(content=result.model_dump(mode="json"))
