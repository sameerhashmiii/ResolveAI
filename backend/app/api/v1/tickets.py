from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response, status

from app.api.dependencies import (
    CsrfAuth,
    CurrentAuth,
    DbSession,
    ManagerAuth,
    enforce_workflow_rate_limit,
)
from app.models.enums import TicketPriority, TicketStatus
from app.schemas.analyses import (
    AnalysisAccepted,
    AnalysisResponse,
    PriorityOverrideRequest,
)
from app.schemas.assessments import AssessmentAccepted, AssessmentResponse
from app.schemas.investigations import (
    InvestigationAccepted,
    InvestigationResponse,
    SimilarTicketResponse,
)
from app.schemas.tickets import (
    AssignTicketRequest,
    TicketAuditRecordResponse,
    TicketCreate,
    TicketEventResponse,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.services.analyses import AnalysisService, analysis_response, run_analysis_job
from app.services.assessments import AssessmentService, assessment_response, run_assessment_job
from app.services.investigations import (
    InvestigationService,
    investigation_response,
    run_investigation_job,
)
from app.services.similar_tickets import SimilarTicketService
from app.services.tickets import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post(
    "/{ticket_id}/assessments",
    response_model=AssessmentAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_assessment(
    ticket_id: UUID,
    background_tasks: BackgroundTasks,
    auth: CsrfAuth,
    db: DbSession,
    request: Request,
) -> AssessmentAccepted:
    await enforce_workflow_rate_limit(request, auth, "/api/v1/tickets/{ticket_id}/assessments")
    assessment = await AssessmentService(db).request(ticket_id, auth.user)
    background_tasks.add_task(run_assessment_job, assessment.id)
    return AssessmentAccepted(assessment_id=assessment.id, status=assessment.status)


@router.get("/{ticket_id}/assessments/latest", response_model=AssessmentResponse | None)
async def latest_assessment(
    ticket_id: UUID, auth: CurrentAuth, db: DbSession
) -> AssessmentResponse | None:
    del auth
    service = AssessmentService(db)
    assessment = await service.latest(ticket_id)
    return assessment_response(assessment, service.settings) if assessment is not None else None


@router.get("/{ticket_id}/similar", response_model=list[SimilarTicketResponse])
async def similar_tickets(
    ticket_id: UUID,
    auth: CurrentAuth,
    db: DbSession,
    top_k: Annotated[int, Query(ge=1, le=10)] = 5,
) -> list[SimilarTicketResponse]:
    del auth
    ticket = await TicketService(db).get(ticket_id)
    return await SimilarTicketService(db).search(ticket.title, ticket.description, top_k)


@router.post(
    "/{ticket_id}/investigations",
    response_model=InvestigationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_investigation(
    ticket_id: UUID,
    background_tasks: BackgroundTasks,
    auth: CsrfAuth,
    db: DbSession,
    request: Request,
) -> InvestigationAccepted:
    await enforce_workflow_rate_limit(request, auth, "/api/v1/tickets/{ticket_id}/investigations")
    investigation = await InvestigationService(db).request(ticket_id, auth.user)
    background_tasks.add_task(run_investigation_job, investigation.id)
    return InvestigationAccepted(investigation_id=investigation.id, status=investigation.status)


@router.get("/{ticket_id}/investigations/latest", response_model=InvestigationResponse | None)
async def latest_investigation(
    ticket_id: UUID, auth: CurrentAuth, db: DbSession
) -> InvestigationResponse | None:
    del auth
    investigation = await InvestigationService(db).latest(ticket_id)
    return investigation_response(investigation) if investigation is not None else None


@router.post(
    "/{ticket_id}/analyses",
    response_model=AnalysisAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_analysis(
    ticket_id: UUID,
    background_tasks: BackgroundTasks,
    auth: CsrfAuth,
    db: DbSession,
    request: Request,
) -> AnalysisAccepted:
    await enforce_workflow_rate_limit(request, auth, "/api/v1/tickets/{ticket_id}/analyses")
    analysis = await AnalysisService(db).request(ticket_id, auth.user)
    background_tasks.add_task(run_analysis_job, analysis.id)
    return AnalysisAccepted(analysis_id=analysis.id, status=analysis.status)


@router.get("/{ticket_id}/analyses/latest", response_model=AnalysisResponse | None)
async def latest_analysis(
    ticket_id: UUID, auth: CurrentAuth, db: DbSession
) -> AnalysisResponse | None:
    del auth
    analysis = await AnalysisService(db).latest(ticket_id)
    return analysis_response(analysis) if analysis is not None else None


@router.post("/{ticket_id}/priority-override", response_model=TicketResponse)
async def override_priority(
    ticket_id: UUID,
    payload: PriorityOverrideRequest,
    auth: CsrfAuth,
    db: DbSession,
) -> TicketResponse:
    ticket = await TicketService(db).override_priority(
        ticket_id, payload.priority, payload.reason.strip(), auth.user
    )
    return TicketResponse.model_validate(ticket)


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


@router.get("/{ticket_id}/audit", response_model=list[TicketAuditRecordResponse])
async def ticket_audit(
    ticket_id: UUID, auth: ManagerAuth, db: DbSession, response: Response
) -> list[TicketAuditRecordResponse]:
    del auth
    response.headers["Cache-Control"] = "no-store"
    return await TicketService(db).audit(ticket_id)
