from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CsrfAuth, CurrentAuth, DbSession
from app.models.enums import TicketPriority, TicketStatus
from app.schemas.tickets import (
    AssignTicketRequest,
    TicketCreate,
    TicketEventResponse,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.services.tickets import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreate, auth: CsrfAuth, db: DbSession) -> TicketResponse:
    ticket = await TicketService(db).create(payload, auth.user)
    return TicketResponse.model_validate(ticket)


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    auth: CurrentAuth,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    status_filter: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: TicketPriority | None = None,
    assigned_to_id: UUID | None = None,
) -> TicketListResponse:
    del auth
    items, total = await TicketService(db).search(
        page=page,
        page_size=page_size,
        q=q,
        status=status_filter,
        priority=priority,
        assigned_to_id=assigned_to_id,
    )
    return TicketListResponse(
        items=[TicketResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        has_next=page * page_size < total,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: UUID, auth: CurrentAuth, db: DbSession) -> TicketResponse:
    del auth
    return TicketResponse.model_validate(await TicketService(db).get(ticket_id))


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: UUID, payload: TicketUpdate, auth: CsrfAuth, db: DbSession
) -> TicketResponse:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "At least one field is required")
    ticket = await TicketService(db).update(ticket_id, changes, auth.user)
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: UUID, payload: AssignTicketRequest, auth: CsrfAuth, db: DbSession
) -> TicketResponse:
    ticket = await TicketService(db).assign(ticket_id, payload.assigned_to_id, auth.user)
    return TicketResponse.model_validate(ticket)


@router.get("/{ticket_id}/events", response_model=list[TicketEventResponse])
async def ticket_events(
    ticket_id: UUID, auth: CurrentAuth, db: DbSession
) -> list[TicketEventResponse]:
    del auth
    return [
        TicketEventResponse.model_validate(event)
        for event in await TicketService(db).events(ticket_id)
    ]
