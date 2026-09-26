"""Contract tests for the Data Use Disclosure page (specs/017 US4, FR-019; Constitution v3.3.0)."""
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

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.api.main import create_app
    return TestClient(create_app())


class TestDataUsePage:
    def test_reachable_without_auth(self, client):
        resp = client.get("/data-use")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    @pytest.mark.parametrize(
        "row",
        [
            "Schwab login",
            "Schwab access token",
            "Positions",
            "Covered call screener",
            "Account selection",
            "Server processing",
            "Security logs",
            "Quorum — Google Vertex AI",
            "Quorum — news feeds",
        ],
    )
    def test_lists_every_data_use(self, client, row):
        assert row in client.get("/data-use").text

    def test_states_no_identifying_data_to_vertex(self, client):
        html = client.get("/data-use").text
        assert "No user-identifiable or pedigree data" in html

    def test_has_retention_and_destination_columns(self, client):
        html = client.get("/data-use").text
        for header in ("Data", "Sent to", "Why", "Kept for"):
            assert f">{header}<" in html

    def test_has_csp_header(self, client):
        assert "Content-Security-Policy" in client.get("/data-use").headers


class TestDataUseLinks:
    def test_login_page_links_to_disclosure(self, client):
        assert 'href="/data-use"' in client.get("/auth/login").text

    @pytest.mark.parametrize("path", ["/", "/screener"])
    def test_app_pages_link_to_disclosure(self, client, path):
        assert 'href="/data-use"' in client.get(path).text
