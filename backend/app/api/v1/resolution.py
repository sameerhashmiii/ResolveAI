from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import CsrfAuth, CurrentAuth, DbSession
from app.schemas.outcomes import EscalateTicketRequest, ResolveTicketRequest
from app.schemas.recommendations import RecommendationDecision, RecommendationResponse
from app.schemas.responses import ResponseEdit, ResponseRejection, SupportResponseView
from app.schemas.tickets import TicketResponse
from app.services.outcomes import OutcomeService
from app.services.recommendations import RecommendationService
from app.services.responses import ResponseService

router = APIRouter(tags=["resolution"])


@router.get(
    "/tickets/{ticket_id}/recommendations/latest",
    response_model=RecommendationResponse | None,
)
async def latest_recommendation(
    ticket_id: UUID, auth: CurrentAuth, db: DbSession
) -> RecommendationResponse | None:
    del auth
    value = await RecommendationService(db).latest(ticket_id)
    return RecommendationResponse.model_validate(value) if value is not None else None


@router.post(
    "/recommendations/{recommendation_id}/decision",
    response_model=RecommendationResponse,
)
async def decide_recommendation(
    recommendation_id: UUID,
    payload: RecommendationDecision,
    auth: CsrfAuth,
    db: DbSession,
) -> RecommendationResponse:
    value = await RecommendationService(db).decide(recommendation_id, payload, auth.user)
    return RecommendationResponse.model_validate(value)


@router.post("/tickets/{ticket_id}/responses", response_model=SupportResponseView)
async def generate_response(
    ticket_id: UUID, auth: CsrfAuth, db: DbSession
) -> SupportResponseView:
    value = await ResponseService(db).generate(ticket_id, auth.user)
    return SupportResponseView.model_validate(value)


@router.get("/tickets/{ticket_id}/responses/latest", response_model=SupportResponseView | None)
async def latest_response(
    ticket_id: UUID, auth: CurrentAuth, db: DbSession
) -> SupportResponseView | None:
    del auth
    value = await ResponseService(db).latest(ticket_id)
    return SupportResponseView.model_validate(value) if value is not None else None


@router.patch("/responses/{response_id}", response_model=SupportResponseView)
async def edit_response(
    response_id: UUID, payload: ResponseEdit, auth: CsrfAuth, db: DbSession
) -> SupportResponseView:
    value = await ResponseService(db).edit(response_id, payload.draft_body, auth.user)
    return SupportResponseView.model_validate(value)


@router.post("/responses/{response_id}/approve", response_model=SupportResponseView)
async def approve_response(
    response_id: UUID, auth: CsrfAuth, db: DbSession
) -> SupportResponseView:
    value = await ResponseService(db).approve(response_id, auth.user)
    return SupportResponseView.model_validate(value)


@router.post("/responses/{response_id}/reject", response_model=SupportResponseView)
async def reject_response(
    response_id: UUID,
    payload: ResponseRejection,
    auth: CsrfAuth,
    db: DbSession,
) -> SupportResponseView:
    value = await ResponseService(db).reject(response_id, payload.reason, auth.user)
    return SupportResponseView.model_validate(value)


@router.post("/tickets/{ticket_id}/resolve", response_model=TicketResponse)
async def resolve_ticket(
    ticket_id: UUID, payload: ResolveTicketRequest, auth: CsrfAuth, db: DbSession
) -> TicketResponse:
    ticket = await OutcomeService(db).resolve(
        ticket_id, payload.response_id, payload.resolution_summary, auth.user
    )
    return TicketResponse.model_validate(ticket)


@router.post("/tickets/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(
    ticket_id: UUID, payload: EscalateTicketRequest, auth: CsrfAuth, db: DbSession
) -> TicketResponse:
    ticket = await OutcomeService(db).escalate(
        ticket_id, payload.destination, payload.reason, auth.user
    )
    return TicketResponse.model_validate(ticket)
