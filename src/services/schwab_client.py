import os
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Greeks, Position, PositionStatus, SourceEnum
from src.services.greeks_service import build_greeks

ACCOUNT_ID = os.getenv("SCHWAB_ACCOUNT_ID", "")


def _parse_occ_symbol(symbol: str) -> tuple[str, date, str, float] | None:
    """Parse OCC symbol e.g. 'QQQ   260618P00650000' → (underlying, expiry, option_type, strike)."""
    try:
        s = symbol.strip()
        # Underlying: up to 6 chars (padded), then 6-digit date, 1 char type, 8-digit strike
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


async def _fetch_positions(client=None) -> list[dict]:
    if client is None:
        from src.auth.schwab_oauth import get_schwab_client
        client = await get_schwab_client()
    resp = await client.get_account(ACCOUNT_ID, fields=[client.Account.Fields.POSITIONS])
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
        # For short positions market value is negative; mark is still positive price
        if quantity < 0:
            mark = abs(market_value) / (contracts * 100)

        result.append({
            "symbol": symbol,
            "underlying_symbol": instrument.get("underlyingSymbol", underlying),
            "option_type": option_type,
            "strike": strike,
            "expiry_date": expiry.isoformat(),
            "quantity": quantity,
            "mark": mark,
            "cost": float(pos.get("averagePrice", 0)),
            "account_id": ACCOUNT_ID,
        })
    return result


async def _fetch_greeks(symbols: list[str], client=None) -> dict[str, dict]:
    if not symbols:
        return {}
    if client is None:
        from src.auth.schwab_oauth import get_schwab_client
        client = await get_schwab_client()

    greeks_by_symbol: dict[str, dict] = {}
    for symbol in symbols:
        try:
            # Extract underlying + option details from OCC symbol
            underlying = symbol[:6].strip()
            resp = await client.get_option_chain(
                symbol=underlying,
                contract_type=client.Options.ContractType.ALL,
                include_underlying_quote=False,
            )
            data = resp.json()
            for side in ("callExpDateMap", "putExpDateMap"):
                for exp_strikes in data.get(side, {}).values():
                    for strike_opts in exp_strikes.values():
                        for opt in strike_opts:
                            if opt.get("symbol") == symbol:
                                greeks_by_symbol[symbol] = {
                                    "delta": opt.get("delta"),
                                    "gamma": opt.get("gamma"),
                                    "theta": opt.get("theta"),
                                    "vega": opt.get("vega"),
                                    "implied_volatility": opt.get("volatility"),
                                }
        except Exception:
            pass
    return greeks_by_symbol


async def sync_positions_and_greeks(session: AsyncSession, schwab_client=None) -> None:
    raw_positions = await _fetch_positions(schwab_client)
    symbols = [p["symbol"] for p in raw_positions]
    raw_greeks = await _fetch_greeks(symbols, schwab_client)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seen_symbols: set[str] = set()

    for raw in raw_positions:
        symbol = raw["symbol"]
        account_id = raw["account_id"]
        seen_symbols.add(symbol)

        result = await session.execute(
            select(Position).where(
                Position.symbol == symbol,
                Position.schwab_account_id == account_id,
                Position.status == PositionStatus.open,
            )
        )
        position = result.scalar_one_or_none()

        expiry = date.fromisoformat(raw["expiry_date"])
        dte = (expiry - date.today()).days
        mark = Decimal(str(round(raw["mark"], 4)))
        cost = Decimal(str(round(raw["cost"], 4)))
        qty = raw["quantity"]
        pnl = (mark - cost) * qty * 100

        if position is None:
            position = Position(
                schwab_account_id=account_id,
                symbol=symbol,
                underlying_symbol=raw["underlying_symbol"],
                option_type=raw["option_type"],
                strike=Decimal(str(raw["strike"])),
                expiry_date=expiry,
                quantity=qty,
                opening_credit_debit=cost,
                current_mark=mark,
                unrealised_pnl=pnl,
                days_to_expiry=dte,
                status=PositionStatus.open,
                last_updated=now,
                created_at=now,
            )
            session.add(position)
            await session.flush()
        else:
            position.current_mark = mark
            position.unrealised_pnl = pnl
            position.days_to_expiry = dte
            position.last_updated = now

        greeks_data = raw_greeks.get(symbol, {})
        greeks_row = await session.execute(
            select(Greeks).where(Greeks.position_id == position.id)
        )
        greeks = greeks_row.scalar_one_or_none()

        built = build_greeks(
            position=position,
            raw=greeks_data,
        )

        if greeks is None:
            greeks = Greeks(position_id=position.id, **built, computed_at=now)
            session.add(greeks)
        else:
            for k, v in built.items():
                setattr(greeks, k, v)
            greeks.computed_at = now

    # Determine which account IDs were queried this cycle
    fetched_account_ids = {p["account_id"] for p in raw_positions}
    if not fetched_account_ids and ACCOUNT_ID:
        fetched_account_ids.add(ACCOUNT_ID)
    # If still empty, fall back to all account IDs that have open positions in DB
    if not fetched_account_ids:
        acct_result = await session.execute(
            select(Position.schwab_account_id)
            .where(Position.status == PositionStatus.open)
            .distinct()
        )
        fetched_account_ids = set(acct_result.scalars().all())

    # Close positions that were not returned in this poll cycle
    for acct_id in fetched_account_ids:
        open_result = await session.execute(
            select(Position).where(
                Position.schwab_account_id == acct_id,
                Position.status == PositionStatus.open,
            )
        )
        for pos in open_result.scalars().all():
            if pos.symbol not in seen_symbols:
                pos.status = PositionStatus.closed
                pos.last_updated = now

    await session.commit()
