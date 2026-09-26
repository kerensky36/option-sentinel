"""Contract tests for POST /api/quorum/vote (specs/017 contracts/quorum-api-contract.md)."""
from __future__ import annotations

import os

# Set required env vars before app import so create_app() does not raise.
for _k, _v in {
    "SCHWAB_CLIENT_ID": "test-id",
    "SCHWAB_CLIENT_SECRET": "test-secret",
    "SCHWAB_REDIRECT_URI": "http://localhost/auth/callback",
    "SCHWAB_AUTH_URL": "https://example.com/oauth/authorize",
    "SCHWAB_TOKEN_URL": "https://example.com/oauth/token",
}.items():
    os.environ.setdefault(_k, _v)

import asyncio
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.data.models import Headline, PositionView, QuorumResult

_TOKEN = "tok-SECRET-123"
_HASH = "HASH-ABCDEF-999"
_AUTH = {"Authorization": f"Bearer {_TOKEN}"}


def _leg(symbol: str, underlying: str = "SPY", strike: str = "560") -> PositionView:
    return PositionView(
        symbol=symbol,
        underlying_symbol=underlying,
        option_type="call",
        strike=Decimal(strike),
        expiry_date=date(2026, 10, 17),
        quantity=-1,
        cost=Decimal("4.20"),
        current_mark=Decimal("3.10"),
        unrealised_pnl=Decimal("110"),
        days_to_expiry=22,
        delta=-0.35,
        implied_volatility=0.18,
        underlying_price=Decimal("552.10"),
    )


_POSITIONS = [
    _leg("SPY   261017C00560000"),
    _leg("SPY   261017C00570000", strike="570"),
    _leg("QQQ   261017C00450000", underlying="QQQ", strike="450"),
]

_HEADLINES = [Headline(publisher="CNBC", title="Fed holds", link="https://www.cnbc.com/x")]


def _result(**kw) -> QuorumResult:
    base = dict(
        verdict="HOLD",
        quorum_met=True,
        seats=5,
        valid_votes=5,
        tally=[
            {"action": "CLOSE", "votes": 0, "mean_confidence": None},
            {"action": "HOLD", "votes": 5, "mean_confidence": 0.6},
            {"action": "ROLL", "votes": 0, "mean_confidence": None},
        ],
        votes=[{"seat": f"s{i}", "lens": f"L{i}", "action": "HOLD", "confidence": 0.6} for i in range(5)],
        macro_brief="brief",
        headlines=_HEADLINES,
        underlying_symbol="SPY",
        model="gemini-2.5-flash",
        generated_at=datetime(2026, 9, 25, tzinfo=timezone.utc),
    )
    base.update(kw)
    return QuorumResult(**base)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    from src.api.main import create_app, limiter
    limiter.reset()
    return TestClient(create_app(), raise_server_exceptions=True)


def _post(client, body, headers=_AUTH):
    return client.post("/api/quorum/vote", json=body, headers=headers)


@pytest.fixture
def patched():
    with (
        patch("src.api.deps.schwab") as mock_schwab,
        patch("src.api.routes.quorum.fetch_positions_and_greeks", new_callable=AsyncMock) as fetch,
        patch("src.api.routes.quorum.fetch_headlines", new_callable=AsyncMock) as news,
        patch("src.api.routes.quorum.run_quorum", new_callable=AsyncMock) as run,
    ):
        mock_schwab.auth.client_from_access_functions.return_value = object()
        fetch.return_value = _POSITIONS
        news.return_value = _HEADLINES
        run.return_value = _result()
        yield {"fetch": fetch, "news": news, "run": run}


class TestHappyPath:
    def test_returns_quorum_result(self, client, patched):
        resp = _post(client, {"symbols": ["SPY   261017C00560000"], "account_hash": _HASH})
        assert resp.status_code == 200
        data = resp.json()
        assert data["verdict"] == "HOLD"
        assert len(data["votes"]) == 5
        assert [t["action"] for t in data["tally"]] == ["CLOSE", "HOLD", "ROLL"]
        assert data["disclaimer"]
        assert resp.headers["Cache-Control"] == "no-store"

    def test_passes_account_hash_to_schwab_fetch(self, client, patched):
        _post(client, {"symbols": ["SPY   261017C00560000"], "account_hash": _HASH})
        assert patched["fetch"].await_args.kwargs["account_hash"] == _HASH

    def test_spread_legs_become_one_context(self, client, patched):
        _post(client, {"symbols": ["SPY   261017C00560000", "SPY   261017C00570000"]})
        ctx = patched["run"].await_args.args[0]
        assert len(ctx.legs) == 2
        assert ctx.underlying_symbol == "SPY"

    def test_only_ticker_sent_to_news(self, client, patched):
        _post(client, {"symbols": ["SPY   261017C00560000"], "account_hash": _HASH})
        assert patched["news"].await_args.args == ("SPY",)


class TestErrors:
    def test_401_without_auth(self, client):
        resp = _post(client, {"symbols": ["X"]}, headers={})
        assert resp.status_code == 401

    def test_404_unknown_symbol(self, client, patched):
        resp = _post(client, {"symbols": ["SPY   261017C00999000"]})
        assert resp.status_code == 404
        patched["run"].assert_not_awaited()

    def test_422_mixed_underlyings(self, client, patched):
        resp = _post(client, {"symbols": ["SPY   261017C00560000", "QQQ   261017C00450000"]})
        assert resp.status_code == 422
        patched["run"].assert_not_awaited()

    @pytest.mark.parametrize("symbols", [[], ["a", "b", "c", "d", "e"], ["a", "a"]])
    def test_422_bad_symbols(self, client, patched, symbols):
        resp = _post(client, {"symbols": symbols})
        assert resp.status_code == 422

    def test_422_unknown_account_hash(self, client, patched):
        patched["fetch"].side_effect = ValueError("account_hash not found")
        resp = _post(client, {"symbols": ["SPY   261017C00560000"], "account_hash": "nope"})
        assert resp.status_code == 422
        patched["run"].assert_not_awaited()

    def test_503_when_not_configured(self, client, patched, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT")
        resp = _post(client, {"symbols": ["SPY   261017C00560000"]})
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Quorum is not configured on this server"
        patched["fetch"].assert_not_awaited()
        patched["run"].assert_not_awaited()

    def test_504_on_overall_timeout(self, client, patched):
        async def slow(*a, **k):
            await asyncio.sleep(5)

        patched["run"].side_effect = slow
        with patch("src.api.routes.quorum.QUORUM_TIMEOUT_SECONDS", 0.1):
            resp = _post(client, {"symbols": ["SPY   261017C00560000"]})
        assert resp.status_code == 504

    def test_429_after_five_requests(self, client, patched):
        codes = [_post(client, {"symbols": ["SPY   261017C00560000"]}).status_code for _ in range(6)]
        assert codes[:5] == [200] * 5
        assert codes[5] == 429


class TestPrivacyEndToEnd:
    def test_no_token_or_account_hash_in_any_model_request(self, client):
        """SC-003 end to end: real run_quorum with a fake ADK model."""
        from tests.unit.test_quorum_agents import _SEAT_IDS, _ballot, _fake

        fake = _fake({sid: _ballot("HOLD") for sid in _SEAT_IDS})
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.quorum.fetch_positions_and_greeks", new_callable=AsyncMock) as fetch,
            patch("src.api.routes.quorum.fetch_headlines", new_callable=AsyncMock) as news,
            patch("src.services.quorum_agents.default_model", return_value=fake),
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            fetch.return_value = _POSITIONS
            news.return_value = _HEADLINES
            resp = _post(client, {"symbols": ["SPY   261017C00560000"], "account_hash": _HASH})

        assert resp.status_code == 200
        assert resp.json()["verdict"] == "HOLD"
        assert fake.requests
        for r in fake.requests:
            text = json.dumps([c.model_dump(mode="json") for c in r.contents]) + str(r.config.system_instruction)
            assert _TOKEN not in text
            assert _HASH not in text
            assert "SPY   261017C00560000" not in text
