import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.domain import Session, User
from app.models.enums import Role, role_allows
from app.repositories.auth import AuthRepository
from app.security import hash_session_token

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: Session


async def get_current_auth(
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
) -> AuthContext:
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    session = await AuthRepository(db).get_active_session(hash_session_token(session_token))
    if session is None or not session.user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return AuthContext(user=session.user, session=session)


CurrentAuth = Annotated[AuthContext, Depends(get_current_auth)]


async def require_analyst(auth: CurrentAuth) -> AuthContext:
    if not role_allows(auth.user.role, Role.SUPPORT_ANALYST):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return auth


async def require_manager(auth: CurrentAuth) -> AuthContext:
    if not role_allows(auth.user.role, Role.MANAGER):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return auth


async def require_administrator(auth: CurrentAuth) -> AuthContext:
    if not role_allows(auth.user.role, Role.ADMINISTRATOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return auth


AnalystAuth = Annotated[AuthContext, Depends(require_analyst)]
ManagerAuth = Annotated[AuthContext, Depends(require_manager)]
AdministratorAuth = Annotated[AuthContext, Depends(require_administrator)]


async def require_csrf(
    auth: CurrentAuth,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthContext:
    if csrf_token is None or not secrets.compare_digest(csrf_token, auth.session.csrf_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid CSRF token")
    return auth


CsrfAuth = Annotated[AuthContext, Depends(require_csrf)]


async def require_manager_csrf(auth: CsrfAuth) -> AuthContext:
    if not role_allows(auth.user.role, Role.MANAGER):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return auth


ManagerCsrfAuth = Annotated[AuthContext, Depends(require_manager_csrf)]


def require_role(required: Role) -> object:
    async def dependency(auth: CurrentAuth) -> AuthContext:
        if not role_allows(auth.user.role, required):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        return auth

    return Depends(dependency)
