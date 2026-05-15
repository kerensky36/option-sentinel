"""Resolve a human-readable Schwab account number to its API hash value.

Schwab's API requires an encrypted hash, not the raw account number.
This module caches resolutions in memory for the process lifetime.
"""
from __future__ import annotations

import re

_cache: dict[str, str] = {}

_RAW_PATTERN = re.compile(r'^[\d\-]{4,15}$')


def _looks_like_raw_number(value: str) -> bool:
    """True if value looks like a human-readable account number (digits + dashes, ≤15 chars).
    Schwab hashes are 40+ alphanumeric chars."""
    return bool(_RAW_PATTERN.match(value))


async def resolve_account_hash(client, account_number_or_hash: str) -> str:
    """Return the API hash for the given account number or hash.

    If `account_number_or_hash` already looks like a hash (long alphanumeric),
    it is returned as-is. Otherwise, `get_account_numbers()` is called once and
    the result is cached for the lifetime of the process.
    """
    value = account_number_or_hash.strip()
    if not value:
        raise ValueError("Account number/hash is empty")

    if not _looks_like_raw_number(value):
        return value  # Already a hash

    if value in _cache:
        return _cache[value]

    resp = await client.get_account_numbers()
    entries = resp.json()

    # Build a normalised lookup: strip dashes from both sides for comparison
    normalised = value.replace("-", "")
    for entry in entries:
        raw = entry.get("accountNumber", "").replace("-", "")
        if raw == normalised:
            _cache[value] = entry["hashValue"]
            return entry["hashValue"]

    available = [e.get("accountNumber", "?") for e in entries]
    raise ValueError(
        f"Account '{account_number_or_hash}' not found. "
        f"Accounts on this token: {available}"
    )


async def list_accounts(client) -> list[dict]:
    """Return all accounts accessible via the current OAuth token."""
    resp = await client.get_account_numbers()
    return resp.json()
