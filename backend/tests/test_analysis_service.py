import asyncio
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import InvalidProviderResponse, LocalDemoProvider
from app.ai.schemas import ProviderSignals, TicketAnalysisInput
from app.config import Settings
from app.errors import AIConfigurationError, ConflictError
from app.models.domain import AIAnalysis, AuditLog, Ticket, TicketEvent, User
from app.models.enums import AnalysisStatus, Role, TicketPriority, TicketStatus
from app.services.analyses import AnalysisService


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _: object) -> None:
        pass

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeAnalysisRepository:
    def __init__(self, analysis: AIAnalysis, ticket: Ticket) -> None:
        self.analysis = analysis
        self.ticket_value = ticket
        self.added: list[object] = []
        self.active: AIAnalysis | None = None

    def add(self, value: object) -> None:
        self.added.append(value)

    async def get(self, analysis_id: UUID) -> AIAnalysis | None:
        return self.analysis if analysis_id == self.analysis.id else None

    async def ticket(self, ticket_id: UUID) -> Ticket | None:
        return self.ticket_value if ticket_id == self.ticket_value.id else None

    async def active_for_ticket(self, _: UUID) -> AIAnalysis | None:
        return self.active


def objects(*, overridden: bool = False) -> tuple[User, Ticket, AIAnalysis]:
    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        name="Analyst",
        email="analyst@example.test",
        role=Role.SUPPORT_ANALYST,
        is_active=True,
        is_demo=False,
    )
    ticket = Ticket(
        id=uuid4(),
        number=1001,
        title="VPN connected but PayrollPro unavailable",
        description="I cannot access PayrollPro after VPN connects",
        requester_name="Requester",
        location="Dallas",
        device="Laptop",
        application="PayrollPro",
        category=None,
        priority=TicketPriority.P4 if overridden else None,
        priority_overridden=overridden,
        priority_override_reason="Approved business exception" if overridden else None,
        status=TicketStatus.NEW,
        created_by=user,
        created_at=now,
        updated_at=now,
    )
    analysis = AIAnalysis(
        id=uuid4(),
        ticket_id=ticket.id,
        requested_by_id=user.id,
        workflow_version="4.0",
        provider="local_demo",
        model=None,
        mode="local_demo",
        status=AnalysisStatus.QUEUED,
        requires_manual_review=False,
        created_at=now,
    )
    return user, ticket, analysis


def service_with_fakes(
    analysis: AIAnalysis, ticket: Ticket, *, timeout: float = 1
) -> tuple[AnalysisService, FakeDb, FakeAnalysisRepository]:
    db = FakeDb()
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        ai_timeout_seconds=timeout,
    )
    service = AnalysisService(cast(AsyncSession, db), settings)
    repository = FakeAnalysisRepository(analysis, ticket)
    service.repository = cast(Any, repository)
    return service, db, repository


async def test_execute_persists_result_ticket_event_and_audit() -> None:
    _, ticket, analysis = objects()
    service, db, repository = service_with_fakes(analysis, ticket)

    await service.execute(analysis.id, LocalDemoProvider())

    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.category == "vpn"
    assert analysis.validated_priority == TicketPriority.P2
    assert ticket.category == "vpn"
    assert ticket.priority == TicketPriority.P2
    assert db.commits == 2
    assert any(isinstance(value, TicketEvent) for value in repository.added)
    assert any(isinstance(value, AuditLog) for value in repository.added)


async def test_execute_respects_manual_priority_override() -> None:
    _, ticket, analysis = objects(overridden=True)
    service, _, _ = service_with_fakes(analysis, ticket)

    await service.execute(analysis.id, LocalDemoProvider())

    assert analysis.validated_priority == TicketPriority.P2
    assert ticket.priority == TicketPriority.P4
    assert ticket.category == "vpn"


class SlowProvider:
    name = "slow"
    model: str | None = None
    mode = "hosted"

    async def analyze(self, _: TicketAnalysisInput) -> ProviderSignals:
        await asyncio.sleep(0.05)
        raise AssertionError


class InvalidProvider:
    name = "invalid"
    model: str | None = None
    mode = "hosted"

    async def analyze(self, _: TicketAnalysisInput) -> ProviderSignals:
        raise InvalidProviderResponse


@pytest.mark.parametrize(
    ("provider", "timeout_seconds", "status", "error"),
    [
        (SlowProvider(), 0.001, AnalysisStatus.TIMED_OUT, "analysis_timeout"),
        (InvalidProvider(), 1, AnalysisStatus.FAILED, "invalid_provider_response"),
    ],
)
async def test_execute_persists_safe_failure_states(
    provider: SlowProvider | InvalidProvider,
    timeout_seconds: float,
    status: AnalysisStatus,
    error: str,
) -> None:
    _, ticket, analysis = objects()
    service, db, repository = service_with_fakes(analysis, ticket, timeout=timeout_seconds)

    await service.execute(analysis.id, provider)

    assert analysis.status == status
    assert analysis.error_code == error
    assert analysis.requires_manual_review is True
    assert db.rollbacks == 1
    events = [value for value in repository.added if isinstance(value, TicketEvent)]
    assert events[-1].data == {"error_code": error}


async def test_retry_rejects_active_and_completed_states() -> None:
    user, ticket, analysis = objects()
    service, _, repository = service_with_fakes(analysis, ticket)

    with pytest.raises(ConflictError):
        await service.retry(analysis.id, user)

    analysis.status = AnalysisStatus.FAILED
    repository.active = analysis
    with pytest.raises(ConflictError):
        await service.retry(analysis.id, user)

    repository.active = None
    retried = await service.retry(analysis.id, user)
    assert retried.status == AnalysisStatus.QUEUED
    assert retried.error_code is None


async def test_request_rejects_missing_hosted_configuration_safely() -> None:
    user, ticket, analysis = objects()
    db = FakeDb()
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        ai_mode="openai_compatible",
    )
    service = AnalysisService(cast(AsyncSession, db), settings)
    service.repository = cast(Any, FakeAnalysisRepository(analysis, ticket))

    with pytest.raises(AIConfigurationError):
        await service.request(ticket.id, user)

    assert db.commits == 0
