from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status

from app.api.dependencies import CsrfAuth, CurrentAuth, DbSession
from app.schemas.investigations import InvestigationAccepted, InvestigationResponse
from app.services.investigations import (
    InvestigationService,
    investigation_response,
    run_investigation_job,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: UUID, auth: CurrentAuth, db: DbSession
) -> InvestigationResponse:
    del auth
    return investigation_response(await InvestigationService(db).get(investigation_id))


@router.post(
    "/{investigation_id}/retry",
    response_model=InvestigationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_investigation(
    investigation_id: UUID,
    background_tasks: BackgroundTasks,
    auth: CsrfAuth,
    db: DbSession,
) -> InvestigationAccepted:
    investigation = await InvestigationService(db).retry(investigation_id, auth.user)
    background_tasks.add_task(run_investigation_job, investigation.id)
    return InvestigationAccepted(investigation_id=investigation.id, status=investigation.status)
