"""Tests for the Google ADK quorum orchestration (specs/017; specs/018 FR-113–FR-119).

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

import time

from src.data.models import Headline, LegFundamentals, PositionView
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
    """Replies per agent name; records every request and completion time.

    A reply may be a string, an Exception (raised), a float (sleep then HOLD),
    or a (seconds, text) tuple (sleep then reply with text).
    """

    replies: dict = {}
    requests: list = []
    finished: dict = {}

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
        if isinstance(reply, tuple):
            await asyncio.sleep(reply[0])
            reply = reply[1]
        self.finished[name] = time.monotonic()
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=reply)]))


def _fake(replies: dict) -> FakeLlm:
    return FakeLlm(model="gemini-2.5-flash", replies=replies, requests=[], finished={})


def _fetcher(headlines, delay: float = 0.0):
    async def fetch(underlying):
        if delay:
            await asyncio.sleep(delay)
        return list(headlines)
    return fetch


def _request_text(r) -> str:
    return json.dumps([c.model_dump(mode="json") for c in r.contents])


def _seat_requests(fake, seat_ids):
    return {
        sid: r
        for r in fake.requests
        for sid in seat_ids
        if f'internal name is "{sid}"' in str(r.config.system_instruction)
    }


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
        gamma=0.01,
        theta=-0.05,
        vega=0.3,
        implied_volatility=0.18,
        underlying_price=Decimal("552.10"),
        as_of=datetime(2026, 9, 25, 14, 0, tzinfo=timezone.utc),
        fundamentals=LegFundamentals(realised_volatility=0.12),
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
_FUND_IDS = _SEAT_IDS[:4]
_OVERLAY_ID = _SEAT_IDS[4]


class TestSeats:
    def test_exactly_five_fundamentals_first_lenses(self):
        assert _SEAT_IDS == [
            "greeks_exposure",
            "volatility_pricing",
            "time_decay_pnl",
            "strike_assignment",
            "macro_news_overlay",
        ]
        assert [s.lens for s in SEATS] == [
            "Greeks & Exposure",
            "Volatility & Pricing",
            "Time Decay & P&L",
            "Strike & Assignment",
            "Macro & News Overlay",
        ]
        assert [s.uses_news for s in SEATS] == [False, False, False, False, True]

    def test_fundamentals_seats_must_cite_a_figure(self):
        for seat in SEATS[:4]:
            text = quorum_agents.build_seat_agent(seat, "gemini-2.5-flash").instruction
            assert "FUNDAMENTALS" in text
            assert "cite at least one specific figure" in text

    def test_overlay_seat_cites_news_or_says_thin(self):
        text = quorum_agents.build_seat_agent(SEATS[4], "gemini-2.5-flash").instruction
        assert "headline" in text and "thin" in text

    def test_null_figures_are_unavailable_never_estimated(self):
        for seat in SEATS:
            text = quorum_agents.build_seat_agent(seat, "gemini-2.5-flash").instruction
            assert "A null figure means it is unavailable; never estimate or assume it" in text

    def test_research_focuses_on_events_before_expiry(self):
        text = quorum_agents.build_researcher_agent("gemini-2.5-flash").instruction
        assert "before the position's expiry" in text
        assert "earnings" in text

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
        assert ctx.as_of == datetime(2026, 9, 25, 14, 0, tzinfo=timezone.utc)

    def test_fundamentals_are_re_derived_and_position_level_computed(self):
        ctx = build_position_context([_leg()])
        f = ctx.legs[0].fundamentals
        assert f.realised_volatility == 0.12
        assert f.iv_rv_ratio == pytest.approx(0.18 / 0.12)
        assert f.position_delta == pytest.approx(-0.35 * -1 * 100)
        assert ctx.position_fundamentals.single_expiry is True
        assert ctx.position_fundamentals.max_profit == pytest.approx(420.0)
        assert ctx.position_fundamentals.max_loss_unbounded is True

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
        result = await run_quorum(
            build_position_context([_leg()]), model=_fake(replies), headline_fetcher=_fetcher(_HEADLINES)
        )
        assert result.verdict == "ROLL"
        assert result.valid_votes == 5
        assert result.seats == 5
        assert [v.seat for v in result.votes] == _SEAT_IDS
        assert result.macro_brief == "Rates steady; VIX low."
        assert result.headlines == _HEADLINES
        assert result.underlying_symbol == "SPY"
        assert result.model == "gemini-2.5-flash"
        assert result.as_of == datetime(2026, 9, 25, 14, 0, tzinfo=timezone.utc)
        assert result.position_fundamentals.max_profit == pytest.approx(420.0)
        roll_votes = [v for v in result.votes if v.action == "ROLL"]
        assert all(v.roll_direction == "out" for v in roll_votes)

    async def test_malformed_seat_abstains_without_affecting_others(self):
        replies = {sid: _ballot("CLOSE") for sid in _SEAT_IDS}
        replies[_SEAT_IDS[1]] = "garbage not json"
        replies[_SEAT_IDS[2]] = json.dumps({"action": "ROLL", "confidence": 0.5, "rationale": "no dir"})
        result = await run_quorum(build_position_context([_leg()]), model=_fake(replies), headline_fetcher=_fetcher([]))
        assert result.valid_votes == 3
        assert result.verdict == "CLOSE"
        abstained = [v.seat for v in result.votes if v.abstained]
        assert abstained == [_SEAT_IDS[1], _SEAT_IDS[2]]
        assert all(v.action is None for v in result.votes if v.abstained)

    async def test_raising_seat_abstains(self):
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        replies[_SEAT_IDS[0]] = RuntimeError("vertex down")
        result = await run_quorum(build_position_context([_leg()]), model=_fake(replies), headline_fetcher=_fetcher([]))
        assert result.votes[0].abstained is True
        assert result.valid_votes == 4
        assert result.verdict == "HOLD"

    async def test_slow_seat_times_out_and_abstains(self):
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        replies[_SEAT_IDS[4]] = 5.0
        result = await run_quorum(
            build_position_context([_leg()]), model=_fake(replies), seat_timeout=0.2,
            headline_fetcher=_fetcher([]),
        )
        assert result.votes[4].abstained is True
        assert result.valid_votes == 4

    async def test_research_failure_gives_none_brief(self):
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        replies["macro_researcher"] = RuntimeError("search failed")
        result = await run_quorum(build_position_context([_leg()]), model=_fake(replies), headline_fetcher=_fetcher([]))
        assert result.macro_brief is None
        assert result.verdict == "HOLD"

    async def test_all_fail_is_no_quorum(self):
        replies = {sid: "nope" for sid in _SEAT_IDS}
        result = await run_quorum(build_position_context([_leg()]), model=_fake(replies), headline_fetcher=_fetcher([]))
        assert result.verdict == "NO_QUORUM"
        assert result.quorum_met is False

    async def test_only_overlay_seat_receives_brief_and_headlines(self):
        replies = {"macro_researcher": "BRIEF-MARKER"}
        replies.update({sid: _ballot("HOLD", rationale=f"VOTE-{sid}") for sid in _SEAT_IDS})
        fake = _fake(replies)
        await run_quorum(build_position_context([_leg()]), model=fake, headline_fetcher=_fetcher(_HEADLINES))
        seats = _seat_requests(fake, _SEAT_IDS)
        assert set(seats) == set(_SEAT_IDS)
        for sid in _FUND_IDS:
            text = _request_text(seats[sid])
            assert "FUNDAMENTALS" in text
            assert "iv_rv_ratio" in text and "breakevens" in text
            assert "BRIEF-MARKER" not in text
            assert "Fed signals patience" not in text
            assert "VOTE-" not in text  # FR-006: independent votes
        overlay = _request_text(seats[_OVERLAY_ID])
        assert "FUNDAMENTALS" in overlay
        assert "BRIEF-MARKER" in overlay
        assert "Fed signals patience" in overlay
        assert "VOTE-" not in overlay

    async def test_fundamentals_seats_finish_before_slow_research(self):
        replies = {"macro_researcher": (0.5, "late brief")}
        replies.update({sid: _ballot("HOLD") for sid in _SEAT_IDS})
        fake = _fake(replies)
        await run_quorum(build_position_context([_leg()]), model=fake, headline_fetcher=_fetcher(_HEADLINES))
        research_done = fake.finished["macro_researcher"]
        for sid in _FUND_IDS:
            assert fake.finished[sid] < research_done
        assert fake.finished[_OVERLAY_ID] > research_done

    async def test_news_fetch_runs_alongside_research(self):
        """FR-119 / SC-101 structure: feeds 0.1 s ∥ research 0.2 s, then seat 5 0.1 s ≈ 0.3 s.
        The 017 ordering (feeds → research → seats) would take ≥ 0.4 s."""
        replies = {"macro_researcher": (0.2, "brief")}
        replies.update({sid: (0.1, _ballot("HOLD")) for sid in _SEAT_IDS})
        start = time.monotonic()
        await run_quorum(
            build_position_context([_leg()]), model=_fake(replies),
            headline_fetcher=_fetcher(_HEADLINES, delay=0.1),
        )
        assert time.monotonic() - start < 0.35

    async def test_research_failure_overlay_still_votes_on_headlines(self):
        replies = {sid: _ballot("CLOSE") for sid in _SEAT_IDS}
        replies["macro_researcher"] = RuntimeError("search failed")
        fake = _fake(replies)
        result = await run_quorum(build_position_context([_leg()]), model=fake, headline_fetcher=_fetcher(_HEADLINES))
        assert result.votes[4].abstained is False
        assert "Fed signals patience" in _request_text(_seat_requests(fake, [_OVERLAY_ID])[_OVERLAY_ID])

    async def test_headline_fetch_failure_is_tolerated(self):
        async def broken(underlying):
            raise RuntimeError("feeds down")

        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        result = await run_quorum(build_position_context([_leg()]), model=_fake(replies), headline_fetcher=broken)
        assert result.headlines == []
        assert result.valid_votes == 5

    async def test_default_fetcher_resolved_at_call_time(self, monkeypatch):
        called = []

        async def patched(underlying):
            called.append(underlying)
            return list(_HEADLINES)

        monkeypatch.setattr(quorum_agents, "fetch_headlines", patched)
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        result = await run_quorum(build_position_context([_leg()]), model=_fake(replies))
        assert called == ["SPY"]
        assert result.headlines == _HEADLINES


class TestPrivacy:
    async def test_no_identifiers_reach_the_model(self):
        """SC-003 / Constitution v3.3.0: nothing identifying in any model request."""
        replies = {sid: _ballot("HOLD") for sid in _SEAT_IDS}
        fake = _fake(replies)
        leg = _leg()
        await run_quorum(build_position_context([leg]), model=fake, headline_fetcher=_fetcher(_HEADLINES))
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
