from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import InvalidProviderResponse, ProviderUnavailable
from app.config import Settings, get_settings
from app.errors import (
    AIConfigurationError,
    ConflictError,
    NotFoundError,
    ResponseGenerationError,
    UnsafeResponseContentError,
)
from app.models.domain import AuditLog, TicketEvent, User
from app.models.enums import (
    RecommendationStatus,
    ResponseGeneratedBy,
    SupportResponseStatus,
    TicketStatus,
)
from app.models.recommendations import SupportResponse
from app.repositories.resolution import ResolutionRepository
from app.response_generation.providers import (
    ResponseProvider,
    build_response_provider,
    validate_response_safety,
)
from app.response_generation.schemas import ResponseGenerationInput


class ResponseService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repository = ResolutionRepository(db)

    async def latest(self, ticket_id: UUID) -> SupportResponse | None:
        if await self.repository.ticket(ticket_id) is None:
            raise NotFoundError
        return await self.repository.latest_response(ticket_id)

    async def generate(
        self,
        ticket_id: UUID,
        actor: User,
        provider: ResponseProvider | None = None,
    ) -> SupportResponse:
        ticket = await self.repository.ticket(ticket_id)
        if ticket is None:
            raise NotFoundError
        if ticket.status in {TicketStatus.RESOLVED, TicketStatus.ESCALATED}:
            raise ConflictError
        assessment = await self.repository.latest_completed_assessment(ticket_id)
        recommendation = await self.repository.latest_recommendation(ticket_id)
        if (
            assessment is None
            or recommendation is None
            or recommendation.assessment_id != assessment.id
            or recommendation.status
            not in {RecommendationStatus.APPROVED, RecommendationStatus.MODIFIED}
        ):
            raise ConflictError
        previous = await self.repository.latest_response(ticket_id)
        if previous is not None and previous.status != SupportResponseStatus.REJECTED:
            raise ConflictError
        try:
            active_provider = provider or build_response_provider(self.settings)
        except ValueError as exc:
            raise AIConfigurationError from exc
        try:
            generated = await active_provider.generate(
                ResponseGenerationInput(
                    ticket_id=ticket.id,
                    requester_name=ticket.requester_name,
                    title=ticket.title,
                    description=ticket.description[:1000],
                    probable_root_cause=assessment.probable_root_cause or "an undetermined issue",
                    recommendation=recommendation.instructions,
                    limitations=assessment.limitations,
                    requires_escalation=assessment.requires_escalation,
                )
            )
        except (InvalidProviderResponse, ProviderUnavailable, TimeoutError) as exc:
            raise ResponseGenerationError from exc
        value = SupportResponse(
            id=uuid4(),
            ticket_id=ticket.id,
            assessment_id=assessment.id,
            recommendation_id=recommendation.id,
            generated_by=ResponseGeneratedBy.AI,
            provider=active_provider.name,
            model=active_provider.model,
            mode=active_provider.mode,
            draft_body=generated.body,
            status=SupportResponseStatus.DRAFT,
            created_by_id=actor.id,
            created_by=actor,
        )
        self.repository.add(value)
        self._record(value, actor, "response_generated", "ticket.response.generated")
        await self._commit(value)
        return value

    async def edit(self, response_id: UUID, draft_body: str, actor: User) -> SupportResponse:
        value = await self._draft(response_id)
        try:
            validate_response_safety(draft_body)
        except InvalidProviderResponse as exc:
            raise UnsafeResponseContentError from exc
        value.draft_body = draft_body
        value.generated_by = ResponseGeneratedBy.HUMAN
        self._record(value, actor, "response_edited", "ticket.response.edited")
        await self._commit(value)
        return value

    async def approve(self, response_id: UUID, actor: User) -> SupportResponse:
        value = await self._draft(response_id)
        try:
            validate_response_safety(value.draft_body)
        except InvalidProviderResponse as exc:
            raise UnsafeResponseContentError from exc
        value.final_body = value.draft_body
        value.status = SupportResponseStatus.APPROVED
        value.approved_by_id = actor.id
        value.approved_by = actor
        value.approved_at = datetime.now(UTC)
        self._record(value, actor, "response_approved", "ticket.response.approved")
        await self._commit(value)
        return value

    async def reject(self, response_id: UUID, reason: str, actor: User) -> SupportResponse:
        value = await self._draft(response_id)
        value.status = SupportResponseStatus.REJECTED
        value.rejected_by_id = actor.id
        value.rejected_by = actor
        value.rejection_reason = reason
        value.rejected_at = datetime.now(UTC)
        self._record(value, actor, "response_rejected", "ticket.response.rejected")
        await self._commit(value)
        return value

    async def _draft(self, response_id: UUID) -> SupportResponse:
        value = await self.repository.response(response_id, lock=True)
        if value is None:
            raise NotFoundError
        if value.status != SupportResponseStatus.DRAFT:
            raise ConflictError
        ticket = await self.repository.ticket(value.ticket_id, lock=True)
        if ticket is None or ticket.status in {TicketStatus.RESOLVED, TicketStatus.ESCALATED}:
            raise ConflictError
        return value

    def _record(self, value: SupportResponse, actor: User, event_type: str, action: str) -> None:
        data: dict[str, Any] = {"generated_by": value.generated_by.value}
        self.repository.add(
            TicketEvent(
                ticket_id=value.ticket_id,
                actor_id=actor.id,
                event_type=event_type,
                summary={
                    "response_generated": "Grounded customer response draft generated",
                    "response_edited": "Customer response draft edited by a human",
                    "response_approved": "Customer response approved; no delivery performed",
                    "response_rejected": "Customer response draft rejected",
                }[event_type],
                data=data,
            )
        )
        self.repository.add(
            AuditLog(
                actor_id=actor.id,
                action=action,
                resource_type="ticket.support_response",
                resource_id=value.id,
                data=data,
            )
        )

    async def _commit(self, value: SupportResponse) -> None:
        try:
            await self.db.commit()
            await self.db.refresh(value)
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError from exc
        except Exception:
            await self.db.rollback()
            raise
