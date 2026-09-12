from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError
from app.models.domain import AuditLog, Ticket, TicketEvent, User
from app.models.enums import (
    RecommendationActionType,
    RecommendationStatus,
    SupportResponseStatus,
    TicketStatus,
)
from app.repositories.resolution import ResolutionRepository


class OutcomeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ResolutionRepository(db)

    async def resolve(
        self, ticket_id: UUID, response_id: UUID, summary: str, actor: User
    ) -> Ticket:
        ticket = await self._open_ticket(ticket_id)
        response = await self.repository.response(response_id, lock=True)
        recommendation = (
            await self.repository.recommendation(response.recommendation_id, lock=True)
            if response is not None and response.ticket_id == ticket.id
            else None
        )
        if (
            response is None
            or response.ticket_id != ticket.id
            or response.status != SupportResponseStatus.APPROVED
            or response.final_body is None
            or recommendation is None
            or recommendation.ticket_id != ticket.id
            or recommendation.status
            not in {RecommendationStatus.APPROVED, RecommendationStatus.MODIFIED}
        ):
            raise ConflictError
        now = datetime.now(UTC)
        ticket.status = TicketStatus.RESOLVED
        ticket.resolved_at = now
        ticket.resolution_summary = summary
        recommendation.status = RecommendationStatus.COMPLETED
        self._record(
            ticket,
            actor,
            "ticket_resolved",
            "ticket.resolve",
            {"response_id": str(response.id), "response_delivery": "not_performed"},
        )
        await self._commit(ticket)
        return ticket

    async def escalate(self, ticket_id: UUID, destination: str, reason: str, actor: User) -> Ticket:
        ticket = await self._open_ticket(ticket_id)
        if await self.repository.latest_completed_assessment(ticket_id) is None:
            raise ConflictError
        recommendation = await self.repository.latest_recommendation(ticket_id, lock=True)
        ticket.status = TicketStatus.ESCALATED
        ticket.escalated_at = datetime.now(UTC)
        ticket.escalation_destination = destination
        ticket.escalation_reason = reason
        if (
            recommendation is not None
            and recommendation.action_type == RecommendationActionType.ESCALATE
            and recommendation.status
            in {
                RecommendationStatus.PROPOSED,
                RecommendationStatus.APPROVED,
                RecommendationStatus.MODIFIED,
            }
        ):
            if recommendation.status == RecommendationStatus.PROPOSED:
                recommendation.decided_by_id = actor.id
                recommendation.decided_by = actor
                recommendation.decision_reason = reason
                recommendation.decided_at = datetime.now(UTC)
            recommendation.status = RecommendationStatus.COMPLETED
        self._record(
            ticket,
            actor,
            "ticket_escalated",
            "ticket.escalate",
            {"destination": destination, "routing_only": True},
        )
        await self._commit(ticket)
        return ticket

    async def _open_ticket(self, ticket_id: UUID) -> Ticket:
        ticket = await self.repository.ticket(ticket_id, lock=True)
        if ticket is None:
            raise NotFoundError
        if ticket.status in {TicketStatus.RESOLVED, TicketStatus.ESCALATED}:
            raise ConflictError
        return ticket

    def _record(
        self,
        ticket: Ticket,
        actor: User,
        event_type: str,
        action: str,
        data: dict[str, Any],
    ) -> None:
        self.repository.add(
            TicketEvent(
                ticket_id=ticket.id,
                actor_id=actor.id,
                event_type=event_type,
                summary=(
                    "Ticket explicitly resolved by a human"
                    if event_type == "ticket_resolved"
                    else "Ticket explicitly routed for internal escalation"
                ),
                data=data,
            )
        )
        self.repository.add(
            AuditLog(
                actor_id=actor.id,
                action=action,
                resource_type="ticket",
                resource_id=ticket.id,
                data=data,
            )
        )

    async def _commit(self, ticket: Ticket) -> None:
        try:
            await self.db.commit()
            await self.db.refresh(ticket)
        except Exception:
            await self.db.rollback()
            raise
