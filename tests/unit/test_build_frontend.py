"""Tests for the static Firebase Hosting build (specs/017 T024)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_frontend.py"


def _build(out: Path) -> None:
    spec = importlib.util.spec_from_file_location("build_frontend", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.build(out_dir=out)


def test_builds_existing_pages(tmp_path):
    _build(tmp_path)
    assert (tmp_path / "index.html").is_file()
    assert (tmp_path / "screener" / "index.html").is_file()
    assert (tmp_path / "static").is_dir()


def test_prerenders_data_use_page(tmp_path):
    """Firebase rewrites unknown paths to index.html, so /data-use must be pre-rendered."""
    _build(tmp_path)
    page = tmp_path / "data-use" / "index.html"
    assert page.is_file()
    html = page.read_text(encoding="utf-8")
    assert "How we use your data" in html
    assert "No user-identifiable or pedigree data" in html
