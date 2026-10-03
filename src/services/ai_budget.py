"""Service-wide daily cap on AI analyses and single-use summary tokens (specs/022).

Both are held in this process's memory only and carry no user identifier
(constitution Principle I): one counter for the whole service, and the MACs of
summary tokens this server issued. Cloud Run runs a single instance
(--max-instances 1), so the count is the service's count; a restart resets it,
and the billing budget is the backstop outside the app.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

_log = logging.getLogger(__name__)

DEFAULT_DAILY_CAP = 50
DAY_ZONE = ZoneInfo("America/New_York")

_lock = threading.Lock()
_day: date | None = None
_used = 0
_tokens: dict[str, datetime] = {}  # token MAC → expiry


def daily_cap() -> int:
    """QUORUM_DAILY_CAP, or the default when unset or not a non-negative integer."""
    raw = os.getenv("QUORUM_DAILY_CAP")
    if raw is None:
        return DEFAULT_DAILY_CAP
    if raw.strip().isdigit():
        return int(raw)
    _log.warning("QUORUM_DAILY_CAP is not a non-negative integer; using %d", DEFAULT_DAILY_CAP)
    return DEFAULT_DAILY_CAP


def paused() -> bool:
    """QUORUM_DAILY_CAP=0 is the kill switch for every AI route."""
    return daily_cap() == 0


def _today(now: datetime) -> date:
    return now.astimezone(DAY_ZONE).date()


def _roll(now: datetime) -> None:
    global _day, _used
    today = _today(now)
    if today != _day:
        _day, _used = today, 0


def try_start(now: datetime) -> bool:
    """Count one AI analysis if today's cap allows it."""
    global _used
    with _lock:
        _roll(now)
        if _used >= daily_cap():
            return False
        _used += 1
        return True


def used_today(now: datetime) -> int:
    with _lock:
        _roll(now)
        return _used


def seconds_until_reset(now: datetime) -> int:
    """Seconds until the next midnight in America/New_York."""
    local = now.astimezone(DAY_ZONE)
    midnight = datetime.combine(local.date() + timedelta(days=1), time(0), tzinfo=DAY_ZONE)
    return max(1, int((midnight - local).total_seconds()))


def claim_token(token_id: str, expires_at: datetime, now: datetime) -> bool:
    """Accept a summary token once; records are dropped when the token expires."""
    with _lock:
        for key in [k for k, exp in _tokens.items() if exp <= now]:
            del _tokens[key]
        if token_id in _tokens:
            return False
        _tokens[token_id] = expires_at
        return True


def tracked_tokens() -> int:
    with _lock:
        return len(_tokens)


def reset() -> None:
    """Clear all state (tests)."""
    global _day, _used
    with _lock:
        _day, _used = None, 0
        _tokens.clear()
