"""Quorum routes: vote (specs/018) and summary (specs/020 contracts/quorum-api-contract.md)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.deps import get_schwab_client
from src.api.main import limiter, log_security_event
from src.data.models import QuorumRequest, QuorumSummary, SummaryRequest
from src.services import quorum_agents
from src.services.quorum_agents import build_position_context, quorum_configured, run_quorum
from src.services.quorum_summary import TokenRejected as SummaryTokenRejected
from src.services.quorum_summary import seal_key, summarise, unseal
from src.services.schwab_client import TokenCheckFailed, TokenRejected, verify_token

router = APIRouter(prefix="/api")

QUORUM_TIMEOUT_SECONDS = 60.0
SUMMARY_TIMEOUT_SECONDS = 15.0
MAX_SUMMARY_BODY_BYTES = 24 * 1024
MAX_BODY_BYTES = 16 * 1024
MAX_DATA_AGE = timedelta(minutes=15)
MAX_CLOCK_SKEW = timedelta(minutes=2)
MAX_FIELDS = 20  # unknown keys are caller-chosen text: bound what is reflected back
MAX_FIELD_CHARS = 64


def _invalid(fields: list[str] | None = None) -> JSONResponse:
    """422 that names failing locations only — never the submitted values (D-106)."""
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid quorum request", "fields": fields or []},
    )


@router.post("/quorum/vote")
@limiter.limit("5/minute")
async def quorum_vote(request: Request, schwab_client=Depends(get_schwab_client)):
    """Ask the five-seat quorum to vote CLOSE / HOLD / ROLL on one position.

    The browser sends the legs it already holds from its last positions refresh;
    the server validates them strictly, checks freshness, confirms the token with
    Schwab, and never re-fetches the position (FR-110). Only allow-listed fields
    reach the model — never the token or any account identifier (FR-113).
    """
    if not quorum_configured():
        raise HTTPException(status_code=503, detail="Quorum is not configured on this server")

    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        return _invalid()
    try:
        body = QuorumRequest.model_validate_json(raw)
    except ValidationError as exc:
        locations = [".".join(str(p) for p in err["loc"])[:MAX_FIELD_CHARS] for err in exc.errors()]
        return _invalid(locations[:MAX_FIELDS])

    now = datetime.now(timezone.utc)
    if not now - MAX_DATA_AGE <= body.as_of <= now + MAX_CLOCK_SKEW:
        raise HTTPException(
            status_code=409, detail="Position data is stale — refresh positions and try again"
        )

    try:
        await verify_token(schwab_client)
    except TokenRejected:
        log_security_event("401_invalid_token", request)
        raise HTTPException(status_code=401, detail="Missing or invalid token") from None
    except TokenCheckFailed:
        log_security_event("schwab_api_error", request)
        raise HTTPException(status_code=502, detail="Could not verify Schwab login") from None

    try:
        ctx = build_position_context(body.legs, as_of=body.as_of)
    except ValueError:
        return _invalid()

    try:
        result = await asyncio.wait_for(
            run_quorum(ctx, model=quorum_agents.default_model()), QUORUM_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Quorum timed out") from exc

    return JSONResponse(content=result.model_dump(mode="json"))


@router.post("/quorum/summary")
@limiter.limit("5/minute")
async def quorum_summary(request: Request, schwab_client=Depends(get_schwab_client)):
    """Summarise a vote result the server itself produced (specs/020 FR-306, FR-306a).

    The body carries only the opaque summary token from the vote response. It is
    verified by HMAC and age, so nothing is stored between the two requests and a
    browser-edited result never reaches the model.
    """
    key = seal_key()
    if not quorum_configured() or key is None:
        raise HTTPException(status_code=503, detail="Quorum summary is not configured on this server")

    raw = await request.body()
    if len(raw) > MAX_SUMMARY_BODY_BYTES:
        return JSONResponse(status_code=422, content={"detail": "Invalid summary request", "fields": []})
    try:
        body = SummaryRequest.model_validate_json(raw)
    except ValidationError as exc:
        locations = [".".join(str(p) for p in err["loc"])[:MAX_FIELD_CHARS] for err in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid summary request", "fields": locations[:MAX_FIELDS]},
        )

    try:
        await verify_token(schwab_client)
    except TokenRejected:
        log_security_event("401_invalid_token", request)
        raise HTTPException(status_code=401, detail="Missing or invalid token") from None
    except TokenCheckFailed:
        log_security_event("schwab_api_error", request)
        raise HTTPException(status_code=502, detail="Could not verify Schwab login") from None

    try:
        payload = unseal(body.summary_token, key=key, now=datetime.now(timezone.utc))
    except SummaryTokenRejected:
        # One body for every failure: never say which check failed.
        return JSONResponse(status_code=403, content={"detail": "Summary request rejected"})

    try:
        summary = await asyncio.wait_for(
            summarise(payload, model=quorum_agents.default_model()), SUMMARY_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        summary = QuorumSummary(status="unavailable")

    return JSONResponse(content=summary.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
