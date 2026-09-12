from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AuthContext, get_current_auth
from app.db.session import get_db_session
from app.main import app
from app.models.domain import AuditLog, Session, User
from app.models.enums import Role
from app.repositories.analytics import AnalyticsRepository
from app.repositories.tickets import TicketRepository
from app.services.analytics import AnalyticsService
from app.services.tickets import TicketService


def auth_context(role: Role) -> AuthContext:
    user = User(
        id=uuid4(),
        name="Phase 11 user",
        email=f"phase11-{role.value}@example.test",
        role=role,
        is_active=True,
        is_demo=role == Role.SUPPORT_ANALYST,
    )
    session = Session(
        id=uuid4(),
        user_id=user.id,
        token_hash="d" * 64,
        csrf_token="phase11-csrf",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=user,
    )
    return AuthContext(user=user, session=session)


class EvaluationRepository:
    async def latest_completed_evaluation(self) -> Any:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=uuid4(),
            dataset_version="eval-v1",
            dataset_checksum="a" * 64,
            runner_version="runner-v1",
            workflow_version="workflow-v1",
            provider="local_demo",
            model=None,
            synthetic=True,
            sample_count=150,
            methodology={"scoring": "exact", "expected_outcomes": "hidden"},
            metrics={
                "classification": {"accuracy": 0.8, "provider_output": "hidden"},
                "ticket_text": "hidden",
            },
            started_at=now - timedelta(minutes=1),
            completed_at=now,
        )


async def test_evaluation_summary_is_authenticated_and_analyst_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AnalyticsService(cast(AsyncSession, object()))
    service.repository = cast(AnalyticsRepository, EvaluationRepository())

    async def analyst_auth() -> AuthContext:
        return auth_context(Role.SUPPORT_ANALYST)

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, object())

    original = AnalyticsService.ai_performance

    async def safe_summary(_: AnalyticsService) -> Any:
        return await original(service)

    monkeypatch.setattr(AnalyticsService, "ai_performance", safe_summary)
    app.dependency_overrides[get_current_auth] = analyst_auth
    app.dependency_overrides[get_db_session] = db_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/analytics/evaluation-summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    run = response.json()["latest_run"]
    assert run["sample_count"] == 150
    assert run["metrics"] == {"classification": {"accuracy": 0.8}}
    assert run["methodology"] == {"scoring": "exact"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unauthenticated = await client.get("/api/v1/analytics/evaluation-summary")
    assert unauthenticated.status_code == 401


class CapturingAuditDb:
    def __init__(self) -> None:
        self.statement: Any = None

    async def execute(self, statement: Any) -> Any:
        self.statement = statement
        return SimpleNamespace(all=lambda: [])


async def test_audit_repository_correlates_every_child_resource_to_ticket() -> None:
    db = CapturingAuditDb()
    ticket_id = uuid4()
    records = await TicketRepository(cast(AsyncSession, db)).audit(ticket_id)

    assert records == []
    compiled = db.statement.compile()
    sql = str(compiled)
    assert "audit_logs.resource_id =" in sql
    for table in (
        "ai_analyses",
        "investigations",
        "root_cause_assessments",
        "recommendations",
        "support_responses",
    ):
        assert f"FROM {table}" in sql
        assert f"{table}.ticket_id =" in sql
    assert sum(value == ticket_id for value in compiled.params.values()) == 6


class AuditRepository:
    def __init__(self, ticket_id: UUID, actor: User) -> None:
        self.ticket_id = ticket_id
        self.actor = actor

    async def get(self, ticket_id: UUID) -> object | None:
        return object() if ticket_id == self.ticket_id else None

    async def audit(self, ticket_id: UUID) -> list[tuple[AuditLog, User | None]]:
        assert ticket_id == self.ticket_id
        return [
            (
                AuditLog(
                    id=uuid4(),
                    actor_id=self.actor.id,
                    action="ticket.response.approved",
                    resource_type="ticket.support_response",
                    resource_id=uuid4(),
                    data={
                        "generated_by": "ai",
                        "decision": "approve",
                        "draft_body": "secret draft",
                        "final_body": "secret final",
                        "prompt": "secret prompt",
                        "token": "secret token",
                        "title": "secret title",
                        "description": "secret description",
                        "reason": "sensitive free text",
                    },
                    created_at=datetime.now(UTC),
                ),
                self.actor,
            )
        ]


async def test_ticket_audit_sanitizes_metadata_and_actor() -> None:
    ticket_id = uuid4()
    actor = auth_context(Role.MANAGER).user
    service = TicketService(cast(AsyncSession, object()))
    service.repository = cast(TicketRepository, AuditRepository(ticket_id, actor))

    records = await service.audit(ticket_id)

    assert len(records) == 1
    assert records[0].metadata == {"generated_by": "ai", "decision": "approve"}
    assert records[0].actor is not None
    assert records[0].actor.display_name == actor.name
    assert records[0].actor.role == Role.MANAGER
    rendered = records[0].model_dump_json()
    for secret in ("secret draft", "secret final", "secret prompt", "secret token"):
        assert secret not in rendered


async def test_manager_can_access_ticket_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    ticket_id = uuid4()
    queried: list[UUID] = []

    async def manager_auth() -> AuthContext:
        return auth_context(Role.MANAGER)

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, object())

    async def empty_audit(_: TicketService, requested_id: UUID) -> list[Any]:
        queried.append(requested_id)
        return []

    monkeypatch.setattr(TicketService, "audit", empty_audit)
    app.dependency_overrides[get_current_auth] = manager_auth
    app.dependency_overrides[get_db_session] = db_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/tickets/{ticket_id}/audit")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["Cache-Control"] == "no-store"
    assert queried == [ticket_id]


async def test_analyst_audit_denial_happens_before_database_query() -> None:
    database_requested = False

    async def analyst_auth() -> AuthContext:
        return auth_context(Role.SUPPORT_ANALYST)

    async def forbidden_db() -> AsyncIterator[AsyncSession]:
        nonlocal database_requested
        database_requested = True
        yield cast(AsyncSession, object())

    app.dependency_overrides[get_current_auth] = analyst_auth
    app.dependency_overrides[get_db_session] = forbidden_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/tickets/{uuid4()}/audit")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.headers["Cache-Control"] == "no-store"
    assert database_requested is False
