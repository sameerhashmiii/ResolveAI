from fastapi import APIRouter

from app.api.dependencies import CurrentAuth, DbSession
from app.schemas.auth import UserResponse
from app.services.tickets import TicketService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_active_users(auth: CurrentAuth, db: DbSession) -> list[UserResponse]:
    del auth
    return [
        UserResponse.model_validate(user) for user in await TicketService(db).active_users()
    ]
