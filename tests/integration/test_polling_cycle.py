import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from src.data.models import Position, Greeks, PositionStatus, SourceEnum
from src.services.schwab_client import sync_positions_and_greeks


MOCK_POSITIONS_RESPONSE = [
    {
        "symbol": "SPY   240119C00520000",
        "underlying_symbol": "SPY",
        "option_type": "call",
        "strike": 520.0,
        "expiry_date": "2024-01-19",
        "quantity": 1,
        "mark": 5.50,
        "cost": 4.00,
        "account_id": "TEST123456789012345",
    }
]

MOCK_GREEKS_RESPONSE = {
    "SPY   240119C00520000": {
        "delta": 0.45,
        "gamma": 0.02,
        "theta": -0.15,
        "vega": 0.30,
        "implied_volatility": 0.25,
    }
}


async def test_poll_cycle_creates_position(db):
    with (
        patch("src.services.schwab_client._fetch_positions", new_callable=AsyncMock) as mock_pos,
        patch("src.services.schwab_client._fetch_greeks", new_callable=AsyncMock) as mock_greeks,
    ):
        mock_pos.return_value = MOCK_POSITIONS_RESPONSE
        mock_greeks.return_value = MOCK_GREEKS_RESPONSE

        await sync_positions_and_greeks(db)

    result = await db.execute(select(Position))
    positions = result.scalars().all()
    assert len(positions) == 1
    assert positions[0].underlying_symbol == "SPY"
    assert positions[0].status == PositionStatus.open


async def test_poll_cycle_creates_greeks(db):
    with (
        patch("src.services.schwab_client._fetch_positions", new_callable=AsyncMock) as mock_pos,
        patch("src.services.schwab_client._fetch_greeks", new_callable=AsyncMock) as mock_greeks,
    ):
        mock_pos.return_value = MOCK_POSITIONS_RESPONSE
        mock_greeks.return_value = MOCK_GREEKS_RESPONSE

        await sync_positions_and_greeks(db)

    result = await db.execute(select(Greeks))
    greeks = result.scalars().all()
    assert len(greeks) == 1
    assert greeks[0].delta == pytest.approx(0.45)
    assert greeks[0].delta_source == SourceEnum.api


async def test_poll_cycle_updates_existing_position(db):
    with (
        patch("src.services.schwab_client._fetch_positions", new_callable=AsyncMock) as mock_pos,
        patch("src.services.schwab_client._fetch_greeks", new_callable=AsyncMock) as mock_greeks,
    ):
        mock_pos.return_value = MOCK_POSITIONS_RESPONSE
        mock_greeks.return_value = MOCK_GREEKS_RESPONSE
        await sync_positions_and_greeks(db)

        updated = [{**MOCK_POSITIONS_RESPONSE[0], "mark": 7.00}]
        mock_pos.return_value = updated
        await sync_positions_and_greeks(db)

    result = await db.execute(select(Position))
    positions = result.scalars().all()
    assert len(positions) == 1
    assert positions[0].current_mark == pytest.approx(Decimal("7.00"), abs=Decimal("0.01"))


async def test_poll_cycle_closes_missing_position(db):
    with (
        patch("src.services.schwab_client._fetch_positions", new_callable=AsyncMock) as mock_pos,
        patch("src.services.schwab_client._fetch_greeks", new_callable=AsyncMock) as mock_greeks,
    ):
        mock_pos.return_value = MOCK_POSITIONS_RESPONSE
        mock_greeks.return_value = MOCK_GREEKS_RESPONSE
        await sync_positions_and_greeks(db)

        mock_pos.return_value = []
        mock_greeks.return_value = {}
        await sync_positions_and_greeks(db)

    result = await db.execute(select(Position))
    positions = result.scalars().all()
    assert all(p.status == PositionStatus.closed for p in positions)
