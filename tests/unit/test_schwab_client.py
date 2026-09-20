"""Unit tests for _fetch_greeks in src/services/schwab_client.py.

Tests are written RED-first (Principle IV). They must all fail before the
asyncio.gather implementation is applied in Phase 3.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.schwab_client import _fetch_greeks, fetch_positions_and_greeks

# ---------------------------------------------------------------------------
# OCC symbols used across tests
# ---------------------------------------------------------------------------
QQQ_SYM = "QQQ   260618P00650000"
SPY_SYM = "SPY   260618C00600000"
AAPL_SYM = "AAPL  260618C00200000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chain(occ_symbol: str, underlying_price: float, delta: float) -> dict:
    """Build a minimal option chain response containing one option."""
    is_put = occ_symbol.strip()[-9].upper() == "P"
    side = "putExpDateMap" if is_put else "callExpDateMap"
    other = "callExpDateMap" if is_put else "putExpDateMap"
    return {
        "underlyingPrice": underlying_price,
        side: {
            "2026-06-18:32": {
                "650.0": [{
                    "symbol": occ_symbol,
                    "delta": delta,
                    "gamma": 0.01,
                    "theta": -0.05,
                    "vega": 0.20,
                    "volatility": 25.0,
                }]
            }
        },
        other: {},
    }


def _client(responses: dict[str, dict], *, raise_for: set[str] | None = None) -> MagicMock:
    """Return a mock Schwab client. `responses` maps underlying → chain dict.
    `raise_for` is a set of underlying symbols whose fetch should raise."""
    raise_for = raise_for or set()

    async def get_option_chain(symbol, contract_type, include_underlying_quote):
        if symbol in raise_for:
            raise ConnectionError(f"simulated error for {symbol}")
        data = responses.get(symbol, {"underlyingPrice": 0, "callExpDateMap": {}, "putExpDateMap": {}})
        resp = MagicMock()
        resp.json.return_value = data
        return resp

    client = MagicMock()
    client.get_option_chain = get_option_chain
    client.Options.ContractType.ALL = "ALL"
    return client


# ---------------------------------------------------------------------------
# T006: Edge case — empty symbol list
# ---------------------------------------------------------------------------

async def test_fetch_greeks_empty_symbols_returns_empty_dict():
    """Empty input returns {} immediately; get_option_chain is never called."""
    calls = []

    async def get_option_chain(**kwargs):
        calls.append(kwargs)

    client = MagicMock()
    client.get_option_chain = get_option_chain

    result = await _fetch_greeks([], client)

    assert result == {}
    assert calls == []


# ---------------------------------------------------------------------------
# T004: Correctness — returned Greeks match API values
# ---------------------------------------------------------------------------

async def test_fetch_greeks_returns_correct_values():
    """Greeks values in the returned dict match the mocked API response."""
    responses = {
        "QQQ": _chain(QQQ_SYM, underlying_price=450.0, delta=-0.30),
        "SPY": _chain(SPY_SYM, underlying_price=560.0, delta=0.55),
    }
    client = _client(responses)
    result = await _fetch_greeks([QQQ_SYM, SPY_SYM], client)

    assert QQQ_SYM in result
    assert abs(result[QQQ_SYM]["delta"] - (-0.30)) < 1e-9
    assert abs(result[QQQ_SYM]["underlying_price"] - 450.0) < 1e-9
    assert abs(result[QQQ_SYM]["gamma"] - 0.01) < 1e-9

    assert SPY_SYM in result
    assert abs(result[SPY_SYM]["delta"] - 0.55) < 1e-9
    assert abs(result[SPY_SYM]["underlying_price"] - 560.0) < 1e-9


# ---------------------------------------------------------------------------
# T005: Failure isolation — one bad underlying does not block others
# ---------------------------------------------------------------------------

async def test_fetch_greeks_one_failure_does_not_block_others():
    """A network error on one underlying leaves other underlyings' Greeks intact."""
    responses = {
        "QQQ": _chain(QQQ_SYM, underlying_price=450.0, delta=-0.30),
        "AAPL": _chain(AAPL_SYM, underlying_price=190.0, delta=0.40),
    }
    client = _client(responses, raise_for={"SPY"})
    result = await _fetch_greeks([QQQ_SYM, SPY_SYM, AAPL_SYM], client)

    assert QQQ_SYM in result, "QQQ Greeks absent despite SPY being the only failure"
    assert AAPL_SYM in result, "AAPL Greeks absent despite SPY being the only failure"
    assert SPY_SYM not in result, "SPY Greeks should be absent (fetch raised)"


# ---------------------------------------------------------------------------
# T003: Concurrency — all get_option_chain calls fire simultaneously
# ---------------------------------------------------------------------------

async def test_fetch_greeks_issues_calls_concurrently():
    """All get_option_chain calls for distinct underlyings run concurrently.

    The mock increments an active-call counter before yielding to the event loop.
    With asyncio.gather, all three coroutines reach the counter increment before
    any sleep(0) resolves, so max_active == 3. With a serial loop max_active == 1.
    """
    symbols = [QQQ_SYM, SPY_SYM, AAPL_SYM]
    active = 0
    max_active = 0

    async def get_option_chain(symbol, contract_type, include_underlying_quote):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0)  # yield — lets other coroutines start with gather
        active -= 1
        resp = MagicMock()
        resp.json.return_value = {"underlyingPrice": 0, "callExpDateMap": {}, "putExpDateMap": {}}
        return resp

    client = MagicMock()
    client.get_option_chain = get_option_chain
    client.Options.ContractType.ALL = "ALL"

    await _fetch_greeks(symbols, client)

    assert max_active == 3, (
        f"Expected all 3 get_option_chain calls to run concurrently "
        f"(max_active=3), but max_active={max_active}. "
        f"A serial loop would give max_active=1."
    )


# ---------------------------------------------------------------------------
# 016-T008/T009: underlying_price flows from the option chain into PositionView
# ---------------------------------------------------------------------------

def _raw_position(symbol: str, long_qty: int, short_qty: int, market_value: float, average_price: float) -> dict:
    return {
        "instrument": {"assetType": "OPTION", "symbol": symbol, "underlyingSymbol": symbol[:4].strip()},
        "longQuantity": long_qty,
        "shortQuantity": short_qty,
        "marketValue": market_value,
        "averagePrice": average_price,
    }


async def test_fetch_positions_and_greeks_populates_underlying_price():
    """PositionView.underlying_price comes from the same option-chain quote
    already used for Greeks — no new Schwab API call, per research.md D-001."""
    responses = {"AAPL": _chain(AAPL_SYM, underlying_price=190.0, delta=0.40)}
    client = _client(responses)

    account_data = {
        "securitiesAccount": {
            "positions": [_raw_position(AAPL_SYM, long_qty=0, short_qty=1, market_value=-320.0, average_price=-3.20)],
        }
    }
    account_resp = MagicMock()
    account_resp.json.return_value = account_data
    client.get_account = AsyncMock(return_value=account_resp)
    client.Account.Fields.POSITIONS = "positions"

    with patch(
        "src.auth.account_resolver.list_accounts",
        new=AsyncMock(return_value=[{"hashValue": "hash1"}]),
    ):
        views = await fetch_positions_and_greeks(client)

    assert len(views) == 1
    assert views[0].underlying_price == Decimal("190.0")


async def test_fetch_positions_and_greeks_underlying_price_none_when_unavailable():
    """If the option chain never returns underlyingPrice, PositionView.underlying_price
    is None rather than erroring (matches the graceful-degradation pattern used
    elsewhere for optional fields)."""
    client = _client({})  # no chain data registered for any underlying

    account_data = {
        "securitiesAccount": {
            "positions": [_raw_position(AAPL_SYM, long_qty=0, short_qty=1, market_value=-320.0, average_price=-3.20)],
        }
    }
    account_resp = MagicMock()
    account_resp.json.return_value = account_data
    client.get_account = AsyncMock(return_value=account_resp)
    client.Account.Fields.POSITIONS = "positions"

    with patch(
        "src.auth.account_resolver.list_accounts",
        new=AsyncMock(return_value=[{"hashValue": "hash1"}]),
    ):
        views = await fetch_positions_and_greeks(client)

    assert len(views) == 1
    assert views[0].underlying_price is None
