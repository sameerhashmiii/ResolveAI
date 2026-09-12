from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain import AIAnalysis, AuditLog, Ticket, TicketEvent
from app.models.enums import AnalysisStatus, InvestigationStatus
from app.models.operational import Investigation, InvestigationStep


class InvestigationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, value: Investigation | InvestigationStep | TicketEvent | AuditLog) -> None:
        self.db.add(value)

    async def ticket(self, ticket_id: UUID) -> Ticket | None:
        return cast(Ticket | None, await self.db.get(Ticket, ticket_id))

    async def get(self, investigation_id: UUID) -> Investigation | None:
        return cast(
            Investigation | None,
            await self.db.scalar(
                select(Investigation)
                .options(selectinload(Investigation.steps))
                .where(Investigation.id == investigation_id)
            ),
        )

    async def latest(self, ticket_id: UUID) -> Investigation | None:
        return cast(
            Investigation | None,
            await self.db.scalar(
                select(Investigation)
                .options(selectinload(Investigation.steps))
                .where(Investigation.ticket_id == ticket_id)
                .order_by(Investigation.created_at.desc(), Investigation.id.desc())
                .limit(1)
            ),
        )

    async def latest_completed_analysis(self, ticket_id: UUID) -> AIAnalysis | None:
        return cast(
            AIAnalysis | None,
            await self.db.scalar(
                select(AIAnalysis)
                .where(
                    AIAnalysis.ticket_id == ticket_id,
                    AIAnalysis.status == AnalysisStatus.COMPLETED,
                )
                .order_by(AIAnalysis.created_at.desc(), AIAnalysis.id.desc())
                .limit(1)
            ),
        )

    async def active(self, ticket_id: UUID) -> Investigation | None:
        return cast(
            Investigation | None,
            await self.db.scalar(
                select(Investigation).where(
                    Investigation.ticket_id == ticket_id,
                    Investigation.status.in_(
                        [InvestigationStatus.QUEUED, InvestigationStatus.RUNNING]
                    ),
                )
            ),
        )
