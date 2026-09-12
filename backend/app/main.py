import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.config import Settings, get_settings
from app.db.session import engine
from app.errors import ServiceError
from app.logging import configure_logging
from app.security import FixedWindowRateLimiter

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def request_id_from_header(value: str | None) -> str:
    if value is not None and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid4())


def request_operation(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", "unmatched")
    return f"{request.method} {route_path}"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app(app_settings: Settings | None = None) -> FastAPI:
    effective_settings = app_settings or settings
    application = FastAPI(
        title=f"{effective_settings.app_name} API",
        version=effective_settings.app_version,
        description="ResolveAI support operations API",
        lifespan=lifespan,
    )
    application.state.settings = effective_settings
    application.state.rate_limiter = FixedWindowRateLimiter()
    if app_settings is not None:
        application.dependency_overrides[get_settings] = lambda: effective_settings
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=effective_settings.trusted_hosts
    )

    @application.exception_handler(ServiceError)
    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @application.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request_id_from_header(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "operation": request_operation(request),
                    "outcome": "unhandled_error",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "microphone=(), payment=(), usb=()"
        )
        if request.url.path in {"/docs", "/redoc"} or request.url.path.startswith("/docs/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
            )
        if request.url.path.startswith(
            ("/api/v1/auth", "/api/v1/analytics/", "/api/v1/admin/")
        ):
            response.headers["Cache-Control"] = "no-store"
        if (
            effective_settings.environment.lower() == "production"
            and effective_settings.session_cookie_secure
        ):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "operation": request_operation(request),
                "outcome": "success" if response.status_code < 400 else "error",
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    application.include_router(api_router)
    return application


app = create_app()
