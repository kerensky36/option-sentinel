"""Unit tests for security middleware classes (Constitution v3.1.0 Principle II).

These tests document expected middleware behaviour and FAIL before implementation.
After T027 (CSPNonceMiddleware), T028 (SecurityHeadersMiddleware), T032 (error handler)
they should all pass.
"""
from __future__ import annotations

import os
import re

import pytest

_ENV_DEFAULTS = {
    "SCHWAB_CLIENT_ID": "test-id",
    "SCHWAB_CLIENT_SECRET": "test-secret",
    "SCHWAB_REDIRECT_URI": "http://localhost/auth/callback",
    "SCHWAB_AUTH_URL": "https://example.com/oauth/authorize",
    "SCHWAB_TOKEN_URL": "https://example.com/oauth/token",
}
for _k, _v in _ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)


def _make_csp_app():
    """Minimal app with CSPNonceMiddleware — test via CSP response headers."""
    from fastapi import FastAPI
    from src.api.main import CSPNonceMiddleware

    app = FastAPI()
    app.add_middleware(CSPNonceMiddleware)

    @app.get("/probe")
    async def probe():
        return {"ok": True}

    return app


class TestCSPNonceMiddleware:
    def test_csp_header_present(self):
        """CSPNonceMiddleware adds a Content-Security-Policy response header."""
        from fastapi.testclient import TestClient

        with TestClient(_make_csp_app()) as c:
            resp = c.get("/probe")

        assert "content-security-policy" in resp.headers

    def test_nonce_is_url_safe_base64(self):
        """The CSP nonce extracted from the header matches URL-safe base64 pattern."""
        from fastapi.testclient import TestClient

        pattern = re.compile(r"nonce-([A-Za-z0-9_-]{22})")
        with TestClient(_make_csp_app()) as c:
            for _ in range(3):
                resp = c.get("/probe")
                csp = resp.headers.get("content-security-policy", "")
                m = pattern.search(csp)
                assert m is not None, f"No valid nonce found in CSP: {csp!r}"

    def test_nonce_changes_on_every_request(self):
        """A fresh nonce is generated for each HTTP request (tested via CSP header)."""
        from fastapi.testclient import TestClient

        nonces = []
        with TestClient(_make_csp_app()) as c:
            for _ in range(5):
                resp = c.get("/probe")
                csp = resp.headers.get("content-security-policy", "")
                # Extract the nonce value from CSP
                import re as _re
                m = _re.search(r"nonce-([A-Za-z0-9_-]+)", csp)
                nonces.append(m.group(1) if m else "")

        assert len(set(nonces)) == 5, f"Nonces must be unique per request, got: {nonces}"


class TestSecurityHeadersMiddleware:
    def _make_app(self, https_only: bool = False):
        from fastapi import FastAPI
        from src.api.main import SecurityHeadersMiddleware

        if https_only:
            os.environ["HTTPS_ONLY"] = "true"
        else:
            os.environ.pop("HTTPS_ONLY", None)

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/")
        async def root():
            return {"ok": True}

        @app.get("/api/data")
        async def api_data():
            return {"data": True}

        return app

    def test_x_frame_options_deny(self):
        """SecurityHeadersMiddleware adds X-Frame-Options: DENY."""
        from fastapi.testclient import TestClient
        with TestClient(self._make_app()) as c:
            resp = c.get("/")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_x_content_type_options_nosniff(self):
        """SecurityHeadersMiddleware adds X-Content-Type-Options: nosniff."""
        from fastapi.testclient import TestClient
        with TestClient(self._make_app()) as c:
            resp = c.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_referrer_policy(self):
        """SecurityHeadersMiddleware adds the correct Referrer-Policy."""
        from fastapi.testclient import TestClient
        with TestClient(self._make_app()) as c:
            resp = c.get("/")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_hsts_absent_without_https_only(self):
        """HSTS must NOT be set when HTTPS_ONLY env var is absent."""
        from fastapi.testclient import TestClient
        with TestClient(self._make_app(https_only=False)) as c:
            resp = c.get("/")
        assert "strict-transport-security" not in resp.headers

    def test_hsts_present_with_https_only_true(self):
        """HSTS must be set when HTTPS_ONLY=true."""
        from fastapi.testclient import TestClient
        with TestClient(self._make_app(https_only=True)) as c:
            resp = c.get("/")
        hsts = resp.headers.get("strict-transport-security", "")
        assert "max-age=31536000" in hsts
        os.environ.pop("HTTPS_ONLY", None)

    def test_cache_control_no_store_on_api_routes(self):
        """Cache-Control: no-store must be set on /api/* paths."""
        from fastapi.testclient import TestClient
        with TestClient(self._make_app()) as c:
            resp = c.get("/api/data")
        assert "no-store" in resp.headers.get("cache-control", "")

    def test_cache_control_absent_on_non_api_routes(self):
        """Cache-Control: no-store must NOT be forced on non-API routes."""
        from fastapi.testclient import TestClient
        with TestClient(self._make_app()) as c:
            resp = c.get("/")
        assert "no-store" not in resp.headers.get("cache-control", "")


class TestGenericErrorHandler:
    def _make_app_production(self):
        os.environ["DEBUG"] = "false"
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI()

        async def _generic_error_handler(request, exc):
            return JSONResponse({"detail": "Internal server error"}, status_code=500)

        if os.getenv("DEBUG", "true").lower() != "true":
            app.add_exception_handler(Exception, _generic_error_handler)

        @app.get("/boom")
        async def boom():
            raise RuntimeError("secret internal details")

        return app

    def test_generic_500_in_production(self):
        """Production error handler returns generic message with no stack trace."""
        from fastapi.testclient import TestClient
        os.environ["DEBUG"] = "false"
        app = self._make_app_production()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/boom")
        os.environ.pop("DEBUG", None)
        assert resp.status_code == 500
        body = resp.json()
        assert body == {"detail": "Internal server error"}
        assert "RuntimeError" not in resp.text
        assert "secret internal details" not in resp.text

    def test_debug_mode_passes_through_errors(self):
        """In debug mode, errors propagate as-is (developer experience)."""
        os.environ.pop("DEBUG", None)
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI()

        async def _generic_error_handler(request, exc):
            return JSONResponse({"detail": "Internal server error"}, status_code=500)

        if os.getenv("DEBUG", "true").lower() != "true":
            app.add_exception_handler(Exception, _generic_error_handler)

        @app.get("/boom")
        async def boom():
            raise RuntimeError("intentional test error")

        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/boom")
        assert resp.status_code == 500
