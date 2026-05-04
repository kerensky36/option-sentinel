import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.services.poll_scheduler import start_scheduler, stop_scheduler

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_scheduler()
    yield
    await stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(title="Option Sentinel", lifespan=lifespan)

    if os.path.isdir(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    from src.api.routes import admin, dashboard, partials, sse, thesis, positions, binary, screener
    app.include_router(admin.router)
    app.include_router(dashboard.router)
    app.include_router(partials.router)
    app.include_router(sse.router)
    app.include_router(thesis.router)
    app.include_router(positions.router)
    app.include_router(binary.router)
    app.include_router(screener.router)

    return app


app = create_app()
