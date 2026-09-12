from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AuthContext, get_current_auth
from app.db.session import get_db_session
from app.main import app
from app.models.domain import Session, User
from app.models.enums import Role
from app.repositories.analytics import AnalyticsRepository, TicketAggregate, WorkflowAggregate
from app.services.analytics import AnalyticsService


def auth_context(role: Role) -> AuthContext:
    user = User(
        id=uuid4(),
        name="Phase 9 user",
        email="phase9@example.test",
        role=role,
        is_active=True,
        is_demo=True,
    )
    session = Session(
        id=uuid4(),
        user_id=user.id,
        token_hash="a" * 64,
        csrf_token="phase9-csrf",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=user,
    )
    return AuthContext(user=user, session=session)


class FakeAnalyticsRepository:
    async def ticket_counts(self) -> TicketAggregate:
        now = datetime.now(UTC)
        return TicketAggregate(10, 3, 6, 1, now - timedelta(days=2), now)

    async def analysis_workflow(self) -> WorkflowAggregate:
        return WorkflowAggregate(10, 7, 2, 120.0, None, None, ["triage-v1"])

    async def investigation_workflow(self) -> WorkflowAggregate:
        return WorkflowAggregate(4, 3, 1, 250.0, None, None, ["investigation-v1"])

    async def assessment_workflow(self) -> WorkflowAggregate:
        return WorkflowAggregate(2, 1, 1, 300.0, None, None, ["assessment-v1"])

    async def active_dataset_version(self) -> str:
        return "demo-v9"

    async def latest_completed_evaluation(self) -> Any:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=uuid4(),
            status="completed",
            dataset_version="eval-v1",
            dataset_checksum="a" * 64,
            runner_version="runner-v1",
            workflow_version="workflow-v1",
            provider="local_demo",
            model=None,
            synthetic=True,
            sample_count=100,
            methodology={"scoring_method": "exact match", "case_records": ["hidden"]},
            metrics={"classification": {"accuracy": 0.8}, "raw_cases": ["hidden"]},
            started_at=now - timedelta(minutes=1),
            completed_at=now,
        )


def service_with_fake() -> AnalyticsService:
    service = AnalyticsService(cast(AsyncSession, object()))
    service.repository = cast(AnalyticsRepository, FakeAnalyticsRepository())
    return service


async def test_overview_aggregates_are_labeled_with_provenance() -> None:
    overview = await service_with_fake().overview()
    assert overview.tickets.resolution_rate == 0.6
    assert overview.tickets.provenance.sample_count == 10
    assert overview.tickets.provenance.synthetic is True
    assert overview.dataset_version == "demo-v9"
    assert overview.workflows[0].completion_rate == 0.7
    assert overview.workflows[0].failure_rate == 0.2
    assert overview.workflows[0].provenance.workflow_versions == ["triage-v1"]


async def test_ai_performance_exposes_only_safe_stored_aggregates() -> None:
    response = await service_with_fake().ai_performance()
    assert response.latest_run is not None
    assert response.latest_run.metrics == {"classification": {"accuracy": 0.8}}
    assert "case_records" not in response.latest_run.methodology
    assert response.latest_run.provenance.sample_count == 100
    assert response.latest_run.provenance.dataset_checksum == "a" * 64


class CapturingDb:
    def __init__(self) -> None:
        self.statement: object | None = None

    async def scalar(self, statement: object) -> None:
        self.statement = statement


async def test_evaluation_repository_selects_completed_runs_only() -> None:
    db = CapturingDb()
    repository = AnalyticsRepository(cast(AsyncSession, db))
    assert await repository.latest_completed_evaluation() is None
    assert db.statement is not None
    sql = str(db.statement)
    assert "evaluation_runs.status" in sql
    assert "completed" in str(cast(Any, db.statement).compile().params)
    assert "completed_at DESC" in sql


async def test_manager_denial_happens_before_analytics_database_dependency() -> None:
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
            response = await client.get("/api/v1/analytics/ai-performance")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.headers["Cache-Control"] == "no-store"
    assert database_requested is False


async def test_analytics_endpoints_require_authentication() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overview = await client.get("/api/v1/analytics/overview")
        performance = await client.get("/api/v1/analytics/ai-performance")
        admin = await client.get("/api/v1/admin/health")
    assert [overview.status_code, performance.status_code, admin.status_code] == [401, 401, 401]


async def test_admin_health_rejects_manager_before_health_database_work() -> None:
    database_requested = False

    async def manager_auth() -> AuthContext:
        return auth_context(Role.MANAGER)

    async def forbidden_db() -> AsyncIterator[AsyncSession]:
        nonlocal database_requested
        database_requested = True
        yield cast(AsyncSession, object())

    app.dependency_overrides[get_current_auth] = manager_auth
    app.dependency_overrides[get_db_session] = forbidden_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/admin/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert database_requested is False
