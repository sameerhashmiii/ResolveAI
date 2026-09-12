from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import AIAnalysis, AuditLog, Ticket, TicketEvent
from app.models.enums import AnalysisStatus


class AnalysisRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, value: AIAnalysis | TicketEvent | AuditLog) -> None:
        self.db.add(value)

    async def get(self, analysis_id: UUID) -> AIAnalysis | None:
        return cast(AIAnalysis | None, await self.db.get(AIAnalysis, analysis_id))

    async def ticket(self, ticket_id: UUID) -> Ticket | None:
        return cast(Ticket | None, await self.db.get(Ticket, ticket_id))

    async def active_for_ticket(self, ticket_id: UUID) -> AIAnalysis | None:
        return cast(
            AIAnalysis | None,
            await self.db.scalar(
                select(AIAnalysis).where(
                    AIAnalysis.ticket_id == ticket_id,
                    AIAnalysis.status.in_([AnalysisStatus.QUEUED, AnalysisStatus.RUNNING]),
                )
            ),
        )

    async def latest_for_ticket(self, ticket_id: UUID) -> AIAnalysis | None:
        return cast(
            AIAnalysis | None,
            await self.db.scalar(
                select(AIAnalysis)
                .where(AIAnalysis.ticket_id == ticket_id)
                .order_by(AIAnalysis.created_at.desc(), AIAnalysis.id.desc())
                .limit(1)
            ),
        )
