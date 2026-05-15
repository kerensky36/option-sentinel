"""Accounts route — returns all Schwab accounts for the current Bearer token."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_schwab_client

router = APIRouter(prefix="/api")


def _mask_account_number(account_number: str, all_numbers: list[str]) -> str:
    """Return '...' + shortest unique suffix of account_number among all_numbers."""
    for suffix_len in range(4, len(account_number) + 1):
        suffix = account_number[-suffix_len:]
        if sum(1 for n in all_numbers if n.endswith(suffix)) == 1:
            return f"...{suffix}"
    return f"...{account_number}"


@router.get("/accounts")
async def list_accounts_endpoint(schwab_client=Depends(get_schwab_client)):
    """Return all Schwab accounts accessible via the current Bearer token.

    Account numbers are masked (last 4 digits minimum, disambiguated if needed).
    hashValue fields are never logged by this endpoint.
    """
    from src.auth.account_resolver import list_accounts
    try:
        accounts = await list_accounts(schwab_client)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to fetch accounts") from exc

    all_numbers = [a.get("accountNumber", "") for a in accounts]
    return [
        {
            "accountNumber": _mask_account_number(a.get("accountNumber", ""), all_numbers),
            "hashValue": a.get("hashValue", ""),
        }
        for a in accounts
    ]
