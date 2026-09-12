from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AuthContext, get_current_auth
from app.config import Settings
from app.db.session import get_db_session
from app.main import create_app
from app.models.domain import Session, User
from app.models.enums import Role
from app.security import FixedWindowRateLimiter
from app.services.auth import AuthService, CreatedSession


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class EmptyDb:
    pass


def settings(**changes: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql+asyncpg://unused:unused@localhost/test",
        "environment": "test",
        "session_cookie_secure": False,
    }
    values.update(changes)
    return Settings(**values)  # type: ignore[arg-type]


def auth_context() -> AuthContext:
    user = User(
        id=uuid4(),
        name="Phase 10 Analyst",
        email="phase10@example.test",
        role=Role.SUPPORT_ANALYST,
        is_active=True,
        is_demo=True,
    )
    session = Session(
        id=uuid4(),
        user_id=user.id,
        token_hash="c" * 64,
        csrf_token="phase10-csrf",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=user,
    )
    return AuthContext(user=user, session=session)


async def test_limiter_boundary_reset_and_key_isolation() -> None:
    clock = Clock()
    limiter = FixedWindowRateLimiter(clock=clock)

    assert await limiter.check("one", limit=2, window_seconds=10) is None
    assert await limiter.check("one", limit=2, window_seconds=10) is None
    assert await limiter.check("two", limit=2, window_seconds=10) is None
    assert await limiter.check("one", limit=2, window_seconds=10) == 10
    clock.now = 9.1
    assert await limiter.check("one", limit=2, window_seconds=10) == 1
    clock.now = 10
    assert await limiter.check("one", limit=2, window_seconds=10) is None


async def test_limiter_cleanup_is_bounded_and_capacity_is_bounded() -> None:
    clock = Clock()
    limiter = FixedWindowRateLimiter(clock=clock, max_keys=3, cleanup_batch=2)
    for key in ("one", "two", "three"):
        assert await limiter.check(key, limit=1, window_seconds=5) is None
    assert await limiter.check("four", limit=1, window_seconds=5) is None
    assert limiter.key_count == 3

    clock.now = 5
    assert await limiter.check("five", limit=1, window_seconds=5) is None
    assert limiter.key_count <= 2


async def test_auth_endpoint_limits_by_client_not_forwarded_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = create_app(settings(auth_rate_limit=1, auth_rate_window_seconds=30))
    user = auth_context().user

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def fake_demo(_: AuthService) -> CreatedSession:
        return CreatedSession(user=user, token="token", csrf_token="csrf")

    monkeypatch.setattr(AuthService, "demo", fake_demo)
    application.dependency_overrides[get_db_session] = db_override
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        first = await client.post(
            "/api/v1/auth/demo", headers={"X-Forwarded-For": "198.51.100.1"}
        )
        limited = await client.post(
            "/api/v1/auth/demo", headers={"X-Forwarded-For": "203.0.113.2"}
        )

    assert first.status_code == 200
    assert limited.status_code == 429
    assert limited.json() == {"detail": "Too many requests"}
    assert limited.headers["Retry-After"] == "30"
    assert limited.headers["Cache-Control"] == "no-store"
    assert limited.headers["X-Content-Type-Options"] == "nosniff"
    assert limited.headers["X-Request-ID"]


async def test_workflow_limit_runs_after_authentication_and_csrf() -> None:
    application = create_app(settings(workflow_rate_limit=1, workflow_rate_window_seconds=30))
    auth = auth_context()

    async def auth_override() -> AuthContext:
        return auth

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    application.dependency_overrides[get_current_auth] = auth_override
    application.dependency_overrides[get_db_session] = db_override
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        invalid_csrf = await client.post(f"/api/v1/tickets/{uuid4()}/analyses")
        first_valid = await client.post(
            f"/api/v1/tickets/{uuid4()}/analyses", headers={"X-CSRF-Token": "phase10-csrf"}
        )
        limited = await client.post(
            f"/api/v1/tickets/{uuid4()}/analyses", headers={"X-CSRF-Token": "phase10-csrf"}
        )

    assert invalid_csrf.status_code == 403
    # The first valid request reaches the fake database, proving invalid CSRF did not consume quota.
    assert first_valid.status_code == 500
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "30"


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/api/v1/health/live", 200),
        ("/missing", 404),
        (f"/api/v1/tickets/{uuid4()}/analyses", 401),
    ],
)
async def test_security_headers_cover_success_and_http_errors(
    path: str, expected_status: int
) -> None:
    application = create_app(settings())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get(path) if expected_status != 401 else await client.post(path)

    assert response.status_code == expected_status
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"]
    assert response.headers["Content-Security-Policy"]
    assert response.headers["X-Request-ID"]


async def test_safe_500_has_request_id_headers_and_no_exception_detail() -> None:
    application = create_app(settings())

    @application.get("/failure")
    async def failure() -> None:
        raise RuntimeError("postgresql://user:secret@private-host/internal")

    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/failure", headers={"X-Request-ID": "phase10-request"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["X-Request-ID"] == "phase10-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "secret" not in response.text
    assert "private-host" not in response.text


async def test_hsts_condition_and_trusted_host_rejection() -> None:
    secure_app = create_app(settings(environment="production", session_cookie_secure=True))
    insecure_app = create_app(settings(environment="production", session_cookie_secure=False))

    async with AsyncClient(
        transport=ASGITransport(app=secure_app), base_url="https://test"
    ) as client:
        secure = await client.get("/api/v1/health/live")
        rejected = await client.get(
            "/api/v1/health/live", headers={"Host": "attacker.example"}
        )
    async with AsyncClient(
        transport=ASGITransport(app=insecure_app), base_url="http://test"
    ) as client:
        insecure = await client.get("/api/v1/health/live")

    assert secure.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "Strict-Transport-Security" not in insecure.headers
    assert rejected.status_code == 400
    assert rejected.headers["X-Content-Type-Options"] == "nosniff"
    assert rejected.headers["X-Request-ID"]


async def test_auth_database_failure_is_safely_sanitized() -> None:
    application = create_app(settings())

    async def failing_db() -> AsyncIterator[AsyncSession]:
        raise RuntimeError("postgresql://user:secret@private-host/internal")
        yield cast(AsyncSession, EmptyDb())

    application.dependency_overrides[get_db_session] = failing_db
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/auth/demo")

    assert response.status_code == 500
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "secret" not in response.text
    assert "private-host" not in response.text
