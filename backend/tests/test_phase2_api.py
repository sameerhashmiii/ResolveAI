from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AuthContext, get_current_auth
from app.db.session import get_db_session
from app.main import app
from app.models.domain import Session, Ticket, User
from app.models.enums import Role, TicketStatus
from app.services.auth import AuthService, CreatedSession


class FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        now = datetime.now(UTC)
        for value in self.added:
            if isinstance(value, Ticket):
                value.id = value.id or uuid4()
                value.number = value.number or 1000
                value.status = value.status or TicketStatus.NEW
                value.attachment_metadata = value.attachment_metadata or []
                value.created_at = value.created_at or now
                value.updated_at = value.updated_at or now

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _: object) -> None:
        pass

    async def rollback(self) -> None:
        pass


def make_auth(role: Role = Role.SUPPORT_ANALYST) -> AuthContext:
    user = User(
        id=uuid4(),
        name="API User",
        email="api.user@example.test",
        role=role,
        is_active=True,
        is_demo=True,
    )
    session = Session(
        id=uuid4(),
        user_id=user.id,
        token_hash="a" * 64,
        csrf_token="csrf-value",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=user,
    )
    return AuthContext(user=user, session=session)


async def test_authentication_and_csrf_are_required() -> None:
    fake_db = FakeDb()

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, fake_db)

    app.dependency_overrides[get_db_session] = db_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            unauthorized = await client.get("/api/v1/tickets")
    finally:
        app.dependency_overrides.clear()

    assert unauthorized.status_code == 401
    assert unauthorized.json() == {"detail": "Authentication required"}


async def test_ticket_create_requires_exact_csrf_and_writes_records() -> None:
    fake_db = FakeDb()
    auth = make_auth()

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, fake_db)

    async def auth_override() -> AuthContext:
        return auth

    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    payload = {
        "title": "Email unavailable",
        "description": "The requester cannot access email.",
        "requester_name": "Taylor Example",
        "requester_department": "Finance",
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            rejected = await client.post("/api/v1/tickets", json=payload)
            accepted = await client.post(
                "/api/v1/tickets", json=payload, headers={"X-CSRF-Token": "csrf-value"}
            )
    finally:
        app.dependency_overrides.clear()

    assert rejected.status_code == 403
    assert accepted.status_code == 201
    assert accepted.json()["status"] == "new"
    assert fake_db.commits == 1
    assert len(fake_db.added) == 3  # ticket, event, and audit log


async def test_empty_patch_is_rejected() -> None:
    fake_db = FakeDb()
    auth = make_auth()

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, fake_db)

    async def auth_override() -> AuthContext:
        return auth

    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    ticket_id = uuid4()
    headers = {"X-CSRF-Token": "csrf-value"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            empty_patch = await client.patch(
                f"/api/v1/tickets/{ticket_id}", json={}, headers=headers
            )
    finally:
        app.dependency_overrides.clear()

    assert empty_patch.status_code == 422


async def test_demo_auth_sets_http_only_cookie_and_returns_csrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = make_auth()

    async def fake_demo(_: AuthService) -> CreatedSession:
        return CreatedSession(user=auth.user, token="opaque-token", csrf_token="csrf-value")

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, FakeDb())

    monkeypatch.setattr(AuthService, "demo", fake_demo)
    app.dependency_overrides[get_db_session] = db_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/demo")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["csrf_token"] == "csrf-value"
    cookie = response.headers["set-cookie"]
    assert "resolveai_session=opaque-token" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
