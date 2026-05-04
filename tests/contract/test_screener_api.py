"""Contract tests for the screener refresh API."""
from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.data.models import ScreenerResultView


def _make_auth_header(token_dict: dict | None = None) -> str:
    if token_dict is None:
        token_dict = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "Bearer",
            "access_token_expiry": 9999999999,
        }
    json_str = json.dumps(token_dict)
    b64 = base64.b64encode(json_str.encode()).decode()
    return f"Bearer {b64}"


_FIXTURE_RESULTS = [
    ScreenerResultView(
        ticker="QQQ",
        shares=100,
        stock_price=475.50,
        iv_rank=65.0,
        recommended_strike=490.0,
        recommended_expiry="2026-06-20",
        bid_premium=3.20,
        annualised_yield=16.5,
        call_delta=0.25,
        days_to_earnings=None,
        composite_score=72.5,
        recommendation_status="recommended",
        sort_order=0,
    ),
    ScreenerResultView(
        ticker="AAPL",
        shares=200,
        stock_price=185.00,
        iv_rank=30.0,
        recommended_strike=None,
        recommended_expiry=None,
        bid_premium=None,
        annualised_yield=None,
        call_delta=None,
        days_to_earnings=5,
        composite_score=0.0,
        recommendation_status="suppressed",
        sort_order=1,
    ),
]


@pytest.fixture
def client():
    from src.api.main import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=True)


class TestScreenerRefresh:
    def test_returns_200_json_array_with_valid_auth(self, client):
        """GET /api/screener/refresh with valid Authorization returns 200 JSON array."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.screener.run_screener", new_callable=AsyncMock) as mock_run,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_run.return_value = _FIXTURE_RESULTS

            resp = client.get(
                "/api/screener/refresh",
                headers={"Authorization": _make_auth_header()},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["ticker"] == "QQQ"
        assert data[1]["ticker"] == "AAPL"

    def test_returns_401_without_authorization_header(self, client):
        """GET /api/screener/refresh without Authorization header returns 401."""
        resp = client.get("/api/screener/refresh")
        assert resp.status_code == 401

    def test_suppressed_rows_present_in_response(self, client):
        """Suppressed rows are included in the response with status='suppressed'."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.screener.run_screener", new_callable=AsyncMock) as mock_run,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_run.return_value = _FIXTURE_RESULTS

            resp = client.get(
                "/api/screener/refresh",
                headers={"Authorization": _make_auth_header()},
            )

        data = resp.json()
        statuses = {r["ticker"]: r["recommendation_status"] for r in data}
        assert statuses["QQQ"] == "recommended"
        assert statuses["AAPL"] == "suppressed"

    def test_response_has_all_screener_fields(self, client):
        """Response objects include all ScreenerResultView fields."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.screener.run_screener", new_callable=AsyncMock) as mock_run,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_run.return_value = _FIXTURE_RESULTS

            resp = client.get(
                "/api/screener/refresh",
                headers={"Authorization": _make_auth_header()},
            )

        data = resp.json()
        first = data[0]
        required_fields = [
            "ticker", "shares", "stock_price", "iv_rank",
            "recommended_strike", "recommended_expiry",
            "bid_premium", "annualised_yield", "call_delta",
            "days_to_earnings", "composite_score",
            "recommendation_status", "sort_order",
        ]
        for field in required_fields:
            assert field in first, f"Missing field: {field}"
