"""Tests for the server figure catalog (specs/020 D-304, data-model.md FigureCatalog)."""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.data.models import AnalystVote, LegFundamentals, PositionView, TallyEntry
from src.services import figure_catalog
from src.services.figure_catalog import add_tally, build, resolve_cited
from src.services.quorum_agents import build_position_context

NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


def _leg(option_type="put", strike="565", qty=-1, cost="2.10", mark="1.55", pnl="55", delta=0.31,
         theta=0.158, vega=-0.42, iv=0.162, rv=0.15, price="572.40", dte=12) -> PositionView:
    return PositionView(
        symbol=f"SPY   261009{option_type[0].upper()}{strike}",
        underlying_symbol="SPY",
        option_type=option_type,
        strike=Decimal(strike),
        expiry_date=date(2026, 10, 9),
        quantity=qty,
        cost=Decimal(cost),
        current_mark=Decimal(mark),
        unrealised_pnl=Decimal(pnl),
        days_to_expiry=dte,
        delta=delta,
        gamma=-0.02,
        theta=theta,
        vega=vega,
        implied_volatility=iv,
        underlying_price=Decimal(price) if price is not None else None,
        as_of=datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc),
        fundamentals=LegFundamentals(realised_volatility=rv),
    )


def _ctx(*legs):
    return build_position_context(list(legs))


LONG_CALL = lambda: _ctx(_leg("call", "580", 1, "3.00", "3.40", "40", 0.4, -0.2, 0.5))
SHORT_PUT = lambda: _ctx(_leg())
PUT_SPREAD = lambda: _ctx(_leg(), _leg("put", "560", 1, "1.24", "1.05", "-19", -0.09, -0.07, 0.26, 0.174))
IRON_CONDOR = lambda: _ctx(
    _leg("put", "550", 1, "0.80", "0.60", "-20", -0.05, -0.03, 0.1),
    _leg("put", "560", -1, "1.60", "1.20", "40", 0.15, 0.06, -0.2),
    _leg("call", "585", -1, "1.50", "1.10", "40", -0.15, 0.06, -0.2),
    _leg("call", "595", 1, "0.70", "0.50", "-20", 0.05, -0.03, 0.1),
)


@pytest.mark.parametrize("make", [LONG_CALL, SHORT_PUT, PUT_SPREAD, IRON_CONDOR])
def test_names_labels_values_are_well_formed(make):
    cat = build(make())
    assert cat, "catalog should not be empty"
    for name, fig in cat.items():
        assert NAME.match(name), name
        assert fig.name == name
        assert len(fig.label) <= 24, fig.label
        assert math.isfinite(fig.value)
        assert fig.display


def test_position_figures_for_a_credit_spread():
    cat = build(PUT_SPREAD())
    for name in ("net_delta", "net_theta_day", "net_vega", "max_profit", "max_loss", "captured_pct", "breakeven_1", "dte"):
        assert name in cat, name
    assert cat["dte"].display == "12 d"
    assert cat["max_profit"].display == "$86.00"  # (2.10 − 1.24) × 100
    assert cat["max_loss"].display == "$414.00"
    assert "breakeven_2" not in cat


def test_iron_condor_has_two_breakevens():
    cat = build(IRON_CONDOR())
    assert "breakeven_1" in cat and "breakeven_2" in cat


def test_per_leg_names_follow_leg_order():
    cat = build(PUT_SPREAD())
    for n in (1, 2):
        for suffix in ("strike", "spot", "iv", "rv", "iv_rv", "moneyness", "prob_itm"):
            assert f"leg{n}_{suffix}" in cat
    assert cat["leg1_strike"].display == "$565.00"
    assert cat["leg2_strike"].display == "$560.00"
    assert cat["leg1_iv"].display == "16%"
    assert cat["leg1_iv_rv"].display == "1.08×"
    assert cat["leg1_iv_rv"].label == "Leg 1 IV/RV"


def test_single_leg_labels_have_no_leg_prefix():
    cat = build(SHORT_PUT())
    assert cat["leg1_iv_rv"].label == "IV/RV"
    assert cat["leg1_moneyness"].display == "-1.3%"  # (565 − 572.40) / 572.40, OTM put


def test_unavailable_figures_are_absent_not_zero():
    cat = build(_ctx(_leg(rv=None, price=None, delta=None)))
    for name in ("leg1_rv", "leg1_iv_rv", "leg1_spot", "leg1_moneyness", "leg1_prob_itm", "net_delta"):
        assert name not in cat, name


@pytest.mark.parametrize(
    "fmt,value,expected",
    [
        ("money", 1234.4, "$1,234"),
        ("money", 572.4, "$572.40"),
        ("money", -8.42, "-$8.42"),
        ("pct", 38.2, "38%"),
        ("pct", 1.34, "1.3%"),
        ("pct", -1.29, "-1.3%"),
        ("ratio", 1.0833, "1.08×"),
        ("shares", 22.1, "+22 sh"),
        ("shares", -5, "-5 sh"),
        ("days", 12, "12 d"),
        ("count", 3, "3"),
    ],
)
def test_display_formats(fmt, value, expected):
    assert figure_catalog.FORMATTERS[fmt](value) == expected


def _votes():
    return [
        AnalystVote(seat="greeks_exposure", lens="Greeks & Exposure", action="HOLD", confidence=0.55, rationale="r"),
        AnalystVote(seat="volatility_pricing", lens="Volatility & Pricing", abstained=True),
        AnalystVote(seat="time_decay_pnl", lens="Time Decay & P&L", action="ROLL", confidence=0.6, rationale="r", roll_direction="out"),
        AnalystVote(seat="strike_assignment", lens="Strike & Assignment", action="ROLL", confidence=0.6, rationale="r", roll_direction="out"),
        AnalystVote(seat="macro_news_overlay", lens="Macro & News Overlay", action="ROLL", confidence=0.55, rationale="r", roll_direction="out"),
    ]


def test_add_tally_adds_counts_and_confidences_for_voting_seats():
    tally = [TallyEntry(action="CLOSE", votes=0), TallyEntry(action="HOLD", votes=1), TallyEntry(action="ROLL", votes=3)]
    base = build(SHORT_PUT())
    cat = add_tally(base, tally, _votes())
    assert cat is not base
    assert cat["votes_close"].display == "0"
    assert cat["votes_hold"].display == "1"
    assert cat["votes_roll"].display == "3"
    assert cat["valid_votes"].display == "4"
    assert cat["seats"].display == "5"
    assert cat["confidence_greeks_exposure"].display == "55%"
    assert "confidence_volatility_pricing" not in cat
    for fig in cat.values():
        assert len(fig.label) <= 24


def test_resolve_cited_keeps_known_unique_max_five():
    cat = build(PUT_SPREAD())
    cited = resolve_cited(
        ["leg1_iv_rv", "nope", "leg1_iv_rv", "dte", "max_profit", "max_loss", "captured_pct", "leg2_iv"], cat
    )
    assert [c.name for c in cited] == ["leg1_iv_rv", "dte", "max_profit", "max_loss", "captured_pct"]
    assert cited[0].label == cat["leg1_iv_rv"].label
    assert cited[0].display == cat["leg1_iv_rv"].display
