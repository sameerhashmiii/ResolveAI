from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessments import RootCauseAssessment
from app.models.domain import AuditLog, Ticket, TicketEvent
from app.models.enums import RootCauseStatus
from app.models.recommendations import Recommendation, SupportResponse


class ResolutionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, value: Recommendation | SupportResponse | TicketEvent | AuditLog) -> None:
        self.db.add(value)

    async def ticket(self, ticket_id: UUID, *, lock: bool = False) -> Ticket | None:
        statement = select(Ticket).where(Ticket.id == ticket_id)
        if lock:
            statement = statement.with_for_update(of=Ticket)
        return cast(Ticket | None, await self.db.scalar(statement))

    async def recommendation(
        self, recommendation_id: UUID, *, lock: bool = False
    ) -> Recommendation | None:
        statement = select(Recommendation).where(Recommendation.id == recommendation_id)
        if lock:
            statement = statement.with_for_update(of=Recommendation)
        return cast(Recommendation | None, await self.db.scalar(statement))

    async def latest_recommendation(
        self, ticket_id: UUID, *, lock: bool = False
    ) -> Recommendation | None:
        statement = (
            select(Recommendation)
            .where(Recommendation.ticket_id == ticket_id)
            .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
            .limit(1)
        )
        if lock:
            statement = statement.with_for_update(of=Recommendation)
        return cast(
            Recommendation | None,
            await self.db.scalar(statement),
        )

    async def latest_completed_assessment(self, ticket_id: UUID) -> RootCauseAssessment | None:
        return cast(
            RootCauseAssessment | None,
            await self.db.scalar(
                select(RootCauseAssessment)
                .where(
                    RootCauseAssessment.ticket_id == ticket_id,
                    RootCauseAssessment.status == RootCauseStatus.COMPLETED,
                )
                .order_by(RootCauseAssessment.created_at.desc(), RootCauseAssessment.id.desc())
                .limit(1)
            ),
        )

    async def response(
        self, response_id: UUID, *, lock: bool = False
    ) -> SupportResponse | None:
        statement = select(SupportResponse).where(SupportResponse.id == response_id)
        if lock:
            statement = statement.with_for_update(of=SupportResponse)
        return cast(SupportResponse | None, await self.db.scalar(statement))

    async def latest_response(self, ticket_id: UUID) -> SupportResponse | None:
        return cast(
            SupportResponse | None,
            await self.db.scalar(
                select(SupportResponse)
                .where(SupportResponse.ticket_id == ticket_id)
                .order_by(SupportResponse.created_at.desc(), SupportResponse.id.desc())
                .limit(1)
            ),
        )
