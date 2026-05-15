import hashlib
import hmac
import logging
import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

_security_log = logging.getLogger("security")
_log_pepper = os.getenv("LOG_PEPPER", "sentinel-pepper")

limiter = Limiter(key_func=get_remote_address)


def _hash_ip(ip: str) -> str:
    return hmac.new(_log_pepper.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]


def log_security_event(event: str, request: Request) -> None:
    ip = getattr(request.client, "host", "unknown") if request.client else "unknown"
    _security_log.warning(
        "SECURITY %s path=%s ip=%s",
        event,
        request.url.path,
        _hash_ip(ip),
    )


_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.tailwindcss.com 'nonce-{nonce}'; "
    "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


class CSPNonceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = _CSP.format(nonce=nonce)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if os.getenv("HTTPS_ONLY", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response


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


async def _generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    _security_log.error(
        "SECURITY unhandled_exception path=%s type=%s",
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


def create_app() -> FastAPI:
    missing = [v for v in _REQUIRED_ENV if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Option Sentinel: missing required environment variables: {', '.join(missing)}"
        )

    app = FastAPI(title="Option Sentinel")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    allowed_origin = os.getenv("ALLOWED_ORIGIN", "http://localhost:8000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[allowed_origin],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=False,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSPNonceMiddleware)
    app.add_middleware(NoCacheJSMiddleware)

    if os.path.isdir(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    from src.auth import router as auth_module
    from src.api.routes import accounts, dashboard, partials, positions, screener
    app.include_router(auth_module.router)
    app.include_router(accounts.router)
    app.include_router(dashboard.router)
    app.include_router(partials.router)
    app.include_router(positions.router)
    app.include_router(screener.router)

    if os.getenv("DEBUG", "true").lower() != "true":
        app.add_exception_handler(Exception, _generic_error_handler)

    return app


app = create_app()
