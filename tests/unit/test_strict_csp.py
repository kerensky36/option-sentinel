"""Self-hosted styles and a strict script CSP on every page (specs/023)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

for _k, _v in {
    "SCHWAB_CLIENT_ID": "test-id",
    "SCHWAB_CLIENT_SECRET": "test-secret",
    "SCHWAB_REDIRECT_URI": "http://localhost/auth/callback",
    "SCHWAB_AUTH_URL": "https://example.com/oauth/authorize",
    "SCHWAB_TOKEN_URL": "https://example.com/oauth/token",
}.items():
    os.environ.setdefault(_k, _v)

_REPO = Path(__file__).resolve().parents[2]
_TEMPLATES = sorted((_REPO / "frontend" / "templates").rglob("*.html"))
_CSS = _REPO / "frontend" / "static" / "css" / "app.css"
_INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", re.I)


def _script_src(csp: str) -> str:
    return next(d for d in csp.split(";") if d.strip().startswith("script-src")).strip()


@pytest.mark.parametrize("template", _TEMPLATES, ids=lambda p: p.name)
class TestTemplates:
    def test_no_third_party_script(self, template):
        """FR-601."""
        text = template.read_text()
        assert "cdn.tailwindcss.com" not in text
        for src in re.findall(r'<script[^>]*\bsrc="([^"]+)"', text):
            assert src.startswith("/static/js/"), src

    def test_no_inline_script_body(self, template):
        """FR-603."""
        assert not _INLINE_SCRIPT.search(template.read_text())


@pytest.mark.parametrize("name", ["base.html", "login.html", "data_use.html"])
def test_full_pages_link_self_hosted_css(name):
    assert '<link rel="stylesheet" href="/static/css/app.css">' in (_REPO / "frontend" / "templates" / name).read_text()


def test_built_css_has_theme_and_used_classes():
    """FR-602: committed build carries the custom theme and classes from templates and JS."""
    css = _CSS.read_text()
    assert "JetBrains Mono" in css
    assert re.search(r"\.text-xs\{font-size:9px", css)
    for cls in (r"\.bg-gray-950", r"\.md\\:flex", r"\.text-red-400", r"\.hover\\:bg-red-800:hover", r"\.min-h-screen"):
        assert re.search(cls, css), cls


def test_cloud_run_csp_has_no_third_party_script_host():
    """FR-604."""
    from src.api.main import _CSP
    script_src = _script_src(_CSP.format(nonce="n"))
    assert script_src == "script-src 'self' 'nonce-n'"


def test_firebase_sends_strict_csp_and_security_headers():
    """FR-605."""
    config = json.loads((_REPO / "firebase.json").read_text())
    rule = next(h for h in config["hosting"]["headers"] if h["source"] == "**")
    headers = {h["key"]: h["value"] for h in rule["headers"]}
    csp = headers["Content-Security-Policy"]
    assert _script_src(csp) == "script-src 'self'"
    for directive in ("object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'", "default-src 'self'"):
        assert directive in csp
    assert "unsafe-eval" not in csp
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "max-age=31536000" in headers["Strict-Transport-Security"]


def test_built_dist_pages_have_no_inline_or_third_party_scripts(tmp_path):
    """US2-4: the pages Firebase actually serves."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_frontend", _REPO / "scripts" / "build_frontend.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dist = tmp_path / "dist"
    module.build(out_dir=dist)
    pages = list(dist.rglob("*.html"))
    assert pages
    for page in pages:
        text = page.read_text()
        assert not _INLINE_SCRIPT.search(text), page
        assert "cdn.tailwindcss.com" not in text, page
    assert (dist / "static" / "css" / "app.css").exists()


def test_data_use_no_longer_lists_tailwind_cdn():
    """FR-607."""
    assert "cdn.tailwindcss.com" not in (_REPO / "frontend" / "templates" / "data_use.html").read_text()
