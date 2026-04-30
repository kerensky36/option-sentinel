"""Shared helper: load open positions + snapshots, return grouped list."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models import Position, PositionStatus, Thesis, ThesisHealthSnapshot
from src.services.position_groups import group_positions


async def load_groups_and_theses(session: AsyncSession):
    pos_result = await session.execute(
        select(Position)
        .where(Position.status == PositionStatus.open)
        .options(
            selectinload(Position.greeks),
            selectinload(Position.exit_goal),
            selectinload(Position.thesis),
            selectinload(Position.health_snapshots),
        )
        .order_by(Position.created_at)
    )
    positions = list(pos_result.scalars().all())

    # Build snapshots dict keyed by position_id string
    snapshots: dict[str, list] = {}
    for p in positions:
        snapshots[str(p.id)] = list(p.health_snapshots)

    theses_result = await session.execute(select(Thesis).order_by(Thesis.name))
    theses = list(theses_result.scalars().all())

    return group_positions(positions, snapshots), theses
