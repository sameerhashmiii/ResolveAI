from fastapi import APIRouter, Response

from app.api.dependencies import AnalystAuth, DbSession, ManagerAuth
from app.schemas.analytics import AIPerformanceResponse, AnalyticsOverview
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def overview(auth: AnalystAuth, db: DbSession, response: Response) -> AnalyticsOverview:
    del auth
    response.headers["Cache-Control"] = "no-store"
    return await AnalyticsService(db).overview()


@router.get("/ai-performance", response_model=AIPerformanceResponse)
async def ai_performance(
    auth: ManagerAuth, db: DbSession, response: Response
) -> AIPerformanceResponse:
    del auth
    response.headers["Cache-Control"] = "no-store"
    return await AnalyticsService(db).ai_performance()
