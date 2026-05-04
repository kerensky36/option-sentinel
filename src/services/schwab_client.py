"""Stateless Schwab client helpers.

All functions return plain Pydantic model instances or dicts — no DB, no session.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal

from src.data.models import PositionView
from src.services.greeks_service import build_greeks

ACCOUNT_ID = os.getenv("SCHWAB_ACCOUNT_ID", "")


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


async def _fetch_positions(client) -> list[dict]:
    """Fetch raw option positions from the Schwab account."""
    from src.auth.account_resolver import resolve_account_hash
    account_hash = await resolve_account_hash(client, ACCOUNT_ID)
    resp = await client.get_account(account_hash, fields=[client.Account.Fields.POSITIONS])
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


async def _fetch_greeks(symbols: list[str], client) -> dict[str, dict]:
    """Fetch Greeks for a list of OCC symbols via the option chain endpoint."""
    if not symbols:
        return {}

    underlying_to_symbols: dict[str, list[str]] = {}
    for symbol in symbols:
        underlying = symbol[:6].strip()
        underlying_to_symbols.setdefault(underlying, []).append(symbol)

    greeks_by_symbol: dict[str, dict] = {}
    for underlying, sym_list in underlying_to_symbols.items():
        try:
            resp = await client.get_option_chain(
                symbol=underlying,
                contract_type=client.Options.ContractType.ALL,
                include_underlying_quote=True,
            )
            data = resp.json()
            underlying_price = data.get("underlyingPrice") or data.get("underlying", {}).get("last")
            for side in ("callExpDateMap", "putExpDateMap"):
                for exp_strikes in data.get(side, {}).values():
                    for strike_opts in exp_strikes.values():
                        for opt in strike_opts:
                            opt_symbol = opt.get("symbol", "").strip()
                            for req_sym in sym_list:
                                if opt_symbol == req_sym.strip():
                                    greeks_by_symbol[req_sym] = {
                                        "delta": opt.get("delta"),
                                        "gamma": opt.get("gamma"),
                                        "theta": opt.get("theta"),
                                        "vega": opt.get("vega"),
                                        "implied_volatility": opt.get("volatility"),
                                        "underlying_price": underlying_price,
                                    }
        except Exception:
            pass
    return greeks_by_symbol


async def fetch_positions_and_greeks(schwab_client) -> list[PositionView]:
    """Fetch live positions and Greeks from Schwab; return a list of PositionView.

    No database reads or writes. Each call fetches fresh data from Schwab.

    Args:
        schwab_client: An authenticated async schwab-py client.

    Returns:
        List of PositionView objects with Greeks populated (from API or Black-Scholes).
    """
    raw_positions = await _fetch_positions(schwab_client)
    symbols = [p["symbol"] for p in raw_positions]
    raw_greeks = await _fetch_greeks(symbols, schwab_client)

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

        views.append(PositionView(
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
            delta_source=_map_source(greeks.get("delta_source")),
            gamma_source=_map_source(greeks.get("gamma_source")),
            theta_source=_map_source(greeks.get("theta_source")),
            vega_source=_map_source(greeks.get("vega_source")),
            iv_source=_map_source(greeks.get("iv_source")),
        ))

    return views
