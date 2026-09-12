from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import InvalidProviderResponse, ProviderUnavailable
from app.api.dependencies import AuthContext, get_current_auth
from app.db.session import get_db_session
from app.errors import ConflictError, ForbiddenError, UnsafeResponseContentError
from app.main import app
from app.models.assessments import RootCauseAssessment
from app.models.domain import AuditLog, Session, Ticket, TicketEvent, User
from app.models.enums import (
    InvestigationStatus,
    RecommendationActionType,
    RecommendationStatus,
    ResponseGeneratedBy,
    Role,
    RootCauseStatus,
    SupportResponseStatus,
    TicketStatus,
)
from app.models.operational import Investigation
from app.models.recommendations import Recommendation, SupportResponse
from app.recommendations.policy import classify_action, recommendation_from_assessment
from app.response_generation.providers import (
    LocalResponseProvider,
    OpenAICompatibleResponseProvider,
)
from app.response_generation.schemas import GeneratedResponse, ResponseGenerationInput
from app.root_cause.schemas import EvidenceSnapshot, GroundedInference
from app.schemas.recommendations import RecommendationDecision
from app.schemas.responses import ResponseEdit, SupportResponseView
from app.schemas.tickets import TicketUpdate
from app.services.assessments import AssessmentService
from app.services.outcomes import OutcomeService
from app.services.recommendations import RecommendationService
from app.services.responses import ResponseService


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


class FakeResolutionRepository:
    def __init__(
        self, ticket: Ticket, assessment: RootCauseAssessment, recommendation: Recommendation
    ) -> None:
        self.ticket_value = ticket
        self.assessment = assessment
        self.recommendation_value = recommendation
        self.response_value: SupportResponse | None = None
        self.records: list[object] = []

    def add(self, value: object) -> None:
        self.records.append(value)
        if isinstance(value, SupportResponse):
            now = datetime.now(UTC)
            value.created_at = now
            value.updated_at = now
            self.response_value = value

    async def ticket(self, ticket_id: UUID, *, lock: bool = False) -> Ticket | None:
        del lock
        return self.ticket_value if ticket_id == self.ticket_value.id else None

    async def recommendation(
        self, recommendation_id: UUID, *, lock: bool = False
    ) -> Recommendation | None:
        del lock
        if recommendation_id == self.recommendation_value.id:
            return self.recommendation_value
        return None

    async def latest_recommendation(
        self, ticket_id: UUID, *, lock: bool = False
    ) -> Recommendation | None:
        del lock
        return self.recommendation_value if ticket_id == self.ticket_value.id else None

    async def latest_completed_assessment(self, ticket_id: UUID) -> RootCauseAssessment | None:
        return self.assessment if ticket_id == self.ticket_value.id else None

    async def response(self, response_id: UUID, *, lock: bool = False) -> SupportResponse | None:
        del lock
        if self.response_value is not None and response_id == self.response_value.id:
            return self.response_value
        return None

    async def latest_response(self, ticket_id: UUID) -> SupportResponse | None:
        return self.response_value if ticket_id == self.ticket_value.id else None


class FakeAssessmentRepository:
    def __init__(self, db: FakeDb, ticket: Ticket, assessment: RootCauseAssessment) -> None:
        self.db = db
        self.ticket_value = ticket
        self.assessment = assessment
        self.records: list[object] = []
        self.get_rollback_counts: list[int] = []

    def add(self, value: object) -> None:
        self.records.append(value)

    async def get(self, assessment_id: UUID) -> RootCauseAssessment | None:
        self.get_rollback_counts.append(self.db.rollbacks)
        return self.assessment if assessment_id == self.assessment.id else None

    async def ticket(self, ticket_id: UUID) -> Ticket | None:
        return self.ticket_value if ticket_id == self.ticket_value.id else None

    async def analysis(self, _: UUID | None) -> None:
        return None


def user(role: Role = Role.SUPPORT_ANALYST) -> User:
    return User(
        id=uuid4(),
        name="Alex Analyst",
        email=f"{uuid4()}@example.test",
        role=role,
        is_active=True,
        is_demo=True,
    )


def workflow() -> tuple[Ticket, RootCauseAssessment, Recommendation]:
    now = datetime.now(UTC)
    actor = user()
    ticket = Ticket(
        id=uuid4(),
        number=1800,
        title="VPN connected but PayrollPro is unavailable",
        description="VPN connects successfully, but the internal application does not load.",
        requester_name="Taylor Example",
        status=TicketStatus.NEW,
        created_by=actor,
        created_at=now,
        updated_at=now,
    )
    assessment = RootCauseAssessment(
        id=uuid4(),
        ticket_id=ticket.id,
        investigation_id=uuid4(),
        requested_by_id=actor.id,
        workflow_version="7.0",
        provider="local_grounded_demo",
        mode="local_demo",
        status=RootCauseStatus.COMPLETED,
        probable_root_cause="Dallas internal DNS service degradation",
        confidence_version="confidence-v1",
        recommendation="Reconnect the VPN, verify access, and escalate if the issue persists.",
        requires_escalation=False,
        limitations=["The cause is probable rather than confirmed"],
        confidence_factors=[],
        completed_at=now,
        created_at=now,
    )
    recommendation = recommendation_from_assessment(assessment)
    recommendation.created_at = now
    recommendation.updated_at = now
    return ticket, assessment, recommendation


def generation_input() -> ResponseGenerationInput:
    ticket, assessment, recommendation = workflow()
    return ResponseGenerationInput(
        ticket_id=ticket.id,
        requester_name=ticket.requester_name,
        title=ticket.title,
        description=ticket.description,
        probable_root_cause=assessment.probable_root_cause or "unknown",
        recommendation=recommendation.instructions,
        limitations=assessment.limitations,
        requires_escalation=False,
    )


async def test_assessment_completion_proposes_one_recommendation(monkeypatch: Any) -> None:
    ticket, assessment, _ = workflow()
    investigation = Investigation(
        id=assessment.investigation_id,
        ticket_id=ticket.id,
        requested_by_id=assessment.requested_by_id,
        workflow_version="6.0",
        status=InvestigationStatus.COMPLETED,
        reference_time=datetime.now(UTC),
        reference_basis="ticket_created_at",
        planned_tools=[],
        steps=[],
    )
    assessment.investigation = investigation
    assessment.status = RootCauseStatus.QUEUED
    evidence = EvidenceSnapshot(
        evidence_type="incident",
        source_id="incident:1",
        title="Dallas DNS degradation",
        excerpt="DNS degradation observed",
        supports="Correlated service incident",
        metadata={"service": "DNS"},
    )
    inference = GroundedInference(
        probable_root_cause="Dallas DNS service degradation",
        inference_key="dns_service_degradation",
        recommended_action="Verify DNS and escalate if the issue persists",
        selected_source_ids=[evidence.source_id],
        limitations=[],
    )

    class Provider:
        async def infer(self, _: object) -> GroundedInference:
            return inference

    monkeypatch.setattr("app.services.assessments.collect_evidence", lambda *_: ([evidence], []))
    db = FakeDb()
    repository = FakeAssessmentRepository(db, ticket, assessment)
    service = AssessmentService(cast(AsyncSession, db))
    service.repository = cast(Any, repository)

    await service.execute(assessment.id, cast(Any, Provider()))

    recommendations = [item for item in repository.records if isinstance(item, Recommendation)]
    assert len(recommendations) == 1
    assert assessment.status == RootCauseStatus.COMPLETED
    assert db.commits == 2


async def test_assessment_failure_reloads_by_id_after_rollback() -> None:
    ticket, assessment, _ = workflow()
    assessment.status = RootCauseStatus.RUNNING
    db = FakeDb()
    repository = FakeAssessmentRepository(db, ticket, assessment)
    service = AssessmentService(cast(AsyncSession, db))
    service.repository = cast(Any, repository)

    await service._fail(assessment.id, RootCauseStatus.FAILED, "root_cause_failed")

    assert db.rollbacks == 1
    assert db.commits == 1
    assert repository.get_rollback_counts == [1]
    assert assessment.status == RootCauseStatus.FAILED
    assert assessment.error_code == "root_cause_failed"


def test_recommendation_policy_prioritizes_escalation_and_high_impact() -> None:
    assert (
        classify_action("Perform an MFA reset", requires_escalation=False)
        == RecommendationActionType.HIGH_IMPACT
    )
    assert (
        classify_action("Perform an account reset", requires_escalation=True)
        == RecommendationActionType.HIGH_IMPACT
    )
    _, assessment, recommendation = workflow()
    assert recommendation.assessment_id == assessment.id
    assert recommendation.requires_approval is True
    assert recommendation.status == RecommendationStatus.PROPOSED


def test_strict_decision_and_terminal_patch_contracts() -> None:
    with pytest.raises(ValidationError):
        RecommendationDecision(decision="modify", reason="valid reason")
    with pytest.raises(ValidationError):
        RecommendationDecision(
            decision="approve",
            reason="valid reason",
            modified_instructions="not permitted here",
        )
    with pytest.raises(ValidationError):
        TicketUpdate(status=TicketStatus.RESOLVED)
    assert TicketUpdate(status=TicketStatus.IN_PROGRESS).status == TicketStatus.IN_PROGRESS
    assert "sent_at" not in SupportResponseView.model_fields
    assert "sent" not in {item.value for item in SupportResponseStatus}


async def test_recommendation_rbac_decision_conflict_and_safe_audit() -> None:
    ticket, assessment, recommendation = workflow()
    recommendation.instructions = "Perform an MFA reset for the requester."
    recommendation.original_instructions = recommendation.instructions
    recommendation.action_type = RecommendationActionType.HIGH_IMPACT
    db = FakeDb()
    repository = FakeResolutionRepository(ticket, assessment, recommendation)
    service = RecommendationService(cast(AsyncSession, db))
    service.repository = cast(Any, repository)
    payload = RecommendationDecision(decision="approve", reason="Manager reviewed evidence")

    with pytest.raises(ForbiddenError):
        await service.decide(recommendation.id, payload, user())
    result = await service.decide(recommendation.id, payload, user(Role.MANAGER))
    assert result.status == RecommendationStatus.APPROVED
    assert db.commits == 1
    audit = next(item for item in repository.records if isinstance(item, AuditLog))
    assert recommendation.instructions not in str(audit.data)
    with pytest.raises(ConflictError):
        await service.decide(recommendation.id, payload, user(Role.MANAGER))


async def test_local_primary_response_is_cautious_and_never_claims_delivery() -> None:
    result = await LocalResponseProvider().generate(generation_input())
    normalized = result.body.casefold()
    assert result.body.startswith("Hi Taylor,")
    assert "vpn connection appears successful" in normalized
    assert "internal dns" in normalized
    assert "reconnect" in normalized and "verify" in normalized and "escalated" in normalized
    assert "no remediation action has been completed or sent" in normalized
    assert "we reset" not in normalized and "has been resolved" not in normalized


async def test_hosted_response_valid_malformed_claim_and_timeout() -> None:
    safe = GeneratedResponse(
        body="Hi Taylor, based on evidence, the probable DNS issue should be verified manually."
    ).model_dump_json()

    def response(content: str) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    valid_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response(safe)))
    provider = OpenAICompatibleResponseProvider(
        base_url="https://llm.test", api_key="key", model="model", timeout=1, client=valid_client
    )
    assert "probable" in (await provider.generate(generation_input())).body
    await valid_client.aclose()

    for content in (
        "not-json",
        GeneratedResponse(
            body="Hi Taylor, based on evidence, we reset the account and access appears normal."
        ).model_dump_json(),
    ):
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _, value=content: response(value))
        )
        invalid = OpenAICompatibleResponseProvider(
            base_url="https://llm.test", api_key="key", model="model", timeout=1, client=client
        )
        with pytest.raises(InvalidProviderResponse):
            await invalid.generate(generation_input())
        await client.aclose()

    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
    unavailable = OpenAICompatibleResponseProvider(
        base_url="https://llm.test", api_key="key", model="model", timeout=1, client=client
    )
    with pytest.raises(ProviderUnavailable):
        await unavailable.generate(generation_input())
    await client.aclose()


async def test_service_end_to_end_human_controlled_resolution() -> None:
    ticket, assessment, recommendation = workflow()
    actor = user()
    db = FakeDb()
    repository = FakeResolutionRepository(ticket, assessment, recommendation)

    recommendations = RecommendationService(cast(AsyncSession, db))
    recommendations.repository = cast(Any, repository)
    await recommendations.decide(
        recommendation.id,
        RecommendationDecision(decision="approve", reason="Evidence supports safe guidance"),
        actor,
    )

    responses = ResponseService(cast(AsyncSession, db))
    responses.repository = cast(Any, repository)
    draft = await responses.generate(ticket.id, actor, LocalResponseProvider())
    edited_body = draft.draft_body.replace(
        "Regards,", "Please reply if this continues.\n\nRegards,"
    )
    edited = await responses.edit(draft.id, ResponseEdit(draft_body=edited_body).draft_body, actor)
    assert edited.generated_by == ResponseGeneratedBy.HUMAN
    approved = await responses.approve(draft.id, actor)
    assert approved.final_body == edited_body
    assert not hasattr(approved, "sent_at")

    outcomes = OutcomeService(cast(AsyncSession, db))
    outcomes.repository = cast(Any, repository)
    resolved = await outcomes.resolve(
        ticket.id, approved.id, "Customer-facing guidance approved after human review.", actor
    )
    assert resolved.status == TicketStatus.RESOLVED
    assert recommendation.status == RecommendationStatus.COMPLETED
    assert resolved.resolved_at is not None
    assert db.commits == 5
    assert sum(isinstance(item, TicketEvent) for item in repository.records) == 5
    with pytest.raises(ConflictError):
        await outcomes.escalate(ticket.id, "Network Operations", "Issue persisted", actor)


async def test_response_requires_acceptance_and_rejection_allows_new_draft() -> None:
    ticket, assessment, recommendation = workflow()
    actor = user()
    db = FakeDb()
    repository = FakeResolutionRepository(ticket, assessment, recommendation)
    service = ResponseService(cast(AsyncSession, db))
    service.repository = cast(Any, repository)
    with pytest.raises(ConflictError):
        await service.generate(ticket.id, actor, LocalResponseProvider())

    recommendation.status = RecommendationStatus.APPROVED
    first = await service.generate(ticket.id, actor, LocalResponseProvider())
    with pytest.raises(ConflictError):
        await service.generate(ticket.id, actor, LocalResponseProvider())
    rejected = await service.reject(first.id, "Draft needs clearer customer guidance", actor)
    assert rejected.status == SupportResponseStatus.REJECTED
    second = await service.generate(ticket.id, actor, LocalResponseProvider())
    assert second.id != first.id
    assert second.status == SupportResponseStatus.DRAFT
    with pytest.raises(UnsafeResponseContentError):
        await service.edit(
            second.id,
            "Hi Taylor, based on evidence, we reset your account and restored access.",
            actor,
        )


async def test_escalation_is_explicit_internal_routing_without_response() -> None:
    ticket, assessment, recommendation = workflow()
    actor = user()
    db = FakeDb()
    repository = FakeResolutionRepository(ticket, assessment, recommendation)
    service = OutcomeService(cast(AsyncSession, db))
    service.repository = cast(Any, repository)
    result = await service.escalate(
        ticket.id, "Network Operations", "Probable DNS issue requires specialist review", actor
    )
    assert result.status == TicketStatus.ESCALATED
    assert result.escalation_destination == "Network Operations"
    event = next(item for item in repository.records if isinstance(item, TicketEvent))
    assert event.data == {"destination": "Network Operations", "routing_only": True}
    with pytest.raises(ConflictError):
        await service.resolve(ticket.id, uuid4(), "Cannot resolve after escalation", actor)


async def test_phase8_api_requires_auth_csrf_and_has_no_send_endpoint() -> None:
    ticket_id = uuid4()
    recommendation_id = uuid4()
    actor = user()
    auth = AuthContext(
        user=actor,
        session=Session(
            id=uuid4(),
            user_id=actor.id,
            token_hash="a" * 64,
            csrf_token="phase8-csrf",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            user=actor,
        ),
    )

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, FakeDb())

    async def auth_override() -> AuthContext:
        return auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unauthorized = await client.get(f"/api/v1/tickets/{ticket_id}/recommendations/latest")
    assert unauthorized.status_code == 401

    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            csrf = await client.post(
                f"/api/v1/recommendations/{recommendation_id}/decision",
                json={"decision": "approve", "reason": "Human reviewed evidence"},
            )
            no_send = await client.post(
                f"/api/v1/responses/{uuid4()}/send",
                headers={"X-CSRF-Token": "phase8-csrf"},
            )
    finally:
        app.dependency_overrides.clear()
    assert csrf.status_code == 403
    assert no_send.status_code == 404
