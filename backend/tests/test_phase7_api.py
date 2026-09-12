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
from app.models.assessments import RootCauseAssessment
from app.models.domain import Session, User
from app.models.enums import Role, RootCauseStatus
from app.services.assessments import AssessmentService


class EmptyDb:
    pass


def auth_context() -> AuthContext:
    user = User(
        id=uuid4(),
        name="Investigator",
        email="phase7@example.test",
        role=Role.SUPPORT_ANALYST,
        is_active=True,
        is_demo=True,
    )
    session = Session(
        id=uuid4(),
        user_id=user.id,
        token_hash="a" * 64,
        csrf_token="csrf-phase7",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=user,
    )
    return AuthContext(user=user, session=session)


def queued(ticket_id: UUID, user_id: UUID) -> RootCauseAssessment:
    return RootCauseAssessment(
        id=uuid4(),
        ticket_id=ticket_id,
        investigation_id=uuid4(),
        requested_by_id=user_id,
        workflow_version="7.0",
        provider="local_grounded_demo",
        mode="local_demo",
        status=RootCauseStatus.QUEUED,
        confidence_version="confidence-v1",
        requires_escalation=True,
        limitations=[],
        confidence_factors=[],
        created_at=datetime.now(UTC),
    )


async def test_phase7_endpoints_require_authentication() -> None:
    ticket_id = uuid4()
    assessment_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        requested = await client.post(f"/api/v1/tickets/{ticket_id}/assessments")
        latest = await client.get(f"/api/v1/tickets/{ticket_id}/assessments/latest")
        explanation = await client.get(f"/api/v1/assessments/{assessment_id}/explanation")
    assert requested.status_code == 401
    assert latest.status_code == 401
    assert explanation.status_code == 401


async def test_assessment_requires_csrf_and_returns_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = auth_context()
    ticket_id = uuid4()
    value = queued(ticket_id, auth.user.id)
    jobs: list[UUID] = []

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_request(
        _: AssessmentService, requested_id: UUID, actor: User
    ) -> RootCauseAssessment:
        assert requested_id == ticket_id
        assert actor is auth.user
        return value

    async def fake_job(assessment_id: UUID) -> None:
        jobs.append(assessment_id)

    monkeypatch.setattr(AssessmentService, "request", fake_request)
    monkeypatch.setattr(ticket_routes, "run_assessment_job", fake_job)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            rejected = await client.post(f"/api/v1/tickets/{ticket_id}/assessments")
            accepted = await client.post(
                f"/api/v1/tickets/{ticket_id}/assessments",
                headers={"X-CSRF-Token": "csrf-phase7"},
            )
    finally:
        app.dependency_overrides.clear()
    assert rejected.status_code == 403
    assert accepted.status_code == 202
    assert accepted.json() == {"assessment_id": str(value.id), "status": "queued"}
    assert jobs == [value.id]


async def test_latest_assessment_returns_json_null(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = auth_context()

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_latest(_: AssessmentService, __: UUID) -> RootCauseAssessment | None:
        return None

    monkeypatch.setattr(AssessmentService, "latest", fake_latest)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/tickets/{uuid4()}/assessments/latest")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() is None
