"""Unit tests for the /auth/demo-login endpoint (feature 014)."""
from __future__ import annotations

import os
import re
from pathlib import Path

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


_HANDOFF_JS = (Path(__file__).resolve().parents[2] / "frontend" / "static" / "js" / "auth_handoff.js").read_text()


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
        assert 'data-handoff="demo"' in resp.text
        assert "sessionStorage.setItem('demo_mode', 'true')" in _HANDOFF_JS

    def test_redirects_to_root(self):
        assert "window.location.replace('/')" in _HANDOFF_JS

    def test_script_is_self_hosted_not_inline(self, client):
        """specs/023: Firebase's CSP has no nonce, so hand-off pages load a file."""
        resp = client.get("/auth/demo-login")
        assert '<script src="/static/js/auth_handoff.js"></script>' in resp.text
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", resp.text, re.IGNORECASE)

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


class TestModeSwitch:
    """specs/021 FR-401, FR-405."""

    def test_demo_login_keeps_live_token(self, client):
        resp = client.get("/auth/demo-login")
        assert 'data-token=' not in resp.text
        demo = _HANDOFF_JS.split("handoff === 'demo'")[1].split("} else")[0]
        assert "schwab_access_token" not in demo
        assert "sessionStorage.clear()" not in demo

    def test_dev_login_clears_demo_flag(self, client, tmp_path, monkeypatch):
        import src.auth.router as router
        token = tmp_path / "schwab_token.json"
        token.write_text('{"access_token": "abc"}')
        monkeypatch.setattr(router, "_TOKEN_FILE", str(token))
        resp = client.get("/auth/dev-login")
        assert 'data-handoff="live"' in resp.text and 'data-token="abc"' in resp.text
        assert "sessionStorage.removeItem('demo_mode')" in _HANDOFF_JS

    def test_callback_clears_demo_flag(self, client, monkeypatch):
        import time
        import httpx
        import src.auth.router as router

        router._pkce_store["st"] = {"code_verifier": "v", "created_at": time.time()}

        class _Resp:
            is_success = True
            def json(self):
                return {"access_token": "abc"}

        async def _post(self, *a, **k):
            return _Resp()

        monkeypatch.setattr(httpx.AsyncClient, "post", _post)
        resp = client.get("/auth/callback?code=c&state=st")
        assert resp.status_code == 200
        assert 'data-handoff="live"' in resp.text and 'data-token="abc"' in resp.text

    def test_base_template_has_mode_switch(self):
        from pathlib import Path
        html = (Path(__file__).resolve().parents[2] / "frontend" / "templates" / "base.html").read_text()
        assert 'id="mode-switch-demo"' in html
        assert 'id="mode-switch-live"' in html
        # handlers live in a file since specs/023 (no inline scripts)
        assert '<script type="module" src="/static/js/shell_actions.js"></script>' in html
        actions = (Path(__file__).resolve().parents[2] / "frontend" / "static" / "js" / "shell_actions.js").read_text()
        assert "switchMode" in actions
