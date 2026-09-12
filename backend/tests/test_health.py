from httpx import ASGITransport, AsyncClient

from app.api.v1.health import check_database_ready
from app.main import app


async def database_ready() -> bool:
    return True


async def database_unready() -> bool:
    return False


async def test_liveness_does_not_require_database() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "alive"
    assert body["service"] == "ResolveAI API"
    assert body["version"] == "0.10.0"
    assert body["checks"] is None
    assert body["timestamp"]
    assert response.headers["X-Request-ID"]


async def test_readiness_when_database_is_available() -> None:
    app.dependency_overrides[check_database_ready] = database_ready
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"] == {"database": {"status": "up"}}


async def test_readiness_when_database_is_unavailable() -> None:
    app.dependency_overrides[check_database_ready] = database_unready
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"] == {"database": {"status": "down"}}
