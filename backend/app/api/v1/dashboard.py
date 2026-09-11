from fastapi import APIRouter

from app.api.dependencies import CurrentAuth, DbSession
from app.schemas.dashboard import DashboardOverview
from app.schemas.tickets import TicketResponse
from app.services.tickets import TicketService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def overview(auth: CurrentAuth, db: DbSession) -> DashboardOverview:
    del auth
    total, open_count, resolved, escalated, recent = await TicketService(db).overview()
    return DashboardOverview(
        total_tickets=total,
        open_tickets=open_count,
        resolved_tickets=resolved,
        escalated_tickets=escalated,
        recent_tickets=[TicketResponse.model_validate(ticket) for ticket in recent],
    )
