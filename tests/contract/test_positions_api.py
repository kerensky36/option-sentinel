"""Contract tests for the positions refresh API."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.data.models import PositionView


def _make_auth_header(access_token: str = "test-access-token") -> str:
    """Build a valid Authorization: Bearer header with a raw access token string."""
    return f"Bearer {access_token}"


_FIXTURE_POSITIONS = [
    PositionView(
        symbol="QQQ   260618P00450000",
        underlying_symbol="QQQ",
        option_type="put",
        strike=Decimal("450.00"),
        expiry_date=date(2026, 6, 18),
        quantity=-1,
        cost=Decimal("2.5000"),
        current_mark=Decimal("1.8000"),
        unrealised_pnl=Decimal("70.0000"),
        days_to_expiry=46,
        delta=-0.25,
        gamma=0.01,
        theta=-0.05,
        vega=0.12,
        implied_volatility=0.28,
        delta_source="api",
        gamma_source="api",
        theta_source="api",
        vega_source="api",
        iv_source="api",
    ),
    PositionView(
        symbol="SPY   260515C00560000",
        underlying_symbol="SPY",
        option_type="call",
        strike=Decimal("560.00"),
        expiry_date=date(2026, 5, 15),
        quantity=1,
        cost=Decimal("5.0000"),
        current_mark=Decimal("3.5000"),
        unrealised_pnl=Decimal("-150.0000"),
        days_to_expiry=12,
        delta=0.40,
        gamma=0.02,
        theta=-0.08,
        vega=0.20,
        implied_volatility=None,
        delta_source="calculated",
        gamma_source="calculated",
        theta_source="calculated",
        vega_source="calculated",
        iv_source=None,
    ),
]


@pytest.fixture
def client():
    """TestClient with patched schwab client to avoid real Schwab calls."""
    from src.api.main import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=True)


class TestPositionsRefresh:
    def test_returns_200_json_array_with_valid_auth(self, client):
        """GET /api/positions/refresh with valid Authorization returns 200 JSON array."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.positions.fetch_positions_and_greeks", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_fetch.return_value = _FIXTURE_POSITIONS

            resp = client.get(
                "/api/positions/refresh",
                headers={"Authorization": _make_auth_header()},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["symbol"] == "QQQ   260618P00450000"
        assert data[1]["symbol"] == "SPY   260515C00560000"

    def test_returns_401_without_authorization_header(self, client):
        """GET /api/positions/refresh without Authorization header returns 401."""
        resp = client.get("/api/positions/refresh")
        assert resp.status_code == 401

    def test_returns_401_with_missing_bearer_prefix(self, client):
        """GET /api/positions/refresh with wrong auth scheme returns 401."""
        resp = client.get(
            "/api/positions/refresh",
            headers={"Authorization": "Token some-token"},
        )
        assert resp.status_code == 401

    def test_returns_401_with_empty_bearer_token(self, client):
        """GET /api/positions/refresh with empty Bearer value returns 401."""
        resp = client.get(
            "/api/positions/refresh",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_response_sets_no_cookies(self, client):
        """Successful response must not set any cookies."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.positions.fetch_positions_and_greeks", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_fetch.return_value = _FIXTURE_POSITIONS

            resp = client.get(
                "/api/positions/refresh",
                headers={"Authorization": _make_auth_header()},
            )

        assert "set-cookie" not in {k.lower() for k in resp.headers.keys()}

    def test_response_contains_greeks_fields(self, client):
        """Response objects include all Greek fields."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.positions.fetch_positions_and_greeks", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_fetch.return_value = _FIXTURE_POSITIONS

            resp = client.get(
                "/api/positions/refresh",
                headers={"Authorization": _make_auth_header()},
            )

        data = resp.json()
        first = data[0]
        assert "delta" in first
        assert "gamma" in first
        assert "theta" in first
        assert "vega" in first
        assert "implied_volatility" in first
        assert first["delta_source"] == "api"
