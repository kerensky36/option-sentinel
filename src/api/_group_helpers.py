"""Shared helper: load open positions + snapshots, return grouped list."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models import Position, PositionStatus, Thesis, ThesisHealthSnapshot
from src.services.position_groups import group_positions


async def load_thesis_cards(session: AsyncSession) -> list[dict]:
    """Return one card dict per thesis group plus one for unassigned positions."""
    pos_result = await session.execute(
        select(Position)
        .where(Position.status == PositionStatus.open)
        .options(selectinload(Position.thesis), selectinload(Position.exit_goal))
    )
    positions = list(pos_result.scalars().all())

    theses_result = await session.execute(
        select(Thesis).order_by(Thesis.name)
    )
    theses = list(theses_result.scalars().all())

    # Build per-thesis buckets
    buckets: dict[str | None, list] = {str(t.id): [] for t in theses}
    buckets[None] = []
    for p in positions:
        key = str(p.thesis_id) if p.thesis_id else None
        if key not in buckets:
            key = None
        buckets[key].append(p)

    cards = []
    for t in theses:
        members = buckets[str(t.id)]
        cards.append(_build_card(t, members))

    unassigned = buckets[None]
    if unassigned:
        cards.append(_build_card(None, unassigned))

    return cards


def _build_card(thesis: Thesis | None, positions: list) -> dict:
    position_count = len(positions)
    combined_pnl: float | None = None
    scores = []
    for p in positions:
        if p.unrealised_pnl is not None:
            combined_pnl = (combined_pnl or 0.0) + float(p.unrealised_pnl)
        if p.exit_goal and p.exit_goal.profit_target_pct is not None:
            scores.append(p.exit_goal.exit_proximity_score)

    avg_score = round(sum(scores) / len(scores)) if scores else None
    return {
        "thesis": thesis,
        "position_count": position_count,
        "combined_pnl": combined_pnl,
        "avg_exit_proximity_score": avg_score,
    }


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
