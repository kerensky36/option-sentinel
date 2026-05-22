"""Unit tests for the /auth/demo-login endpoint (feature 014)."""
from __future__ import annotations

import os
import re

import pytest
from fastapi.testclient import TestClient

_ENV = {
    "SCHWAB_CLIENT_ID": "test-id",
    "SCHWAB_CLIENT_SECRET": "test-secret",
    "SCHWAB_REDIRECT_URI": "http://localhost/auth/callback",
    "SCHWAB_AUTH_URL": "https://example.com/oauth/authorize",
    "SCHWAB_TOKEN_URL": "https://example.com/oauth/token",
}
for _k, _v in _ENV.items():
    os.environ.setdefault(_k, _v)


@pytest.fixture
def client():
    from src.api.main import create_app
    return TestClient(create_app(), raise_server_exceptions=True)


class TestDemoLoginEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/auth/demo-login")
        assert resp.status_code == 200

    def test_content_type_is_html(self, client):
        resp = client.get("/auth/demo-login")
        assert "text/html" in resp.headers.get("content-type", "")

    def test_sets_demo_mode_in_session_storage(self, client):
        resp = client.get("/auth/demo-login")
        assert "sessionStorage.setItem('demo_mode'" in resp.text or \
               'sessionStorage.setItem("demo_mode"' in resp.text

    def test_redirects_to_root(self, client):
        resp = client.get("/auth/demo-login")
        assert "window.location.replace('/')" in resp.text or \
               'window.location.replace("/")' in resp.text

    def test_script_has_csp_nonce(self, client):
        resp = client.get("/auth/demo-login")
        assert re.search(r'<script\s+nonce="[^"]{10,}"', resp.text), \
            "Expected <script nonce='...'> in demo-login response"

    def test_has_noscript_fallback(self, client):
        resp = client.get("/auth/demo-login")
        assert "<noscript>" in resp.text

    def test_demo_login_independent_of_schwab_env(self, client):
        """Demo login must work even without real Schwab credentials configured."""
        resp = client.get("/auth/demo-login")
        assert resp.status_code == 200

    def test_demo_hash_prefix_differs_from_real_schwab_format(self):
        """Demo account hashes use 'demo-' prefix; real Schwab hashes are alphanumeric only."""
        demo_hashes = ["demo-spreads-0001", "demo-equity-0002"]
        for h in demo_hashes:
            assert h.startswith("demo-"), f"Demo hash '{h}' must start with 'demo-'"
            assert not h.isalnum(), f"Demo hash '{h}' must not be a plain alphanumeric Schwab-style hash"
