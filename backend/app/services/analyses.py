import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.policy import assign_priority
from app.ai.providers import (
    AnalysisProvider,
    InvalidProviderResponse,
    ProviderUnavailable,
    build_provider,
)
from app.ai.schemas import ExtractedEntities, PriorityFactors, TicketAnalysisInput
from app.config import Settings, get_settings
from app.db.session import session_factory
from app.errors import AIConfigurationError, ConflictError, NotFoundError
from app.models.domain import AIAnalysis, AuditLog, TicketEvent, User
from app.models.enums import AnalysisStatus
from app.repositories.analyses import AnalysisRepository
from app.schemas.analyses import AnalysisResponse

WORKFLOW_VERSION = "4.0"


def analysis_response(analysis: AIAnalysis) -> AnalysisResponse:
    entities = (
        ExtractedEntities.model_validate(analysis.entities)
        if analysis.entities is not None
        else None
    )
    factors = (
        PriorityFactors.model_validate(analysis.priority_factors)
        if analysis.priority_factors is not None
        else None
    )
    return AnalysisResponse(
        id=analysis.id,
        ticket_id=analysis.ticket_id,
        requested_by_id=analysis.requested_by_id,
        workflow_version=analysis.workflow_version,
        provider=analysis.provider,
        model=analysis.model,
        mode=analysis.mode,
        status=analysis.status,
        category=analysis.category,
        category_confidence=analysis.category_confidence,
        recommended_priority=analysis.recommended_priority,
        validated_priority=analysis.validated_priority,
        entities=entities,
        priority_factors=factors,
        requires_manual_review=analysis.requires_manual_review,
        error_code=analysis.error_code,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        duration_ms=analysis.duration_ms,
        created_at=analysis.created_at,
    )


class AnalysisService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repository = AnalysisRepository(db)

    async def request(self, ticket_id: UUID, actor: User) -> AIAnalysis:
        ticket = await self.repository.ticket(ticket_id)
        if ticket is None:
            raise NotFoundError
        if await self.repository.active_for_ticket(ticket_id) is not None:
            raise ConflictError
        try:
            provider = build_provider(self.settings)
        except ValueError as exc:
            raise AIConfigurationError from exc
        analysis = AIAnalysis(
            ticket_id=ticket.id,
            requested_by_id=actor.id,
            workflow_version=WORKFLOW_VERSION,
            provider=provider.name,
            model=provider.model,
            mode=provider.mode,
            status=AnalysisStatus.QUEUED,
        )
        self.repository.add(analysis)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError from exc
        except Exception:
            await self.db.rollback()
            raise
        self._record(analysis, "queued", "AI triage queued", "ticket.analysis.requested")
        await self._commit(analysis)
        return analysis

    async def get(self, analysis_id: UUID) -> AIAnalysis:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            raise NotFoundError
        return analysis

    async def latest(self, ticket_id: UUID) -> AIAnalysis | None:
        if await self.repository.ticket(ticket_id) is None:
            raise NotFoundError
        return await self.repository.latest_for_ticket(ticket_id)

    async def retry(self, analysis_id: UUID, actor: User) -> AIAnalysis:
        analysis = await self.get(analysis_id)
        if analysis.status not in {AnalysisStatus.FAILED, AnalysisStatus.TIMED_OUT}:
            raise ConflictError
        if await self.repository.active_for_ticket(analysis.ticket_id) is not None:
            raise ConflictError
        try:
            provider = build_provider(self.settings)
        except ValueError as exc:
            raise AIConfigurationError from exc
        analysis.requested_by_id = actor.id
        analysis.provider = provider.name
        analysis.model = provider.model
        analysis.mode = provider.mode
        analysis.status = AnalysisStatus.QUEUED
        analysis.category = None
        analysis.category_confidence = None
        analysis.recommended_priority = None
        analysis.validated_priority = None
        analysis.entities = None
        analysis.priority_factors = None
        analysis.requires_manual_review = False
        analysis.error_code = None
        analysis.started_at = None
        analysis.completed_at = None
        analysis.duration_ms = None
        self._record(analysis, "queued", "AI triage retry queued", "ticket.analysis.retried")
        await self._commit(analysis)
        return analysis

    async def execute(self, analysis_id: UUID, provider: AnalysisProvider) -> None:
        analysis = await self.get(analysis_id)
        if analysis.status != AnalysisStatus.QUEUED:
            return
        analysis.status = AnalysisStatus.RUNNING
        analysis.started_at = datetime.now(UTC)
        await self._commit(analysis)
        ticket = await self.repository.ticket(analysis.ticket_id)
        if ticket is None:
            await self._fail(analysis, AnalysisStatus.FAILED, "ticket_not_found")
            return
        payload = TicketAnalysisInput(
            title=ticket.title,
            description=ticket.description,
            requester_name=ticket.requester_name,
            requester_department=ticket.requester_department,
            location=ticket.location,
            device=ticket.device,
            application=ticket.application,
        )
        started = monotonic()
        try:
            async with asyncio.timeout(self.settings.ai_timeout_seconds):
                signals = await provider.analyze(payload)
            priority = assign_priority(signals.priority_factors, signals.entities.urgency)
            analysis.status = AnalysisStatus.COMPLETED
            analysis.category = signals.category.value
            analysis.category_confidence = signals.category_confidence
            analysis.recommended_priority = priority
            analysis.validated_priority = priority
            analysis.entities = signals.entities.model_dump(mode="json")
            analysis.priority_factors = signals.priority_factors.model_dump(mode="json")
            analysis.requires_manual_review = (
                signals.category_confidence < self.settings.ai_confidence_threshold
                or signals.entities.affected_scope.value == "unknown"
            )
            analysis.error_code = None
            analysis.completed_at = datetime.now(UTC)
            analysis.duration_ms = max(0, round((monotonic() - started) * 1000))
            ticket.category = signals.category.value
            if not ticket.priority_overridden:
                ticket.priority = priority
            self._record(
                analysis,
                "completed",
                "AI triage completed",
                "ticket.analysis.completed",
                {"requires_manual_review": analysis.requires_manual_review},
            )
            await self._commit(analysis)
        except TimeoutError:
            await self._fail(analysis, AnalysisStatus.TIMED_OUT, "analysis_timeout", started)
        except ProviderUnavailable:
            await self._fail(analysis, AnalysisStatus.FAILED, "provider_unavailable", started)
        except InvalidProviderResponse:
            await self._fail(analysis, AnalysisStatus.FAILED, "invalid_provider_response", started)
        except Exception:
            await self._fail(analysis, AnalysisStatus.FAILED, "analysis_failed", started)

    async def _fail(
        self,
        analysis: AIAnalysis,
        status: AnalysisStatus,
        error_code: str,
        started: float | None = None,
    ) -> None:
        await self.db.rollback()
        analysis = await self.get(analysis.id)
        analysis.status = status
        analysis.requires_manual_review = True
        analysis.error_code = error_code
        analysis.completed_at = datetime.now(UTC)
        if started is not None:
            analysis.duration_ms = max(0, round((monotonic() - started) * 1000))
        self._record(
            analysis,
            "timed_out" if status == AnalysisStatus.TIMED_OUT else "failed",
            "AI triage timed out" if status == AnalysisStatus.TIMED_OUT else "AI triage failed",
            "ticket.analysis.timed_out"
            if status == AnalysisStatus.TIMED_OUT
            else "ticket.analysis.failed",
            {"error_code": error_code},
        )
        await self._commit(analysis)

    def _record(
        self,
        analysis: AIAnalysis,
        event_type: str,
        summary: str,
        action: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.repository.add(
            TicketEvent(
                ticket_id=analysis.ticket_id,
                actor_id=analysis.requested_by_id,
                event_type=event_type,
                summary=summary,
                data=data,
            )
        )
        self.repository.add(
            AuditLog(
                actor_id=analysis.requested_by_id,
                action=action,
                resource_type="ticket.analysis",
                resource_id=analysis.id,
                data=data,
            )
        )

    async def _commit(self, analysis: AIAnalysis) -> None:
        try:
            await self.db.commit()
            await self.db.refresh(analysis)
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError from exc
        except Exception:
            await self.db.rollback()
            raise


async def run_analysis_job(
    analysis_id: UUID,
    *,
    provider: AnalysisProvider | None = None,
    settings: Settings | None = None,
    session_maker: async_sessionmaker[AsyncSession] | Callable[[], Any] = session_factory,
) -> None:
    runtime_settings = settings or get_settings()
    runtime_provider = provider or build_provider(runtime_settings)
    async with session_maker() as db:
        await AnalysisService(db, runtime_settings).execute(analysis_id, runtime_provider)
