from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies import CsrfAuth, CurrentAuth, DbSession, enforce_auth_rate_limit
from app.config import Settings, get_settings
from app.schemas.auth import AuthResponse, LoginRequest, UserResponse
from app.services.auth import AuthService, CreatedSession

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, created: CreatedSession, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=created.token,
        max_age=settings.session_expiry_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
) -> AuthResponse:
    await enforce_auth_rate_limit(request)
    created = await AuthService(db, settings).login(payload.email, payload.password)
    _set_cookie(response, created, settings)
    return AuthResponse(
        user=UserResponse.model_validate(created.user), csrf_token=created.csrf_token
    )


@router.post("/demo", response_model=AuthResponse)
async def demo(
    response: Response,
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
) -> AuthResponse:
    await enforce_auth_rate_limit(request)
    created = await AuthService(db, settings).demo()
    _set_cookie(response, created, settings)
    return AuthResponse(
        user=UserResponse.model_validate(created.user), csrf_token=created.csrf_token
    )


@router.get("/me", response_model=AuthResponse)
async def me(auth: CurrentAuth) -> AuthResponse:
    return AuthResponse(
        user=UserResponse.model_validate(auth.user), csrf_token=auth.session.csrf_token
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    auth: CsrfAuth,
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    await AuthService(db, settings).logout(auth.session)
    response.delete_cookie(
        settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
