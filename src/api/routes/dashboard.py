"""Dashboard routes — stateless shell renders."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.api.main import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the dashboard shell.

    Position data is NOT included in the server response — the page loads empty
    and JS triggers a positions refresh (or loads from IndexedDB cache).
    Thesis assignments are applied client-side from localStorage.
    """
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "current_page": "thesis_monitor",
            "csp_nonce": getattr(request.state, "csp_nonce", ""),
        },
    )


@router.get("/health")
async def health():
    """Health check — no DB check, no auth required."""
    return JSONResponse({"status": "ok"})
