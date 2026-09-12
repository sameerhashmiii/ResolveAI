from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status

from app.api.dependencies import CsrfAuth, CurrentAuth, DbSession
from app.schemas.analyses import AnalysisAccepted, AnalysisResponse
from app.services.analyses import AnalysisService, analysis_response, run_analysis_job

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: UUID, auth: CurrentAuth, db: DbSession
) -> AnalysisResponse:
    del auth
    return analysis_response(await AnalysisService(db).get(analysis_id))


@router.post(
    "/{analysis_id}/retry", response_model=AnalysisAccepted, status_code=status.HTTP_202_ACCEPTED
)
async def retry_analysis(
    analysis_id: UUID,
    background_tasks: BackgroundTasks,
    auth: CsrfAuth,
    db: DbSession,
) -> AnalysisAccepted:
    analysis = await AnalysisService(db).retry(analysis_id, auth.user)
    background_tasks.add_task(run_analysis_job, analysis.id)
    return AnalysisAccepted(analysis_id=analysis.id, status=analysis.status)
