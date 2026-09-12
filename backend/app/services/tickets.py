from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError, ServiceError
from app.models.domain import AuditLog, Ticket, TicketEvent, User
from app.models.enums import TicketPriority, TicketStatus
from app.repositories.tickets import TicketRepository
from app.schemas.tickets import TicketCreate


class TicketService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = TicketRepository(db)

    async def create(self, payload: TicketCreate, actor: User) -> Ticket:
        ticket = Ticket(
            title=payload.title,
            description=payload.description,
            requester_name=payload.requester_name,
            requester_department=payload.requester_department,
            location=payload.location,
            device=payload.device,
            application=payload.application,
            attachment_metadata=[item.model_dump() for item in payload.attachment_metadata],
            priority_overridden=False,
            created_by=actor,
        )
        self.repository.add(ticket)
        await self.db.flush()
        self._record(ticket, actor, "created", "ticket.create")
        await self._commit_ticket(ticket)
        return ticket

    async def get(self, ticket_id: UUID) -> Ticket:
        ticket = await self.repository.get(ticket_id)
        if ticket is None:
            raise NotFoundError
        return ticket

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
        return await self.repository.search(
            page=page,
            page_size=page_size,
            q=q,
            status=status,
            priority=priority,
            assigned_to_id=assigned_to_id,
        )

    async def update(self, ticket_id: UUID, changes: dict[str, Any], actor: User) -> Ticket:
        ticket = await self.get(ticket_id)
        if ticket.status in {TicketStatus.RESOLVED, TicketStatus.ESCALATED}:
            raise ConflictError
        if changes.get("status") in {TicketStatus.RESOLVED, TicketStatus.ESCALATED}:
            raise ConflictError
        event_data: dict[str, Any] = {}
        for field, value in changes.items():
            setattr(ticket, field, value)
            event_data[field] = value.value if isinstance(value, TicketStatus) else value
        self._record(ticket, actor, "updated", "ticket.update", event_data)
        await self._commit_ticket(ticket)
        return ticket

    async def assign(self, ticket_id: UUID, assignee_id: UUID | None, actor: User) -> Ticket:
        ticket = await self.get(ticket_id)
        if ticket.status in {TicketStatus.RESOLVED, TicketStatus.ESCALATED}:
            raise ConflictError
        assignee = None
        if assignee_id is not None:
            assignee = await self._ensure_active_assignee(assignee_id)
        ticket.assigned_to_id = assignee_id
        ticket.assigned_to = assignee
        self._record(
            ticket,
            actor,
            "assigned",
            "ticket.assign",
            {"assigned_to_id": str(assignee_id) if assignee_id else None},
        )
        await self._commit_ticket(ticket)
        return ticket

    async def events(self, ticket_id: UUID) -> list[TicketEvent]:
        await self.get(ticket_id)
        return await self.repository.events(ticket_id)

    async def override_priority(
        self, ticket_id: UUID, priority: TicketPriority, reason: str, actor: User
    ) -> Ticket:
        ticket = await self.get(ticket_id)
        ticket.priority = priority
        ticket.priority_overridden = True
        ticket.priority_override_reason = reason
        self._record(
            ticket,
            actor,
            "priority_overridden",
            "ticket.priority.override",
            {"priority": priority.value, "reason": reason},
        )
        await self._commit_ticket(ticket)
        return ticket

    async def overview(self) -> tuple[int, int, int, int, list[Ticket]]:
        return await self.repository.overview()

    async def active_users(self) -> list[User]:
        return await self.repository.active_users()

    async def _ensure_active_assignee(self, user_id: UUID) -> User:
        assignee = await self.repository.active_user(user_id)
        if assignee is None:
            raise ServiceError("Assignee must be an active user")
        return assignee

    def _record(
        self,
        ticket: Ticket,
        actor: User,
        event_type: str,
        action: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        safe_data = {
            key: str(value) if isinstance(value, UUID) else value
            for key, value in (data or {}).items()
        }
        self.repository.add(
            TicketEvent(
                ticket_id=ticket.id,
                actor=actor,
                event_type=event_type,
                summary={
                    "created": "Ticket created",
                    "updated": "Ticket details updated",
                    "assigned": "Ticket assigned",
                    "priority_overridden": "Ticket priority manually overridden",
                }[event_type],
                data=safe_data or None,
            )
        )
        self.repository.add(
            AuditLog(
                actor_id=actor.id,
                action=action,
                resource_type="ticket",
                resource_id=ticket.id,
                data=safe_data or None,
            )
        )

    async def _commit_ticket(self, ticket: Ticket) -> None:
        try:
            await self.db.commit()
            await self.db.refresh(ticket)
        except Exception:
            await self.db.rollback()
            raise
