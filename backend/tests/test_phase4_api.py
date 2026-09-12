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
from app.models.domain import AIAnalysis, Session, Ticket, User
from app.models.enums import AnalysisStatus, Role, TicketPriority, TicketStatus
from app.services.analyses import AnalysisService
from app.services.tickets import TicketService


class EmptyDb:
    pass


def auth_context() -> AuthContext:
    user = User(
        id=uuid4(),
        name="API Analyst",
        email="phase4@example.test",
        role=Role.SUPPORT_ANALYST,
        is_active=True,
        is_demo=True,
    )
    session = Session(
        id=uuid4(),
        user_id=user.id,
        token_hash="b" * 64,
        csrf_token="csrf-phase4",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=user,
    )
    return AuthContext(user=user, session=session)


def analysis(auth: AuthContext, ticket_id: UUID) -> AIAnalysis:
    return AIAnalysis(
        id=uuid4(),
        ticket_id=ticket_id,
        requested_by_id=auth.user.id,
        workflow_version="4.0",
        provider="local_demo",
        model=None,
        mode="local_demo",
        status=AnalysisStatus.QUEUED,
        requires_manual_review=False,
        created_at=datetime.now(UTC),
    )


def response_ticket(auth: AuthContext, ticket_id: UUID) -> Ticket:
    now = datetime.now(UTC)
    return Ticket(
        id=ticket_id,
        number=1005,
        title="Issue",
        description="Issue details",
        requester_name="Requester",
        attachment_metadata=[],
        category=None,
        priority=TicketPriority.P2,
        priority_overridden=True,
        priority_override_reason="Validated business impact",
        status=TicketStatus.NEW,
        assigned_to=None,
        created_by=auth.user,
        created_at=now,
        updated_at=now,
    )


async def test_analysis_request_requires_authentication() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/tickets/{uuid4()}/analyses")
    assert response.status_code == 401


async def test_analysis_request_requires_csrf_then_returns_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = auth_context()
    ticket_id = uuid4()
    queued = analysis(auth, ticket_id)
    jobs: list[UUID] = []

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_request(_: AnalysisService, requested_id: UUID, actor: User) -> AIAnalysis:
        assert requested_id == ticket_id
        assert actor is auth.user
        return queued

    async def fake_job(analysis_id: UUID) -> None:
        jobs.append(analysis_id)

    monkeypatch.setattr(AnalysisService, "request", fake_request)
    monkeypatch.setattr(ticket_routes, "run_analysis_job", fake_job)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            rejected = await client.post(f"/api/v1/tickets/{ticket_id}/analyses")
            accepted = await client.post(
                f"/api/v1/tickets/{ticket_id}/analyses",
                headers={"X-CSRF-Token": "csrf-phase4"},
            )
    finally:
        app.dependency_overrides.clear()

    assert rejected.status_code == 403
    assert accepted.status_code == 202
    assert accepted.json() == {"analysis_id": str(queued.id), "status": "queued"}
    assert jobs == [queued.id]


async def test_latest_returns_json_null(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = auth_context()

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_latest(_: AnalysisService, __: UUID) -> AIAnalysis | None:
        return None

    monkeypatch.setattr(AnalysisService, "latest", fake_latest)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/tickets/{uuid4()}/analyses/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() is None


async def test_priority_override_returns_extended_ticket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = auth_context()
    ticket_id = uuid4()
    ticket = response_ticket(auth, ticket_id)

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_override(
        _: TicketService,
        requested_id: UUID,
        priority: TicketPriority,
        reason: str,
        actor: User,
    ) -> Ticket:
        assert (requested_id, priority, reason, actor) == (
            ticket_id,
            TicketPriority.P2,
            "Validated business impact",
            auth.user,
        )
        return ticket

    monkeypatch.setattr(TicketService, "override_priority", fake_override)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/tickets/{ticket_id}/priority-override",
                json={"priority": "p2", "reason": "Validated business impact"},
                headers={"X-CSRF-Token": "csrf-phase4"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["priority_overridden"] is True
    assert response.json()["priority_override_reason"] == "Validated business impact"
