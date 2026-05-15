"""Contract tests for the GET /api/accounts endpoint."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_auth_header(access_token: str = "test-access-token") -> str:
    return f"Bearer {access_token}"


_FIXTURE_ACCOUNTS = [
    {"accountNumber": "12345678", "hashValue": "abc123def456abc123def456abc123def456abc123"},
    {"accountNumber": "87654321", "hashValue": "xyz789uvw012xyz789uvw012xyz789uvw012xyz789"},
]


@pytest.fixture
def client():
    from src.api.main import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=True)


class TestAccountsEndpoint:
    def test_returns_200_with_masked_account_numbers(self, client):
        """GET /api/accounts returns 200 with masked accountNumbers and hashValues."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.auth.account_resolver.list_accounts", new_callable=AsyncMock) as mock_list,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_list.return_value = _FIXTURE_ACCOUNTS

            resp = client.get(
                "/api/accounts",
                headers={"Authorization": _make_auth_header()},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["accountNumber"] == "...5678"
        assert data[0]["hashValue"] == "abc123def456abc123def456abc123def456abc123"
        assert data[1]["accountNumber"] == "...4321"
        assert data[1]["hashValue"] == "xyz789uvw012xyz789uvw012xyz789uvw012xyz789"

    def test_returns_401_without_authorization_header(self, client):
        """GET /api/accounts without Authorization header returns 401."""
        resp = client.get("/api/accounts")
        assert resp.status_code == 401

    def test_returns_401_with_missing_bearer_prefix(self, client):
        """GET /api/accounts with wrong auth scheme returns 401."""
        resp = client.get(
            "/api/accounts",
            headers={"Authorization": "Token some-token"},
        )
        assert resp.status_code == 401

    def test_returns_empty_list_when_no_accounts(self, client):
        """GET /api/accounts returns empty list when no accounts on token."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.auth.account_resolver.list_accounts", new_callable=AsyncMock) as mock_list,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_list.return_value = []

            resp = client.get(
                "/api/accounts",
                headers={"Authorization": _make_auth_header()},
            )

        assert resp.status_code == 200
        assert resp.json() == []

    def test_disambiguates_accounts_with_same_last_four(self, client):
        """When two accounts share the same last 4 digits, more digits are shown."""
        accounts = [
            {"accountNumber": "11115678", "hashValue": "hash-aaa"},
            {"accountNumber": "22225678", "hashValue": "hash-bbb"},
        ]
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.auth.account_resolver.list_accounts", new_callable=AsyncMock) as mock_list,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_list.return_value = accounts

            resp = client.get(
                "/api/accounts",
                headers={"Authorization": _make_auth_header()},
            )

        data = resp.json()
        assert data[0]["accountNumber"] != data[1]["accountNumber"]
        assert data[0]["accountNumber"].startswith("...")
        assert data[1]["accountNumber"].startswith("...")

    def test_response_sets_no_cookies(self, client):
        """Successful /api/accounts response must not set any cookies."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.auth.account_resolver.list_accounts", new_callable=AsyncMock) as mock_list,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_list.return_value = _FIXTURE_ACCOUNTS

            resp = client.get(
                "/api/accounts",
                headers={"Authorization": _make_auth_header()},
            )

        assert "set-cookie" not in {k.lower() for k in resp.headers.keys()}


class TestPositionsRefreshWithAccountHash:
    def test_returns_422_for_unknown_account_hash(self, client):
        """GET /api/positions/refresh with unknown account_hash returns 422."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.positions.fetch_positions_and_greeks", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_fetch.side_effect = ValueError("Account hash 'bad-hash...' not found on this token")

            resp = client.get(
                "/api/positions/refresh",
                params={"account_hash": "bad-hash-not-real"},
                headers={"Authorization": _make_auth_header()},
            )

        assert resp.status_code == 422

    def test_accepts_valid_account_hash(self, client):
        """GET /api/positions/refresh with valid account_hash returns 200."""
        from datetime import date
        from decimal import Decimal
        from src.data.models import PositionView

        fixture = [PositionView(
            symbol="QQQ   260618P00450000",
            underlying_symbol="QQQ",
            option_type="put",
            strike=Decimal("450.00"),
            expiry_date=date(2026, 6, 18),
            quantity=-1,
            cost=Decimal("2.50"),
            current_mark=Decimal("1.80"),
            unrealised_pnl=Decimal("70.00"),
            days_to_expiry=46,
        )]
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.positions.fetch_positions_and_greeks", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_fetch.return_value = fixture

            resp = client.get(
                "/api/positions/refresh",
                params={"account_hash": "valid-hash-abc"},
                headers={"Authorization": _make_auth_header()},
            )

        assert resp.status_code == 200


class TestScreenerRefreshWithAccountHash:
    def test_returns_422_for_unknown_account_hash(self, client):
        """GET /api/screener/refresh with unknown account_hash returns 422."""
        with (
            patch("src.api.deps.schwab") as mock_schwab,
            patch("src.api.routes.screener.run_screener", new_callable=AsyncMock) as mock_run,
        ):
            mock_schwab.auth.client_from_access_functions.return_value = object()
            mock_run.side_effect = ValueError("Account hash 'bad-hash...' not found on this token")

            resp = client.get(
                "/api/screener/refresh",
                params={"account_hash": "bad-hash-not-real"},
                headers={"Authorization": _make_auth_header()},
            )

        assert resp.status_code == 422
