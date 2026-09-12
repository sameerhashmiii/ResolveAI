import re
import time
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.schemas.admin import AdminHealthResponse, ComponentHealth


class AdminService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def health(self) -> AdminHealthResponse:
        started = time.perf_counter()
        database_up = True
        try:
            await self.db.execute(text("SELECT 1"))
        except Exception:
            database_up = False
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        return AdminHealthResponse(
            status="healthy" if database_up else "degraded",
            service=f"{self._label(self.settings.app_name)} API",
            environment=self._label(self.settings.environment),
            version=self._label(self.settings.app_version),
            checked_at=datetime.now(UTC),
            components=[
                ComponentHealth(
                    name="database",
                    status="up" if database_up else "down",
                    latency_ms=duration_ms,
                )
            ],
        )

    @staticmethod
    def _label(value: str) -> str:
        if len(value) <= 64 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*", value):
            return value
        return "unknown"
