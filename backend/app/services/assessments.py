import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Any, cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.providers import InvalidProviderResponse, ProviderUnavailable
from app.config import Settings, get_settings
from app.db.session import session_factory
from app.errors import AIConfigurationError, ConflictError, NotFoundError
from app.models.assessments import AssessmentEvidence, RootCauseAssessment
from app.models.domain import AuditLog, TicketEvent, User
from app.models.enums import RootCauseStatus
from app.repositories.assessments import AssessmentRepository
from app.root_cause.confidence import calculate_confidence
from app.root_cause.evidence import collect_evidence
from app.root_cause.providers import GroundedInferenceProvider, build_grounded_provider
from app.root_cause.schemas import ConfidenceFactor, GroundedInferenceInput
from app.schemas.assessments import (
    AssessmentExplanation,
    AssessmentResponse,
    ConfidenceResponse,
    EscalationResponse,
    EvidenceResponse,
    InferenceResponse,
    RecommendationResponse,
    TimelineStep,
)

WORKFLOW_VERSION = "7.0"
CONFIDENCE_VERSION = "confidence-v1"


def assessment_response(value: RootCauseAssessment, settings: Settings) -> AssessmentResponse:
    evidence = [
        _evidence_response(item)
        for item in sorted(value.evidence, key=lambda item: item.display_order)
        if item.assessment_id == value.id
    ]
    factors = [ConfidenceFactor.model_validate(item) for item in value.confidence_factors]
    inference = (
        InferenceResponse(summary=value.probable_root_cause, key=value.inference_key)
        if value.probable_root_cause is not None
        else None
    )
    recommendation = (
        RecommendationResponse(text=value.recommendation)
        if value.recommendation is not None
        else None
    )
    threshold = settings.root_cause_confidence_threshold
    return AssessmentResponse(
        id=value.id,
        ticket_id=value.ticket_id,
        investigation_id=value.investigation_id,
        analysis_id=value.analysis_id,
        requested_by_id=value.requested_by_id,
        workflow_version=value.workflow_version,
        provider=value.provider,
        model=value.model,
        mode=cast(Any, value.mode),
        mode_label=(
            "Deterministic demo inference"
            if value.mode == "local_demo"
            else "Hosted grounded inference"
        ),
        status=value.status,
        observed_evidence=evidence,
        inference=inference,
        confidence=ConfidenceResponse(
            score=value.confidence,
            version=value.confidence_version,
            factors=factors,
        ),
        recommendation=recommendation,
        limitations=value.limitations,
        escalation=EscalationResponse(
            required=value.requires_escalation,
            threshold=threshold,
            reason=_escalation_reason(value, threshold),
        ),
        error_code=value.error_code,
        started_at=value.started_at,
        completed_at=value.completed_at,
        duration_ms=value.duration_ms,
        created_at=value.created_at,
    )


class AssessmentService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repository = AssessmentRepository(db)

    async def request(self, ticket_id: UUID, actor: User) -> RootCauseAssessment:
        ticket = await self.repository.ticket(ticket_id)
        if ticket is None:
            raise NotFoundError
        investigation = await self.repository.latest_completed_investigation(ticket_id)
        if (
            investigation is None
            or await self.repository.active(ticket_id) is not None
            or await self.repository.for_investigation(investigation.id) is not None
        ):
            raise ConflictError
        try:
            provider = build_grounded_provider(self.settings)
        except ValueError as exc:
            raise AIConfigurationError from exc
        value = RootCauseAssessment(
            ticket_id=ticket.id,
            investigation_id=investigation.id,
            analysis_id=investigation.analysis_id,
            requested_by_id=actor.id,
            workflow_version=WORKFLOW_VERSION,
            provider=provider.name,
            model=provider.model,
            mode=provider.mode,
            status=RootCauseStatus.QUEUED,
            confidence_version=CONFIDENCE_VERSION,
            requires_escalation=True,
            limitations=[],
            confidence_factors=[],
        )
        self.repository.add(value)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError from exc
        except Exception:
            await self.db.rollback()
            raise
        self._record(value, "queued", "Root-cause assessment queued", "ticket.assessment.requested")
        await self._commit(value)
        return value

    async def get(self, assessment_id: UUID) -> RootCauseAssessment:
        value = await self.repository.get(assessment_id)
        if value is None:
            raise NotFoundError
        return value

    async def latest(self, ticket_id: UUID) -> RootCauseAssessment | None:
        if await self.repository.ticket(ticket_id) is None:
            raise NotFoundError
        return await self.repository.latest(ticket_id)

    async def retry(self, assessment_id: UUID, actor: User) -> RootCauseAssessment:
        value = await self.get(assessment_id)
        if value.status not in {RootCauseStatus.FAILED, RootCauseStatus.TIMED_OUT}:
            raise ConflictError
        if await self.repository.active(value.ticket_id) is not None:
            raise ConflictError
        try:
            provider = build_grounded_provider(self.settings)
        except ValueError as exc:
            raise AIConfigurationError from exc
        for item in list(value.evidence):
            await self.db.delete(item)
        value.evidence.clear()
        value.requested_by_id = actor.id
        value.provider = provider.name
        value.model = provider.model
        value.mode = provider.mode
        value.status = RootCauseStatus.QUEUED
        value.probable_root_cause = None
        value.inference_key = None
        value.confidence = None
        value.recommendation = None
        value.requires_escalation = True
        value.limitations = []
        value.confidence_factors = []
        value.error_code = None
        value.started_at = None
        value.completed_at = None
        value.duration_ms = None
        self._record(
            value, "queued", "Root-cause assessment retry queued", "ticket.assessment.retried"
        )
        await self._commit(value)
        return value

    async def execute(
        self,
        assessment_id: UUID,
        provider: GroundedInferenceProvider | None = None,
    ) -> None:
        value = await self.get(assessment_id)
        if value.status != RootCauseStatus.QUEUED:
            return
        value.status = RootCauseStatus.RUNNING
        value.started_at = datetime.now(UTC)
        await self._commit(value)
        ticket = await self.repository.ticket(value.ticket_id)
        analysis = await self.repository.analysis(value.analysis_id)
        investigation = value.investigation
        if ticket is None or investigation.id != value.investigation_id:
            await self._fail(value, RootCauseStatus.FAILED, "required_context_missing")
            return
        started = monotonic()
        try:
            evidence, collection_limitations = collect_evidence(investigation, ticket, analysis)
            if not evidence:
                await self._fail(value, RootCauseStatus.FAILED, "insufficient_context", started)
                return
            active_provider = provider or build_grounded_provider(self.settings)
            payload = GroundedInferenceInput(
                ticket_id=ticket.id,
                title=ticket.title,
                description=ticket.description[:1000],
                location=ticket.location,
                application=ticket.application,
                evidence=evidence,
            )
            async with asyncio.timeout(self.settings.root_cause_timeout_seconds):
                inference = await active_provider.infer(payload)
            source_ids = {item.source_id for item in evidence}
            if not set(inference.selected_source_ids) <= source_ids:
                raise InvalidProviderResponse
            confidence = calculate_confidence(inference, evidence)
            for order, item in enumerate(evidence, 1):
                self.repository.add(
                    AssessmentEvidence(
                        assessment_id=value.id,
                        evidence_type=item.evidence_type,
                        source_id=item.source_id,
                        title=item.title,
                        excerpt=item.excerpt,
                        supports=item.supports,
                        relevance_score=item.relevance_score,
                        evidence_metadata=item.metadata,
                        display_order=order,
                    )
                )
            value.status = RootCauseStatus.COMPLETED
            value.probable_root_cause = inference.probable_root_cause
            value.inference_key = inference.inference_key
            value.confidence = confidence.score
            value.recommendation = inference.recommended_action
            value.requires_escalation = (
                confidence.score < self.settings.root_cause_confidence_threshold
            )
            value.limitations = list(dict.fromkeys(collection_limitations + inference.limitations))[
                :20
            ]
            value.confidence_factors = [item.model_dump(mode="json") for item in confidence.factors]
            value.error_code = None
            value.completed_at = datetime.now(UTC)
            value.duration_ms = max(0, round((monotonic() - started) * 1000))
            self._record(
                value,
                "completed",
                "Probable root-cause assessment completed",
                "ticket.assessment.completed",
                {
                    "confidence": confidence.score,
                    "confidence_version": confidence.version,
                    "requires_escalation": value.requires_escalation,
                    "evidence_count": len(evidence),
                },
            )
            await self._commit(value)
        except TimeoutError:
            await self._fail(value, RootCauseStatus.TIMED_OUT, "root_cause_timeout", started)
        except ProviderUnavailable:
            await self._fail(value, RootCauseStatus.FAILED, "provider_unavailable", started)
        except InvalidProviderResponse:
            await self._fail(value, RootCauseStatus.FAILED, "invalid_provider_response", started)
        except ValueError:
            await self._fail(value, RootCauseStatus.FAILED, "provider_configuration", started)
        except Exception:
            await self._fail(value, RootCauseStatus.FAILED, "root_cause_failed", started)

    async def explanation(self, assessment_id: UUID) -> AssessmentExplanation:
        value = await self.get(assessment_id)
        response = assessment_response(value, self.settings)
        selected = {
            source_id
            for factor in response.confidence.factors
            if factor.applied
            for source_id in factor.source_ids
        }
        supporting = [item for item in response.observed_evidence if item.source_id in selected]
        if not supporting:
            supporting = response.observed_evidence
        return AssessmentExplanation(
            assessment=response,
            investigation_timeline=[
                TimelineStep(
                    label=step.label,
                    status=step.status,
                    source_count=step.source_count,
                )
                for step in sorted(value.investigation.steps, key=lambda item: item.step_order)
            ],
            supporting_evidence=supporting,
            confidence_factors=response.confidence.factors,
        )

    async def _fail(
        self,
        value: RootCauseAssessment,
        status: RootCauseStatus,
        error_code: str,
        started: float | None = None,
    ) -> None:
        await self.db.rollback()
        value = await self.get(value.id)
        value.status = status
        value.requires_escalation = True
        value.error_code = error_code
        value.limitations = ["Automated probable-cause assessment did not complete"]
        value.completed_at = datetime.now(UTC)
        if started is not None:
            value.duration_ms = max(0, round((monotonic() - started) * 1000))
        timed_out = status == RootCauseStatus.TIMED_OUT
        self._record(
            value,
            "timed_out" if timed_out else "failed",
            "Root-cause assessment timed out" if timed_out else "Root-cause assessment failed",
            "ticket.assessment.timed_out" if timed_out else "ticket.assessment.failed",
            {"error_code": error_code, "requires_escalation": True},
        )
        await self._commit(value)

    def _record(
        self,
        value: RootCauseAssessment,
        event_type: str,
        summary: str,
        action: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.repository.add(
            TicketEvent(
                ticket_id=value.ticket_id,
                actor_id=value.requested_by_id,
                event_type=event_type,
                summary=summary,
                data=data,
            )
        )
        self.repository.add(
            AuditLog(
                actor_id=value.requested_by_id,
                action=action,
                resource_type="ticket.root_cause_assessment",
                resource_id=value.id,
                data=data,
            )
        )

    async def _commit(self, value: RootCauseAssessment) -> None:
        try:
            await self.db.commit()
            await self.db.refresh(value)
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError from exc
        except Exception:
            await self.db.rollback()
            raise


def _evidence_response(item: AssessmentEvidence) -> EvidenceResponse:
    return EvidenceResponse(
        id=item.id,
        evidence_type=item.evidence_type,
        source_id=item.source_id,
        title=item.title,
        excerpt=item.excerpt,
        supports=item.supports,
        relevance_score=item.relevance_score,
        metadata=item.evidence_metadata,
        display_order=item.display_order,
    )


def _escalation_reason(value: RootCauseAssessment, threshold: float) -> str:
    if value.status != RootCauseStatus.COMPLETED:
        return "Assessment is incomplete; manual escalation is required"
    if value.requires_escalation:
        return f"Deterministic evidence confidence is below the {threshold:.2f} threshold"
    return "Deterministic evidence confidence meets the escalation threshold"


async def run_assessment_job(
    assessment_id: UUID,
    *,
    settings: Settings | None = None,
    session_maker: async_sessionmaker[AsyncSession] | Callable[[], Any] = session_factory,
) -> None:
    async with session_maker() as db:
        service = AssessmentService(db, settings)
        try:
            provider = build_grounded_provider(service.settings)
        except ValueError:
            provider = None
        await service.execute(assessment_id, provider)
