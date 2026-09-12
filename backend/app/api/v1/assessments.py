from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, status

from app.api.dependencies import CsrfAuth, CurrentAuth, DbSession, enforce_workflow_rate_limit
from app.schemas.assessments import AssessmentAccepted, AssessmentExplanation, AssessmentResponse
from app.services.assessments import AssessmentService, assessment_response, run_assessment_job

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: UUID, auth: CurrentAuth, db: DbSession
) -> AssessmentResponse:
    del auth
    service = AssessmentService(db)
    return assessment_response(await service.get(assessment_id), service.settings)


@router.get("/{assessment_id}/explanation", response_model=AssessmentExplanation)
async def explain_assessment(
    assessment_id: UUID, auth: CurrentAuth, db: DbSession
) -> AssessmentExplanation:
    del auth
    return await AssessmentService(db).explanation(assessment_id)


@router.post(
    "/{assessment_id}/retry",
    response_model=AssessmentAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_assessment(
    assessment_id: UUID,
    background_tasks: BackgroundTasks,
    auth: CsrfAuth,
    db: DbSession,
    request: Request,
) -> AssessmentAccepted:
    await enforce_workflow_rate_limit(request, auth, "/api/v1/assessments/{assessment_id}/retry")
    assessment = await AssessmentService(db).retry(assessment_id, auth.user)
    background_tasks.add_task(run_assessment_job, assessment.id)
    return AssessmentAccepted(assessment_id=assessment.id, status=assessment.status)
