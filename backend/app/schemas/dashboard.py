from pydantic import BaseModel

from app.schemas.tickets import TicketResponse


class DashboardOverview(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    escalated_tickets: int
    recent_tickets: list[TicketResponse]
