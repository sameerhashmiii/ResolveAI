from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AuthContext, get_current_auth
from app.api.v1 import tickets as ticket_routes
from app.db.session import get_db_session
from app.main import app
from app.models.domain import Session, User
from app.models.enums import InvestigationStatus, Role
from app.models.operational import Investigation
from app.services.investigations import InvestigationService


class EmptyDb:
    pass


def auth_context() -> AuthContext:
    user = User(
        id=uuid4(),
        name="Investigator",
        email="investigator@example.test",
        role=Role.SUPPORT_ANALYST,
        is_active=True,
        is_demo=True,
    )
    session = Session(
        id=uuid4(),
        user_id=user.id,
        token_hash="f" * 64,
        csrf_token="csrf-phase6",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=user,
    )
    return AuthContext(user=user, session=session)


async def test_phase6_endpoints_require_authentication() -> None:
    ticket_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        similar = await client.get(f"/api/v1/tickets/{ticket_id}/similar")
        investigation = await client.post(f"/api/v1/tickets/{ticket_id}/investigations")
    assert similar.status_code == 401
    assert investigation.status_code == 401


async def test_investigation_requires_csrf_and_returns_queued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = auth_context()
    ticket_id = uuid4()
    queued = Investigation(
        id=uuid4(),
        ticket_id=ticket_id,
        requested_by_id=auth.user.id,
        workflow_version="6.0",
        status=InvestigationStatus.QUEUED,
        reference_time=datetime.now(UTC),
        reference_basis="ticket_created_at",
        planned_tools=[],
        created_at=datetime.now(UTC),
    )
    jobs: list[UUID] = []

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_request(
        _: InvestigationService, requested_id: UUID, actor: User
    ) -> Investigation:
        assert requested_id == ticket_id
        assert actor is auth.user
        return queued

    async def fake_job(investigation_id: UUID) -> None:
        jobs.append(investigation_id)

    monkeypatch.setattr(InvestigationService, "request", fake_request)
    monkeypatch.setattr(ticket_routes, "run_investigation_job", fake_job)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            rejected = await client.post(f"/api/v1/tickets/{ticket_id}/investigations")
            accepted = await client.post(
                f"/api/v1/tickets/{ticket_id}/investigations",
                headers={"X-CSRF-Token": "csrf-phase6"},
            )
    finally:
        app.dependency_overrides.clear()
    assert rejected.status_code == 403
    assert accepted.status_code == 202
    assert accepted.json() == {
        "investigation_id": str(queued.id),
        "status": "queued",
    }
    assert jobs == [queued.id]


async def test_latest_investigation_returns_json_null(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = auth_context()

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_latest(_: InvestigationService, __: UUID) -> Investigation | None:
        return None

    monkeypatch.setattr(InvestigationService, "latest", fake_latest)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/tickets/{uuid4()}/investigations/latest"
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() is None
