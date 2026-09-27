"""Stateless Schwab client helpers.

All functions return plain Pydantic model instances or dicts — no DB, no session.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from src.data.models import PositionView
from src.services.fundamentals import leg_fundamentals, realised_volatility
from src.services.greeks_service import RISK_FREE_RATE, build_greeks

_security_log = logging.getLogger("security")

PRICE_HISTORY_DAYS = 60

# Schwab quotes cash indices with a "$" prefix (research D-102).
_INDEX_SYMBOLS = {
    "SPX": "$SPX", "SPXW": "$SPX", "NDX": "$NDX", "NDXP": "$NDX",
    "RUT": "$RUT", "RUTW": "$RUT", "VIX": "$VIX", "VIXW": "$VIX",
}

def _parse_occ_symbol(symbol: str) -> tuple[str, date, str, float] | None:
    """Parse OCC symbol e.g. 'QQQ   260618P00650000' → (underlying, expiry, option_type, strike)."""
    try:
        s = symbol.strip()
        underlying = s[:-15].strip()
        date_str = s[-15:-9]   # YYMMDD
        type_char = s[-9]      # P or C
        strike_str = s[-8:]    # strike * 1000
        expiry = date(2000 + int(date_str[:2]), int(date_str[2:4]), int(date_str[4:6]))
        option_type = "put" if type_char.upper() == "P" else "call"
        strike = int(strike_str) / 1000.0
        return underlying, expiry, option_type, strike
    except Exception:
        return None


async def _fetch_positions(client, account_hash: str | None = None) -> list[dict]:
    """Fetch raw option positions from the Schwab account."""
    from src.auth.account_resolver import list_accounts
    accounts = await list_accounts(client)
    if not accounts:
        return []
    if account_hash is None:
        resolved_hash = accounts[0]["hashValue"]
    else:
        known = {a["hashValue"] for a in accounts}
        if account_hash not in known:
            raise ValueError(f"Account hash '{account_hash[:8]}...' not found on this token")
        resolved_hash = account_hash
    resp = await client.get_account(resolved_hash, fields=[client.Account.Fields.POSITIONS])
    data = resp.json()
    positions = data.get("securitiesAccount", {}).get("positions", [])
    result = []
    for pos in positions:
        instrument = pos.get("instrument", {})
        if instrument.get("assetType") != "OPTION":
            continue
        symbol = instrument.get("symbol", "")
        parsed = _parse_occ_symbol(symbol)
        if not parsed:
            continue
        underlying, expiry, option_type, strike = parsed

        long_qty = int(pos.get("longQuantity", 0))
        short_qty = int(pos.get("shortQuantity", 0))
        quantity = long_qty - short_qty
        contracts = abs(quantity)
        market_value = float(pos.get("marketValue", 0))
        mark = abs(market_value) / (contracts * 100) if contracts > 0 else 0.0

        result.append({
            "symbol": symbol,
            "underlying_symbol": instrument.get("underlyingSymbol", underlying),
            "option_type": option_type,
            "strike": strike,
            "expiry_date": expiry,
            "quantity": quantity,
            "mark": mark,
            "cost": float(pos.get("averagePrice", 0)),
        })
    return result


def _match_greeks(data: dict, sym_list: list[str]) -> dict[str, dict]:
    """Pick the held contracts' Greeks out of one option-chain response."""
    underlying_price = data.get("underlyingPrice") or data.get("underlying", {}).get("last")
    wanted = {s.strip(): s for s in sym_list}
    result: dict[str, dict] = {}
    for side in ("callExpDateMap", "putExpDateMap"):
        for exp_strikes in data.get(side, {}).values():
            for strike_opts in exp_strikes.values():
                for opt in strike_opts:
                    req_sym = wanted.get(opt.get("symbol", "").strip())
                    if req_sym is not None:
                        result[req_sym] = {
                            "delta": opt.get("delta"),
                            "gamma": opt.get("gamma"),
                            "theta": opt.get("theta"),
                            "vega": opt.get("vega"),
                            "implied_volatility": opt.get("volatility"),
                            "underlying_price": underlying_price,
                        }
    return result


def _narrowing(client, sym_list: list[str]) -> dict:
    """Chain filters covering only the held contracts (FR-108, research D-110)."""
    parsed = [p for p in (_parse_occ_symbol(s) for s in sym_list) if p]
    if len(parsed) != len(sym_list):
        return {}
    expiries = [p[1] for p in parsed]
    strikes = {p[3] for p in parsed}
    types = {p[2] for p in parsed}
    contract_types = client.Options.ContractType
    kwargs = {
        "contract_type": (
            contract_types.CALL if types == {"call"}
            else contract_types.PUT if types == {"put"}
            else contract_types.ALL
        ),
        "from_date": min(expiries),
        "to_date": max(expiries),
    }
    if len(strikes) == 1:
        kwargs["strike"] = strikes.pop()
    return kwargs


async def _fetch_greeks(symbols: list[str], client) -> dict[str, dict]:
    """Fetch Greeks for a list of OCC symbols via narrowed option-chain requests.

    One request per underlying, limited to the held expiries (and strike when only
    one is held). Any held contract missing from that reply triggers a single
    full-chain retry for its underlying.
    """
    if not symbols:
        return {}

    underlying_to_symbols: dict[str, list[str]] = {}
    for symbol in symbols:
        parsed = _parse_occ_symbol(symbol)
        underlying = parsed[0] if parsed else symbol[:6].strip()
        underlying_to_symbols.setdefault(underlying, []).append(symbol)

    async def _query(underlying: str, sym_list: list[str], **filters) -> dict[str, dict]:
        resp = await client.get_option_chain(
            symbol=underlying, include_underlying_quote=True, **filters
        )
        return _match_greeks(resp.json(), sym_list)

    async def _fetch_one(underlying: str, sym_list: list[str]) -> dict[str, dict]:
        try:
            filters = _narrowing(client, sym_list)
            result = await _query(underlying, sym_list, **filters) if filters else {}
            missing = [s for s in sym_list if s not in result]
            if missing:
                result.update(
                    await _query(underlying, missing, contract_type=client.Options.ContractType.ALL)
                )
            return result
        except Exception:
            return {}

    results = await asyncio.gather(
        *[_fetch_one(u, s) for u, s in underlying_to_symbols.items()],
        return_exceptions=True,
    )
    greeks_by_symbol: dict[str, dict] = {}
    for r in results:
        if not isinstance(r, Exception):
            greeks_by_symbol.update(r)
    return greeks_by_symbol


async def _realised_vol_for(client, underlying: str, start: datetime, end: datetime) -> float | None:
    symbol = _INDEX_SYMBOLS.get(underlying, underlying)
    try:
        resp = await client.get_price_history_every_day(symbol, start_datetime=start, end_datetime=end)
    except Exception:
        _security_log.warning("SECURITY schwab_api_error source=price_history status=transport")
        return None
    status = getattr(resp, "status_code", 200)
    if not isinstance(status, int) or status >= 400:
        _security_log.warning("SECURITY schwab_api_error source=price_history status=%s", status)
        return None
    try:
        candles = resp.json().get("candles") or []
        return realised_volatility([c["close"] for c in candles])
    except Exception:
        return None


async def fetch_realised_vols(client, underlyings: set[str]) -> dict[str, float | None]:
    """30-day realised volatility per underlying — one price-history call each (FR-102).

    Failures yield None for that underlying and never raise. Schwab errors are
    logged as security events without the symbol (Constitution II).
    """
    ordered = sorted(underlyings)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=PRICE_HISTORY_DAYS)
    vols = await asyncio.gather(*(_realised_vol_for(client, u, start, end) for u in ordered))
    return dict(zip(ordered, vols))


class TokenRejected(Exception):
    """Schwab answered 401 to the token check."""


class TokenCheckFailed(Exception):
    """The token check failed for any reason other than a 401."""


async def verify_token(client) -> None:
    """Confirm the caller's token with Schwab's lightest authenticated call (D-107).

    The response body is never read or logged.
    """
    try:
        resp = await client.get_account_numbers()
    except Exception as exc:
        raise TokenCheckFailed(type(exc).__name__) from None
    status = getattr(resp, "status_code", None)
    if status == 401:
        raise TokenRejected()
    if not isinstance(status, int) or status >= 400:
        raise TokenCheckFailed(str(status))


async def fetch_positions_and_greeks(
    schwab_client,
    account_hash: str | None = None,
) -> list[PositionView]:
    """Fetch live positions and Greeks from Schwab; return a list of PositionView.

    No database reads or writes. Each call fetches fresh data from Schwab.

    Args:
        schwab_client: An authenticated async schwab-py client.
        account_hash: Optional Schwab account hash. If None, uses the first account.
            Raises ValueError if provided hash is not found on the token.

    Returns:
        List of PositionView objects with Greeks populated (from API or Black-Scholes).
    """
    raw_positions = await _fetch_positions(schwab_client, account_hash=account_hash)
    symbols = [p["symbol"] for p in raw_positions]
    underlyings = {p["underlying_symbol"] for p in raw_positions}
    raw_greeks, realised_vols = await asyncio.gather(
        _fetch_greeks(symbols, schwab_client),
        fetch_realised_vols(schwab_client, underlyings) if underlyings else asyncio.sleep(0, result={}),
    )

    as_of = datetime.now(timezone.utc)
    today = date.today()
    views: list[PositionView] = []

    for raw in raw_positions:
        symbol = raw["symbol"]
        expiry: date = raw["expiry_date"]
        dte = (expiry - today).days
        mark = Decimal(str(round(raw["mark"], 4)))
        cost = Decimal(str(round(raw["cost"], 4)))
        qty = raw["quantity"]
        pnl = (mark - cost) * qty * 100

        greeks_raw = raw_greeks.get(symbol, {})
        greeks = build_greeks(
            strike=float(raw["strike"]),
            option_type=raw["option_type"],
            days_to_expiry=dte,
            raw=greeks_raw,
        )

        # Map source values: SourceEnum → Literal
        def _map_source(val):
            if val is None:
                return None
            src = str(val)
            if src in ("api", "SourceEnum.api"):
                return "api"
            if src in ("calculated", "SourceEnum.calculated"):
                return "calculated"
            return None

        view = PositionView(
            symbol=symbol,
            underlying_symbol=raw["underlying_symbol"],
            option_type=raw["option_type"],
            strike=Decimal(str(raw["strike"])),
            expiry_date=expiry,
            quantity=qty,
            cost=cost,
            current_mark=mark,
            unrealised_pnl=pnl,
            days_to_expiry=dte,
            delta=greeks.get("delta"),
            gamma=greeks.get("gamma"),
            theta=greeks.get("theta"),
            vega=greeks.get("vega"),
            implied_volatility=greeks.get("implied_volatility"),
            underlying_price=(
                Decimal(str(greeks_raw["underlying_price"]))
                if greeks_raw.get("underlying_price")
                else None
            ),
            delta_source=_map_source(greeks.get("delta_source")),
            gamma_source=_map_source(greeks.get("gamma_source")),
            theta_source=_map_source(greeks.get("theta_source")),
            vega_source=_map_source(greeks.get("vega_source")),
            iv_source=_map_source(greeks.get("iv_source")),
            as_of=as_of,
        )
        view.fundamentals = leg_fundamentals(
            view, realised_vols.get(view.underlying_symbol), r=RISK_FREE_RATE
        )
        views.append(view)

    return views
