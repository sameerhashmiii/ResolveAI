from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Ticket, User
from app.models.enums import Role, TicketStatus
from app.services.tickets import TicketService


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _: object) -> None:
        pass

    async def rollback(self) -> None:
        pass


class FakeTicketRepository:
    def __init__(self, ticket: Ticket, assignee: User) -> None:
        self.ticket = ticket
        self.assignee = assignee
        self.added: list[object] = []

    async def get(self, ticket_id: UUID) -> Ticket | None:
        return self.ticket if ticket_id == self.ticket.id else None

    async def active_user(self, user_id: UUID) -> User | None:
        return self.assignee if user_id == self.assignee.id else None

    def add(self, value: object) -> None:
        self.added.append(value)


def make_user(role: Role) -> User:
    return User(
        id=uuid4(),
        name="Test User",
        email=f"{uuid4()}@example.test",
        role=role,
        is_active=True,
        is_demo=False,
    )


def make_ticket(actor: User) -> Ticket:
    now = datetime.now(UTC)
    return Ticket(
        id=uuid4(),
        number=1000,
        title="Issue",
        description="Description",
        requester_name="Requester",
        status=TicketStatus.NEW,
        created_by=actor,
        created_at=now,
        updated_at=now,
    )


async def test_assignment_records_atomic_mutation() -> None:
    analyst = make_user(Role.SUPPORT_ANALYST)
    assignee = make_user(Role.SUPPORT_ANALYST)
    ticket = make_ticket(analyst)
    db = FakeDb()
    service = TicketService(cast(AsyncSession, db))
    repository = FakeTicketRepository(ticket, assignee)
    service.repository = cast(Any, repository)

    result = await service.assign(ticket.id, assignee.id, analyst)

    assert result.assigned_to_id == assignee.id
    assert result.assigned_to == assignee
    assert db.commits == 1
    assert len(repository.added) == 2

    result = await service.assign(ticket.id, None, analyst)
    assert result.assigned_to_id is None
    assert result.assigned_to is None
    assert db.commits == 2
