import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


class NoCacheJSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/js/"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


_REQUIRED_ENV = [
    "SCHWAB_CLIENT_ID",
    "SCHWAB_CLIENT_SECRET",
    "SCHWAB_REDIRECT_URI",
    "SCHWAB_AUTH_URL",
    "SCHWAB_TOKEN_URL",
]


def create_app() -> FastAPI:
    missing = [v for v in _REQUIRED_ENV if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Option Sentinel: missing required environment variables: {', '.join(missing)}"
        )

    app = FastAPI(title="Option Sentinel")
    app.add_middleware(NoCacheJSMiddleware)

    if os.path.isdir(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    from src.auth import router as auth_module
    from src.api.routes import dashboard, partials, positions, screener
    app.include_router(auth_module.router)
    app.include_router(dashboard.router)
    app.include_router(partials.router)
    app.include_router(positions.router)
    app.include_router(screener.router)

    return app


app = create_app()
