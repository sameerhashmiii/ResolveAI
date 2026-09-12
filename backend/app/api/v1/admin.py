from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import AdministratorAuth, DbSession
from app.config import Settings, get_settings
from app.schemas.admin import AdminHealthResponse
from app.services.admin import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health", response_model=AdminHealthResponse)
async def health(
    auth: AdministratorAuth,
    db: DbSession,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminHealthResponse:
    del auth
    response.headers["Cache-Control"] = "no-store"
    return await AdminService(db, settings).health()
