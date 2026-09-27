"""Unit tests for _fetch_greeks in src/services/schwab_client.py.

Tests are written RED-first (Principle IV). They must all fail before the
asyncio.gather implementation is applied in Phase 3.
"""
from __future__ import annotations

import asyncio

import pytest
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

    async def get_option_chain(symbol, **kwargs):
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

    async def get_option_chain(symbol, **kwargs):
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


# ---------------------------------------------------------------------------
# specs/018 T006 — fetch_realised_vols (research D-102)
# ---------------------------------------------------------------------------

import logging
from datetime import datetime, timedelta, timezone


def _candles(n=40, start=100.0, step=0.01):
    closes = [start * (1 + step * ((-1) ** i)) for i in range(n)]
    return {"candles": [{"close": c} for c in closes], "empty": False}


def _history_client(by_symbol: dict, *, status: dict | None = None, raise_for: set | None = None):
    status = status or {}
    raise_for = raise_for or set()
    calls = []

    async def get_price_history_every_day(symbol, **kwargs):
        calls.append((symbol, kwargs))
        if symbol in raise_for:
            raise ConnectionError("boom")
        resp = MagicMock()
        resp.status_code = status.get(symbol, 200)
        resp.json.return_value = by_symbol.get(symbol, {"candles": [], "empty": True})
        return resp

    client = MagicMock()
    client.get_price_history_every_day = get_price_history_every_day
    return client, calls


async def test_fetch_realised_vols_one_call_per_underlying():
    from src.services.schwab_client import fetch_realised_vols
    client, calls = _history_client({"SPY": _candles(), "QQQ": _candles()})
    result = await fetch_realised_vols(client, {"SPY", "QQQ"})
    assert sorted(c[0] for c in calls) == ["QQQ", "SPY"]
    assert result["SPY"] is not None and result["SPY"] > 0
    start = calls[0][1]["start_datetime"]
    assert abs((datetime.now(timezone.utc) - start) - timedelta(days=60)) < timedelta(minutes=5)


async def test_fetch_realised_vols_index_symbol_map():
    from src.services.schwab_client import fetch_realised_vols
    client, calls = _history_client({"$SPX": _candles(), "$NDX": _candles(), "$RUT": _candles(), "$VIX": _candles()})
    result = await fetch_realised_vols(client, {"SPX", "SPXW", "NDX", "RUT", "VIX"})
    assert {c[0] for c in calls} == {"$SPX", "$NDX", "$RUT", "$VIX"}
    assert all(result[u] is not None for u in ("SPX", "SPXW", "NDX", "RUT", "VIX"))


async def test_fetch_realised_vols_errors_become_none_and_log_security_event(caplog):
    from src.services.schwab_client import fetch_realised_vols
    client, _ = _history_client(
        {"AAPL": _candles(n=5)},  # too short → None, no security event
        status={"MSFT": 503},
        raise_for={"TSLA"},
    )
    with caplog.at_level(logging.WARNING, logger="security"):
        result = await fetch_realised_vols(client, {"AAPL", "MSFT", "TSLA", "EMPTY"})
    assert result == {"AAPL": None, "MSFT": None, "TSLA": None, "EMPTY": None}
    lines = [r.getMessage() for r in caplog.records if r.name == "security"]
    assert any("schwab_api_error source=price_history status=503" in m for m in lines)
    assert any("schwab_api_error source=price_history status=transport" in m for m in lines)
    assert not any(sym in m for m in lines for sym in ("AAPL", "MSFT", "TSLA"))


# ---------------------------------------------------------------------------
# specs/018 T007 — fetch_positions_and_greeks adds as_of + fundamentals
# ---------------------------------------------------------------------------

async def test_fetch_positions_and_greeks_adds_as_of_and_fundamentals():
    responses = {"AAPL": _chain(AAPL_SYM, underlying_price=190.0, delta=0.40)}
    client = _client(responses)
    hist_client, _ = _history_client({"AAPL": _candles()})
    client.get_price_history_every_day = hist_client.get_price_history_every_day

    account_data = {
        "securitiesAccount": {
            "positions": [
                _raw_position(AAPL_SYM, long_qty=0, short_qty=1, market_value=-320.0, average_price=3.20),
                _raw_position("AAPL  260618P00180000", long_qty=1, short_qty=0, market_value=150.0, average_price=1.20),
            ],
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

    assert len(views) == 2
    assert views[0].as_of is not None and views[0].as_of.tzinfo is not None
    assert views[0].as_of == views[1].as_of
    assert views[0].fundamentals.realised_volatility is not None
    assert views[0].fundamentals.position_delta == pytest.approx(0.40 * -1 * 100)
    assert views[0].fundamentals.moneyness_pct is not None


async def test_fetch_positions_and_greeks_runs_price_history_concurrently_with_chain():
    responses = {"AAPL": _chain(AAPL_SYM, underlying_price=190.0, delta=0.40)}
    active = 0
    max_active = 0

    async def get_option_chain(symbol, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        resp = MagicMock()
        resp.json.return_value = responses[symbol]
        return resp

    async def get_price_history_every_day(symbol, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _candles()
        return resp

    client = MagicMock()
    client.get_option_chain = get_option_chain
    client.get_price_history_every_day = get_price_history_every_day
    account_resp = MagicMock()
    account_resp.json.return_value = {
        "securitiesAccount": {"positions": [_raw_position(AAPL_SYM, 0, 1, -320.0, 3.20)]}
    }
    client.get_account = AsyncMock(return_value=account_resp)

    with patch(
        "src.auth.account_resolver.list_accounts",
        new=AsyncMock(return_value=[{"hashValue": "hash1"}]),
    ):
        await fetch_positions_and_greeks(client)

    assert max_active == 2


# ---------------------------------------------------------------------------
# specs/018 T038 — narrowed option-chain request (FR-108, D-110, SC-108)
# ---------------------------------------------------------------------------

from datetime import date as _date


def _chain_multi(contracts: list[tuple[str, float]], underlying_price: float = 100.0) -> dict:
    """Chain response holding each (occ_symbol, delta) under its own expiry/strike."""
    data = {"underlyingPrice": underlying_price, "callExpDateMap": {}, "putExpDateMap": {}}
    for sym, delta in contracts:
        side = "putExpDateMap" if sym.strip()[-9].upper() == "P" else "callExpDateMap"
        data[side].setdefault("2026-06-18:32", {}).setdefault(sym[-8:], []).append({
            "symbol": sym, "delta": delta, "gamma": 0.01, "theta": -0.05, "vega": 0.2, "volatility": 25.0,
        })
    return data


def _recording_client(full: dict[str, dict], narrowed: dict[str, dict] | None = None):
    """narrowed[u] is returned when the call carries from_date; full[u] otherwise."""
    calls = []

    async def get_option_chain(symbol, **kwargs):
        calls.append((symbol, kwargs))
        source = narrowed if (narrowed is not None and "from_date" in kwargs) else full
        resp = MagicMock()
        resp.json.return_value = source.get(symbol, {"callExpDateMap": {}, "putExpDateMap": {}})
        return resp

    client = MagicMock()
    client.get_option_chain = get_option_chain
    client.Options.ContractType.ALL = "ALL"
    client.Options.ContractType.CALL = "CALL"
    client.Options.ContractType.PUT = "PUT"
    return client, calls


async def test_fetch_greeks_narrows_to_single_held_contract():
    client, calls = _recording_client({"SPY": _chain(SPY_SYM, 560.0, 0.55)})
    result = await _fetch_greeks([SPY_SYM], client)
    assert len(calls) == 1
    symbol, kwargs = calls[0]
    assert symbol == "SPY"
    assert kwargs["from_date"] == _date(2026, 6, 18)
    assert kwargs["to_date"] == _date(2026, 6, 18)
    assert kwargs["strike"] == 600.0
    assert kwargs["contract_type"] == "CALL"
    assert kwargs["include_underlying_quote"] is True
    assert result[SPY_SYM]["delta"] == 0.55


async def test_fetch_greeks_date_range_and_no_strike_for_multiple_strikes():
    near = "SPY   260618P00500000"
    far = "SPY   260918C00650000"
    client, calls = _recording_client({"SPY": _chain_multi([(near, -0.2), (far, 0.3)])})
    await _fetch_greeks([near, far], client)
    _, kwargs = calls[0]
    assert kwargs["from_date"] == _date(2026, 6, 18)
    assert kwargs["to_date"] == _date(2026, 9, 18)
    assert "strike" not in kwargs
    assert kwargs["contract_type"] == "ALL"


async def test_fetch_greeks_uses_occ_parser_for_underlying():
    sym = "SPXW  260618P05500000"
    client, calls = _recording_client({"SPXW": _chain_multi([(sym, -0.1)])})
    await _fetch_greeks([sym], client)
    assert calls[0][0] == "SPXW"


async def test_fetch_greeks_full_chain_retry_once_for_missing_symbol():
    other = "SPY   260618C00610000"
    full = {"SPY": _chain_multi([(SPY_SYM, 0.55), (other, 0.40)])}
    narrowed = {"SPY": _chain_multi([(other, 0.40)])}  # held SPY_SYM missing from narrowed reply
    client, calls = _recording_client(full, narrowed)
    result = await _fetch_greeks([SPY_SYM], client)
    assert len(calls) == 2
    assert "from_date" in calls[0][1]
    assert "from_date" not in calls[1][1] and calls[1][1]["contract_type"] == "ALL"
    assert result[SPY_SYM]["delta"] == 0.55


async def test_fetch_greeks_narrowed_matches_full_chain_values():
    """SC-108: identical Greeks whether served from the narrowed or the full chain."""
    held = [SPY_SYM, "SPY   260618P00550000"]
    chain = _chain_multi([(held[0], 0.55), (held[1], -0.25)])
    narrowed_client, _ = _recording_client({"SPY": chain})
    full_client, _ = _recording_client({"SPY": chain}, narrowed={})  # narrowed empty → full retry
    assert await _fetch_greeks(held, narrowed_client) == await _fetch_greeks(held, full_client)
