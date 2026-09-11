import logging
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


class HealthCheck(BaseModel):
    status: Literal["up", "down"]


class HealthResponse(BaseModel):
    status: Literal["alive", "ready", "not_ready"]
    service: str
    version: str
    timestamp: datetime
    checks: dict[str, HealthCheck] | None = None


def health_response(
    status_value: Literal["alive", "ready", "not_ready"],
    *,
    database_ready: bool | None = None,
) -> HealthResponse:
    settings = get_settings()
    checks = None
    if database_ready is not None:
        checks = {
            "database": HealthCheck(status="up" if database_ready else "down"),
        }
    return HealthResponse(
        status=status_value,
        service=f"{settings.app_name} API",
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        checks=checks,
    )


async def check_database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Database readiness check failed", exc_info=True)
        return False
    return True


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return health_response("alive")


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
)
async def ready(
    response: Response,
    database_ready: Annotated[bool, Depends(check_database_ready)],
) -> HealthResponse:
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return health_response("not_ready", database_ready=False)
    return health_response("ready", database_ready=True)
