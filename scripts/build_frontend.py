#!/usr/bin/env python3
"""Pre-render Jinja2 templates to static HTML and copy static assets to dist/."""
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def build() -> None:
    root = Path(__file__).parent.parent
    templates_dir = root / "frontend" / "templates"
    static_src = root / "frontend" / "static"
    dist = root / "dist"

    # Clean and recreate dist/
    shutil.rmtree(dist, ignore_errors=True)
    dist.mkdir()

    # Copy static assets verbatim
    shutil.copytree(static_src, dist / "static")
    print("✓ dist/static/")

    # Jinja2 env — loader must be rooted at the templates dir so
    # {% extends "base.html" %} resolves correctly
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)

    # dashboard.html → dist/index.html
    html = env.get_template("dashboard.html").render(current_page="thesis_monitor")
    (dist / "index.html").write_text(html, encoding="utf-8")
    print("✓ dist/index.html")

    # screener.html → dist/screener/index.html  (clean URL: /screener)
    (dist / "screener").mkdir()
    html = env.get_template("screener.html").render(
        current_page="covered_call_screener",
        setup_required=False,
    )
    (dist / "screener" / "index.html").write_text(html, encoding="utf-8")
    print("✓ dist/screener/index.html")


if __name__ == "__main__":
    build()
