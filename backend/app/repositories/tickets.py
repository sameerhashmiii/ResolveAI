from typing import cast
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessments import RootCauseAssessment
from app.models.domain import AIAnalysis, AuditLog, Ticket, TicketEvent, User
from app.models.enums import TicketPriority, TicketStatus
from app.models.operational import Investigation
from app.models.recommendations import Recommendation, SupportResponse


class TicketRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, value: Ticket | TicketEvent | AuditLog) -> None:
        self.db.add(value)

    async def get(self, ticket_id: UUID) -> Ticket | None:
        return await self.db.get(Ticket, ticket_id)

    async def active_user(self, user_id: UUID) -> User | None:
        return cast(
            User | None,
            await self.db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True))),
        )

    async def search(
        self,
        *,
        page: int,
        page_size: int,
        q: str | None,
        status: TicketStatus | None,
        priority: TicketPriority | None,
        assigned_to_id: UUID | None,
    ) -> tuple[list[Ticket], int]:
        filters = []
        if q:
            pattern = f"%{q}%"
            filters.append(
                or_(
                    Ticket.title.ilike(pattern),
                    Ticket.description.ilike(pattern),
                    Ticket.requester_name.ilike(pattern),
                    Ticket.application.ilike(pattern),
                )
            )
        if status is not None:
            filters.append(Ticket.status == status)
        if priority is not None:
            filters.append(Ticket.priority == priority)
        if assigned_to_id is not None:
            filters.append(Ticket.assigned_to_id == assigned_to_id)
        total = await self.db.scalar(select(func.count(Ticket.id)).where(*filters))
        rows = await self.db.scalars(
            select(Ticket)
            .where(*filters)
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), int(total or 0)

    async def events(self, ticket_id: UUID) -> list[TicketEvent]:
        rows = await self.db.scalars(
            select(TicketEvent)
            .where(TicketEvent.ticket_id == ticket_id)
            .order_by(TicketEvent.created_at.asc(), TicketEvent.id.asc())
        )
        return list(rows)

    async def audit(self, ticket_id: UUID) -> list[tuple[AuditLog, User | None]]:
        statement = (
            select(AuditLog, User)
            .outerjoin(User, User.id == AuditLog.actor_id)
            .where(
                or_(
                    (AuditLog.resource_type == "ticket")
                    & (AuditLog.resource_id == ticket_id),
                    (AuditLog.resource_type == "ticket.analysis")
                    & AuditLog.resource_id.in_(
                        select(AIAnalysis.id).where(AIAnalysis.ticket_id == ticket_id)
                    ),
                    (AuditLog.resource_type == "ticket.investigation")
                    & AuditLog.resource_id.in_(
                        select(Investigation.id).where(Investigation.ticket_id == ticket_id)
                    ),
                    (AuditLog.resource_type == "ticket.root_cause_assessment")
                    & AuditLog.resource_id.in_(
                        select(RootCauseAssessment.id).where(
                            RootCauseAssessment.ticket_id == ticket_id
                        )
                    ),
                    (AuditLog.resource_type == "ticket.recommendation")
                    & AuditLog.resource_id.in_(
                        select(Recommendation.id).where(Recommendation.ticket_id == ticket_id)
                    ),
                    (AuditLog.resource_type == "ticket.support_response")
                    & AuditLog.resource_id.in_(
                        select(SupportResponse.id).where(SupportResponse.ticket_id == ticket_id)
                    ),
                )
            )
            .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        )
        rows = await self.db.execute(statement)
        return [(row[0], row[1]) for row in rows.all()]

    async def overview(self) -> tuple[int, int, int, int, list[Ticket]]:
        result = await self.db.execute(
            select(
                func.count(Ticket.id),
                func.count(Ticket.id).filter(
                    Ticket.status.in_([TicketStatus.NEW, TicketStatus.IN_PROGRESS])
                ),
                func.count(Ticket.id).filter(Ticket.status == TicketStatus.RESOLVED),
                func.count(Ticket.id).filter(Ticket.status == TicketStatus.ESCALATED),
            )
        )
        total, open_count, resolved, escalated = result.one()
        recent = await self.db.scalars(
            select(Ticket).order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(5)
        )
        return int(total), int(open_count), int(resolved), int(escalated), list(recent)

    async def active_users(self) -> list[User]:
        rows = await self.db.scalars(
            select(User).where(User.is_active.is_(True)).order_by(User.name.asc())
        )
        return list(rows)
