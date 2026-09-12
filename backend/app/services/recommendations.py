from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, ForbiddenError, NotFoundError
from app.models.domain import AuditLog, TicketEvent, User
from app.models.enums import (
    RecommendationActionType,
    RecommendationStatus,
    Role,
    TicketStatus,
    role_allows,
)
from app.models.recommendations import Recommendation
from app.recommendations.policy import classify_action
from app.repositories.resolution import ResolutionRepository
from app.schemas.recommendations import RecommendationDecision


class RecommendationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ResolutionRepository(db)

    async def latest(self, ticket_id: UUID) -> Recommendation | None:
        if await self.repository.ticket(ticket_id) is None:
            raise NotFoundError
        return await self.repository.latest_recommendation(ticket_id)

    async def decide(
        self, recommendation_id: UUID, payload: RecommendationDecision, actor: User
    ) -> Recommendation:
        value = await self.repository.recommendation(recommendation_id, lock=True)
        if value is None:
            raise NotFoundError
        if value.status != RecommendationStatus.PROPOSED:
            raise ConflictError
        ticket = await self.repository.ticket(value.ticket_id, lock=True)
        if ticket is None or ticket.status in {TicketStatus.RESOLVED, TicketStatus.ESCALATED}:
            raise ConflictError

        action_type = value.action_type
        if payload.modified_instructions is not None:
            action_type = classify_action(
                payload.modified_instructions,
                requires_escalation=value.action_type == RecommendationActionType.ESCALATE,
            )
        if (
            payload.decision != "reject"
            and action_type == RecommendationActionType.HIGH_IMPACT
            and not role_allows(actor.role, Role.MANAGER)
        ):
            raise ForbiddenError

        status = {
            "approve": RecommendationStatus.APPROVED,
            "reject": RecommendationStatus.REJECTED,
            "modify": RecommendationStatus.MODIFIED,
        }[payload.decision]
        if payload.modified_instructions is not None:
            value.instructions = payload.modified_instructions
            value.action_type = action_type
        value.status = status
        value.decided_by_id = actor.id
        value.decided_by = actor
        value.decision_reason = payload.reason
        value.decided_at = datetime.now(UTC)
        self._record(value, actor, payload.decision)
        await self._commit(value)
        return value

    def _record(self, value: Recommendation, actor: User, decision: str) -> None:
        data: dict[str, Any] = {
            "decision": decision,
            "action_type": value.action_type.value,
            "instructions_modified": decision == "modify",
        }
        self.repository.add(
            TicketEvent(
                ticket_id=value.ticket_id,
                actor_id=actor.id,
                event_type="recommendation_decided",
                summary={
                    "approve": "Support recommendation approved by a human",
                    "reject": "Support recommendation rejected by a human",
                    "modify": "Support recommendation modified and accepted by a human",
                }[decision],
                data=data,
            )
        )
        self.repository.add(
            AuditLog(
                actor_id=actor.id,
                action=f"ticket.recommendation.{decision}",
                resource_type="ticket.recommendation",
                resource_id=value.id,
                data=data,
            )
        )

    async def _commit(self, value: Recommendation) -> None:
        try:
            await self.db.commit()
            await self.db.refresh(value)
        except Exception:
            await self.db.rollback()
            raise
