from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessments import AssessmentEvidence, RootCauseAssessment
from app.models.domain import AIAnalysis, AuditLog, Ticket, TicketEvent
from app.models.enums import InvestigationStatus, RootCauseStatus
from app.models.operational import Investigation
from app.models.recommendations import Recommendation


class AssessmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(
        self,
        value: RootCauseAssessment | AssessmentEvidence | Recommendation | TicketEvent | AuditLog,
    ) -> None:
        self.db.add(value)

    async def ticket(self, ticket_id: UUID) -> Ticket | None:
        return cast(Ticket | None, await self.db.get(Ticket, ticket_id))

    async def analysis(self, analysis_id: UUID | None) -> AIAnalysis | None:
        if analysis_id is None:
            return None
        return cast(AIAnalysis | None, await self.db.get(AIAnalysis, analysis_id))

    async def get(self, assessment_id: UUID) -> RootCauseAssessment | None:
        return cast(
            RootCauseAssessment | None,
            await self.db.scalar(
                select(RootCauseAssessment)
                .options(
                    selectinload(RootCauseAssessment.evidence),
                    selectinload(RootCauseAssessment.investigation).selectinload(
                        Investigation.steps
                    ),
                )
                .where(RootCauseAssessment.id == assessment_id)
            ),
        )

    async def latest(self, ticket_id: UUID) -> RootCauseAssessment | None:
        return cast(
            RootCauseAssessment | None,
            await self.db.scalar(
                select(RootCauseAssessment)
                .options(selectinload(RootCauseAssessment.evidence))
                .where(RootCauseAssessment.ticket_id == ticket_id)
                .order_by(RootCauseAssessment.created_at.desc(), RootCauseAssessment.id.desc())
                .limit(1)
            ),
        )

    async def latest_completed_investigation(self, ticket_id: UUID) -> Investigation | None:
        return cast(
            Investigation | None,
            await self.db.scalar(
                select(Investigation)
                .options(selectinload(Investigation.steps))
                .where(
                    Investigation.ticket_id == ticket_id,
                    Investigation.status == InvestigationStatus.COMPLETED,
                )
                .order_by(Investigation.created_at.desc(), Investigation.id.desc())
                .limit(1)
            ),
        )

    async def for_investigation(self, investigation_id: UUID) -> RootCauseAssessment | None:
        return cast(
            RootCauseAssessment | None,
            await self.db.scalar(
                select(RootCauseAssessment).where(
                    RootCauseAssessment.investigation_id == investigation_id
                )
            ),
        )

    async def active(self, ticket_id: UUID) -> RootCauseAssessment | None:
        return cast(
            RootCauseAssessment | None,
            await self.db.scalar(
                select(RootCauseAssessment).where(
                    RootCauseAssessment.ticket_id == ticket_id,
                    RootCauseAssessment.status.in_(
                        [RootCauseStatus.QUEUED, RootCauseStatus.RUNNING]
                    ),
                )
            ),
        )
