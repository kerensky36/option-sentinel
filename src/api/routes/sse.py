import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

_listeners: list[asyncio.Queue] = []


async def notify_refresh(polled_at: datetime, position_count: int) -> None:
    payload = json.dumps({
        "polled_at": polled_at.isoformat(),
        "position_count": position_count,
    })
    dead = []
    for q in _listeners:
        try:
            q.put_nowait(("refresh", payload))
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _listeners.remove(q)


async def notify_re_auth() -> None:
    payload = json.dumps({"message": "Schwab refresh token expiring. Re-authenticate."})
    for q in _listeners:
        try:
            q.put_nowait(("re_auth_required", payload))
        except asyncio.QueueFull:
            pass


async def _event_generator(queue: asyncio.Queue):
    try:
        while True:
            event, data = await asyncio.wait_for(queue.get(), timeout=30)
            yield {"event": event, "data": data}
    except asyncio.TimeoutError:
        yield {"event": "ping", "data": ""}
    except asyncio.CancelledError:
        pass
    finally:
        if queue in _listeners:
            _listeners.remove(queue)


@router.get("/sse")
async def sse_stream():
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    _listeners.append(queue)

    async def generator():
        async for event in _event_generator(queue):
            yield event

    return EventSourceResponse(generator())
