"""FR-018–020: Compute exit proximity score (0–100) per position."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import ExitGoal, Position, PositionStatus


def score_position(pos: Position, goal: ExitGoal) -> int:
    """Return 0–100. 100 means at least one exit dimension has been met."""
    scores: list[float] = []

    # P&L % target
    if goal.profit_target_pct is not None:
        cost = float(pos.opening_credit_debit or 0)
        qty = abs(pos.quantity)
        max_profit = abs(cost * qty * 100)
        pnl = float(pos.unrealised_pnl or 0)
        if max_profit > 0:
            achieved = pnl / max_profit
            scores.append(min(1.0, achieved / goal.profit_target_pct))

    # DTE threshold
    if goal.dte_threshold is not None and pos.days_to_expiry is not None:
        # Score rises as DTE approaches threshold; 100 when DTE <= threshold
        original_dte = 60  # rough estimate of opening DTE if we don't store it
        dte_progress = 1.0 - max(0.0, (pos.days_to_expiry - goal.dte_threshold)) / max(original_dte, 1)
        scores.append(min(1.0, dte_progress))

    # Underlying price target
    if goal.underlying_price_target is not None and goal.price_target_direction is not None:
        # We don't store underlying price directly; skip if unavailable
        pass

    if not scores:
        return 0

    return min(100, int(max(scores) * 100))


async def update_exit_scores(session: AsyncSession) -> None:
    result = await session.execute(
        select(Position, ExitGoal)
        .join(ExitGoal, ExitGoal.position_id == Position.id)
        .where(Position.status == PositionStatus.open)
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for pos, goal in result.all():
        goal.exit_proximity_score = score_position(pos, goal)
        goal.last_scored_at = now
