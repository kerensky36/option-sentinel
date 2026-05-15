"""Contract tests for security response headers (Constitution v3.1.0 Principle II).

These tests document the security header requirements and FAIL before implementation.
After T026-T029 (middleware), T030 (rate limiting), they should all pass.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Set required env vars before app import so create_app() does not raise.
_ENV_DEFAULTS = {
    "SCHWAB_CLIENT_ID": "test-id",
    "SCHWAB_CLIENT_SECRET": "test-secret",
    "SCHWAB_REDIRECT_URI": "http://localhost/auth/callback",
    "SCHWAB_AUTH_URL": "https://example.com/oauth/authorize",
    "SCHWAB_TOKEN_URL": "https://example.com/oauth/token",
}
for _k, _v in _ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)


@pytest.fixture
def client():
    from src.api.main import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


class TestSecurityResponseHeaders:
    def test_x_frame_options_deny(self, client):
        """Every response must include X-Frame-Options: DENY (clickjacking prevention)."""
        resp = client.get("/auth/login")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_x_content_type_options_nosniff(self, client):
        """Every response must include X-Content-Type-Options: nosniff."""
        resp = client.get("/auth/login")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_referrer_policy(self, client):
        """Every response must include Referrer-Policy: strict-origin-when-cross-origin."""
        resp = client.get("/auth/login")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_security_headers_on_api_route(self, client):
        """Security headers apply to API routes too, not just HTML pages."""
        resp = client.get("/api/accounts")  # 401 expected
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_hsts_absent_without_https_only_env(self, client):
        """HSTS must NOT be set when HTTPS_ONLY env var is absent or false (dev mode)."""
        old = os.environ.pop("HTTPS_ONLY", None)
        try:
            resp = client.get("/auth/login")
            assert "strict-transport-security" not in resp.headers
        finally:
            if old is not None:
                os.environ["HTTPS_ONLY"] = old


class TestContentSecurityPolicy:
    def test_csp_header_present_on_html(self, client):
        """HTML responses must include a Content-Security-Policy header."""
        resp = client.get("/auth/login")
        csp = resp.headers.get("content-security-policy", "")
        assert csp != "", "Content-Security-Policy header must be present"

    def test_csp_contains_nonce(self, client):
        """The CSP script-src directive must include a per-request nonce."""
        resp = client.get("/auth/login")
        csp = resp.headers.get("content-security-policy", "")
        assert "nonce-" in csp, "CSP script-src must contain a nonce token"

    def test_csp_nonce_unique_per_request(self, client):
        """Each request must produce a unique CSP nonce."""
        resp1 = client.get("/auth/login")
        resp2 = client.get("/auth/login")
        csp1 = resp1.headers.get("content-security-policy", "")
        csp2 = resp2.headers.get("content-security-policy", "")
        assert csp1 != csp2, "CSP nonce must differ between requests"

    def test_csp_script_src_forbids_unsafe_inline(self, client):
        """script-src in CSP must not include 'unsafe-inline'."""
        resp = client.get("/auth/login")
        csp = resp.headers.get("content-security-policy", "")
        for directive in csp.split(";"):
            directive = directive.strip()
            if directive.startswith("script-src"):
                assert "unsafe-inline" not in directive, (
                    "script-src must not allow unsafe-inline (XSS risk)"
                )

    def test_csp_forbids_object_src(self, client):
        """CSP must include object-src 'none'."""
        resp = client.get("/auth/login")
        csp = resp.headers.get("content-security-policy", "")
        assert "object-src 'none'" in csp


class TestCacheControl:
    def test_api_routes_have_no_store(self, client):
        """API routes must include Cache-Control: no-store."""
        resp = client.get("/api/accounts")  # returns 401 but headers must be set
        cache_control = resp.headers.get("cache-control", "")
        assert "no-store" in cache_control

    def test_api_screener_has_no_store(self, client):
        """GET /api/screener/refresh must include Cache-Control: no-store."""
        resp = client.get("/api/screener/refresh")
        cache_control = resp.headers.get("cache-control", "")
        assert "no-store" in cache_control


class TestCORS:
    def test_foreign_origin_gets_no_acao_header(self, client):
        """Requests from unknown origins must not receive Access-Control-Allow-Origin."""
        resp = client.get(
            "/api/accounts",
            headers={"Origin": "https://evil.example.com"},
        )
        assert "access-control-allow-origin" not in {
            k.lower() for k in resp.headers.keys()
        }, "Foreign origins must not receive CORS permission"

    def test_allowed_origin_gets_acao_header(self, client):
        """Requests from the configured ALLOWED_ORIGIN receive the ACAO header."""
        allowed = os.getenv("ALLOWED_ORIGIN", "http://localhost:8000")
        resp = client.get(
            "/api/accounts",
            headers={"Origin": allowed},
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == allowed, f"ALLOWED_ORIGIN {allowed!r} must be permitted"


class TestRateLimiting:
    def test_auth_start_returns_429_after_limit(self, client):
        """The /auth/start endpoint returns 429 after 10 requests per minute."""
        statuses = []
        for _ in range(12):
            r = client.get("/auth/start", follow_redirects=False)
            statuses.append(r.status_code)
        assert 429 in statuses, (
            "Rate limiting must return 429 after limit exceeded for /auth/start"
        )
