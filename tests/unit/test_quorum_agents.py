"""Tests for the Google ADK quorum orchestration (specs/017 FR-004–FR-011, SC-003).

All seats run against a fake ADK BaseLlm — no network, no Vertex AI.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from src.data.models import Headline, PositionView
from src.services import quorum_agents
from src.services.quorum_agents import (
    SEATS,
    build_position_context,
    quorum_configured,
    run_quorum,
)


def _ballot(action: str, confidence: float = 0.7, **extra) -> str:
    body = {"action": action, "confidence": confidence, "rationale": f"because {action}"}
    if action == "ROLL":
        body["roll_direction"] = "out"
    body.update(extra)
    return json.dumps(body)


class FakeLlm(BaseLlm):
    """Replies per agent name; records every request for privacy assertions."""

    replies: dict = {}
    requests: list = []

    async def generate_content_async(self, llm_request, stream=False):
        self.requests.append(llm_request)
        system = str(llm_request.config.system_instruction or "")
        name = next((n for n in self.replies if f'internal name is "{n}"' in system), None)
        reply = self.replies.get(name, "")
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, float):  # sleep seconds, then answer HOLD
            await asyncio.sleep(reply)
            reply = _ballot("HOLD")
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=reply)]))


def _fake(replies: dict) -> FakeLlm:
    return FakeLlm(model="gemini-2.5-flash", replies=replies, requests=[])


def _leg(symbol="SPY   261017C00560000", underlying="SPY", qty=-1, strike="560") -> PositionView:
    return PositionView(
        symbol=symbol,
        underlying_symbol=underlying,
        option_type="call",
        strike=Decimal(strike),
        expiry_date=date(2026, 10, 17),
        quantity=qty,
        cost=Decimal("4.20"),
        current_mark=Decimal("3.10"),
        unrealised_pnl=Decimal("110"),
        days_to_expiry=22,
        delta=-0.35,
        implied_volatility=0.18,
        underlying_price=Decimal("552.10"),
    )


_HEADLINES = [
    Headline(
        publisher="CNBC",
        title="Fed signals patience on rate cuts",
        link="https://www.cnbc.com/x",
        published=datetime(2026, 9, 24, tzinfo=timezone.utc),
    )
]

_SEAT_IDS = [s.id for s in SEATS]


class TestSeats:
    def test_exactly_five_distinct_lenses(self):
        assert len(SEATS) == 5
        assert len({s.id for s in SEATS}) == 5
        assert [s.lens for s in SEATS] == [
            "Rates & Fed",
            "Volatility Regime",
            "Growth & Inflation",
            "Underlying & Sector News",
            "Position Risk",
        ]

    def test_seat_agents_have_no_tools(self):
        for seat in SEATS:
            agent = quorum_agents.build_seat_agent(seat, "gemini-2.5-flash")
            assert agent.tools == []
            assert agent.output_schema is not None

    def test_seat_instructions_contain_no_braces(self):
        # ADK treats {name} in instructions as state placeholders.
        for seat in SEATS:
            agent = quorum_agents.build_seat_agent(seat, "gemini-2.5-flash")
            assert "{" not in agent.instruction and "}" not in agent.instruction


class TestBuildPositionContext:
    def test_single_leg(self):
        ctx = build_position_context([_leg()])
        assert ctx.underlying_symbol == "SPY"
        assert len(ctx.legs) == 1
        assert ctx.net_unrealised_pnl == Decimal("110")
        assert ctx.min_days_to_expiry == 22

    def test_context_is_allow_listed(self):
        ctx = build_position_context([_leg()])
        fields = set(ctx.legs[0].model_dump().keys())
        assert "symbol" not in fields
        assert not any(f.endswith("_source") for f in fields)

    def test_mixed_underlyings_rejected(self):
        with pytest.raises(ValueError):
            build_position_context([_leg(), _leg(symbol="QQQ   261017C00450000", underlying="QQQ")])

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            build_position_context([])


class TestRunQuorum:
    async def test_all_seats_vote_and_tally(self):
        replies = {"macro_researcher": "Rates steady; VIX low."}
        replies.update({sid: _ballot("ROLL") for sid in _SEAT_IDS[:3]})
        replies.update({sid: _ballot("HOLD") for sid in _SEAT_IDS[3:]})
        result = await run_quorum(build_position_context([_leg()]), _HEADLINES, model=_fake(replies))
        assert result.verdict == "ROLL"
        assert result.valid_votes == 5
        assert result.seats == 5
        assert [v.seat for v in result.votes] == _SEAT_IDS
        assert result.macro_brief == "Rates steady; VIX low."
        assert result.headlines == _HEADLINES
        assert result.underlying_symbol == "SPY"
        assert result.model == "gemini-2.5-flash"
        roll_votes = [v for v in result.votes if v.action == "ROLL"]
        assert all(v.roll_direction == "out" for v in roll_votes)

    async def test_malformed_seat_abstains_without_affecting_others(self):
        replies = {sid: _ballot("CLOSE") for sid in _SEAT_IDS}
        replies[_SEAT_IDS[1]] = "garbage not json"
        replies[_SEAT_IDS[2]] = json.dumps({"action": "ROLL", "confidence": 0.5, "rationale": "no dir"})
        result = await run_quorum(build_position_context([_leg()]), [], model=_fake(replies))
        assert result.valid_votes == 3
        assert result.verdict == "CLOSE"
        abstained = [v.seat for v in result.votes if v.abstained]
        assert abstained == [_SEAT_IDS[1], _SEAT_IDS[2]]
        assert all(v.action is None for v in result.votes if v.abstained)

    async def test_raising_seat_abstains(self):
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        replies[_SEAT_IDS[0]] = RuntimeError("vertex down")
        result = await run_quorum(build_position_context([_leg()]), [], model=_fake(replies))
        assert result.votes[0].abstained is True
        assert result.valid_votes == 4
        assert result.verdict == "HOLD"

    async def test_slow_seat_times_out_and_abstains(self):
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        replies[_SEAT_IDS[4]] = 5.0
        result = await run_quorum(
            build_position_context([_leg()]), [], model=_fake(replies), seat_timeout=0.2
        )
        assert result.votes[4].abstained is True
        assert result.valid_votes == 4

    async def test_research_failure_gives_none_brief(self):
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        replies["macro_researcher"] = RuntimeError("search failed")
        result = await run_quorum(build_position_context([_leg()]), [], model=_fake(replies))
        assert result.macro_brief is None
        assert result.verdict == "HOLD"

    async def test_all_fail_is_no_quorum(self):
        replies = {sid: "nope" for sid in _SEAT_IDS}
        result = await run_quorum(build_position_context([_leg()]), [], model=_fake(replies))
        assert result.verdict == "NO_QUORUM"
        assert result.quorum_met is False

    async def test_seats_receive_brief_and_headlines_but_not_each_other(self):
        replies = {"macro_researcher": "BRIEF-MARKER"}
        replies.update({sid: _ballot("HOLD", rationale=f"VOTE-{sid}") for sid in _SEAT_IDS})
        fake = _fake(replies)
        await run_quorum(build_position_context([_leg()]), _HEADLINES, model=fake)
        seat_requests = [
            r for r in fake.requests
            if any(f'internal name is "{sid}"' in str(r.config.system_instruction) for sid in _SEAT_IDS)
        ]
        assert len(seat_requests) == 5
        for r in seat_requests:
            text = json.dumps([c.model_dump(mode="json") for c in r.contents])
            assert "BRIEF-MARKER" in text
            assert "Fed signals patience" in text
            assert "VOTE-" not in text  # FR-006: independent votes


class TestPrivacy:
    async def test_no_identifiers_reach_the_model(self):
        """SC-003 / Constitution v3.3.0: nothing identifying in any model request."""
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        fake = _fake(replies)
        leg = _leg()
        await run_quorum(build_position_context([leg]), _HEADLINES, model=fake)
        assert fake.requests
        for r in fake.requests:
            text = json.dumps([c.model_dump(mode="json") for c in r.contents]) + str(r.config.system_instruction)
            assert leg.symbol not in text
            assert "account_hash" not in text
            assert "_source" not in text


class TestConfigured:
    def test_requires_vertex_flag_and_project(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        assert quorum_configured() is False
        monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
        assert quorum_configured() is False
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "proj")
        assert quorum_configured() is True
        monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "false")
        assert quorum_configured() is False

    def test_default_model_from_env(self, monkeypatch):
        monkeypatch.delenv("QUORUM_MODEL", raising=False)
        assert quorum_agents.default_model() == "gemini-2.5-flash"
        monkeypatch.setenv("QUORUM_MODEL", "gemini-x")
        assert quorum_agents.default_model() == "gemini-x"
