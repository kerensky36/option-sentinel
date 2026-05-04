import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.api._group_helpers import load_thesis_cards
from src.data.models import (
    AlignmentRating,
    ExitGoal,
    OptionType,
    Position,
    PositionStatus,
    Thesis,
    ThesisTemplateType,
)


def _thesis(name: str, rating: AlignmentRating = AlignmentRating.unrated) -> Thesis:
    return Thesis(
        name=name,
        template_type=ThesisTemplateType.iv_crush,
        alignment_rating=rating,
    )


def _position(thesis: Thesis | None, pnl: float | None = None) -> Position:
    return Position(
        schwab_account_id="TEST123456789012345",
        symbol=f"SPY   2501{uuid.uuid4().hex[:2].upper()}C00500000",
        underlying_symbol="SPY",
        option_type=OptionType.call,
        strike=Decimal("500.00"),
        expiry_date=date(2025, 1, 17),
        quantity=-1,
        status=PositionStatus.open,
        last_updated=datetime.now(timezone.utc),
        unrealised_pnl=Decimal(str(pnl)) if pnl is not None else None,
        thesis=thesis,
    )


def _exit_goal(position: Position, score: int) -> ExitGoal:
    return ExitGoal(
        position=position,
        profit_target_pct=50.0,
        exit_proximity_score=score,
    )


async def test_thesis_cards_position_count(db):
    t1 = _thesis("IV Crush")
    p1 = _position(t1)
    p2 = _position(t1)
    db.add_all([t1, p1, p2])
    await db.commit()

    cards = await load_thesis_cards(db)
    t1_card = next(c for c in cards if c["thesis"] and c["thesis"].name == "IV Crush")
    assert t1_card["position_count"] == 2


async def test_thesis_cards_avg_exit_proximity_score(db):
    t1 = _thesis("Earnings Fade")
    p1 = _position(t1)
    p2 = _position(t1)
    db.add_all([t1, p1, p2])
    await db.flush()
    db.add(_exit_goal(p1, 60))
    db.add(_exit_goal(p2, 80))
    await db.commit()

    cards = await load_thesis_cards(db)
    card = next(c for c in cards if c["thesis"] and c["thesis"].name == "Earnings Fade")
    assert card["avg_exit_proximity_score"] == 70


async def test_thesis_cards_combined_pnl(db):
    t1 = _thesis("Momentum")
    p1 = _position(t1, pnl=120.0)
    p2 = _position(t1, pnl=-40.0)
    db.add_all([t1, p1, p2])
    await db.commit()

    cards = await load_thesis_cards(db)
    card = next(c for c in cards if c["thesis"] and c["thesis"].name == "Momentum")
    assert abs(card["combined_pnl"] - 80.0) < 0.01


async def test_thesis_cards_unassigned_card(db):
    p = _position(None, pnl=50.0)
    db.add(p)
    await db.commit()

    cards = await load_thesis_cards(db)
    unassigned = next((c for c in cards if c["thesis"] is None), None)
    assert unassigned is not None
    assert unassigned["position_count"] == 1


async def test_thesis_cards_no_exit_goals_score_is_none(db):
    t1 = _thesis("Mean Rev")
    p1 = _position(t1)
    db.add_all([t1, p1])
    await db.commit()

    cards = await load_thesis_cards(db)
    card = next(c for c in cards if c["thesis"] and c["thesis"].name == "Mean Rev")
    assert card["avg_exit_proximity_score"] is None
