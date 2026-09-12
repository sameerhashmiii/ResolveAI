import json
import logging
from typing import cast

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.logging import JsonFormatter
from app.main import app
from app.services.admin import AdminService


async def test_request_id_accepts_only_bounded_safe_values() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        accepted = await client.get(
            "/api/v1/health/live", headers={"X-Request-ID": "safe.request-9:abc"}
        )
        unsafe = await client.get(
            "/api/v1/health/live", headers={"X-Request-ID": "unsafe request id"}
        )
        oversized = await client.get(
            "/api/v1/health/live", headers={"X-Request-ID": "a" * 129}
        )
    assert accepted.headers["X-Request-ID"] == "safe.request-9:abc"
    assert unsafe.headers["X-Request-ID"] != "unsafe request id"
    assert oversized.headers["X-Request-ID"] != "a" * 129
    assert len(unsafe.headers["X-Request-ID"]) == 36


def test_json_formatter_emits_bounded_structured_fields_without_exception_text() -> None:
    record = logging.makeLogRecord(
        {
            "name": "phase9",
            "levelno": logging.ERROR,
            "levelname": "ERROR",
            "msg": "failed",
            "request_id": "request-9",
            "operation": "GET /api/v1/analytics/overview",
            "outcome": "unhandled_error",
            "status_code": 500,
            "duration_ms": 12.5,
            "provider_output": "must-not-appear",
        }
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "request-9"
    assert payload["operation"] == "GET /api/v1/analytics/overview"
    assert payload["outcome"] == "unhandled_error"
    assert payload["status_code"] == 500
    assert payload["duration_ms"] == 12.5
    assert "provider_output" not in payload
    assert "exception" not in payload


class FailingDb:
    async def execute(self, _: object) -> None:
        raise RuntimeError("postgresql://user:secret@private-host/internal SQL")


async def test_admin_health_is_timed_and_sanitized() -> None:
    settings = Settings(database_url="postgresql+asyncpg://unused:unused@localhost/test")
    service = AdminService(cast(AsyncSession, FailingDb()), settings)
    response = await service.health()
    dumped = response.model_dump_json()
    assert response.status == "degraded"
    assert response.components[0].name == "database"
    assert response.components[0].status == "down"
    assert response.components[0].latency_ms >= 0
    assert "secret" not in dumped
    assert "private-host" not in dumped
    assert "SELECT" not in dumped
