import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


def create_app() -> FastAPI:
    app = FastAPI(title="Option Sentinel")

    if os.path.isdir(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    from src.api.routes import auth, dashboard, partials, positions, screener
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(partials.router)
    app.include_router(positions.router)
    app.include_router(screener.router)

    return app


app = create_app()
