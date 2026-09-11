from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import AuthenticationError, InvalidCredentialsError
from app.models.domain import AuditLog, Session, User
from app.repositories.auth import AuthRepository
from app.security import generate_token, hash_session_token, verify_password


@dataclass(frozen=True)
class CreatedSession:
    user: User
    token: str
    csrf_token: str


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = AuthRepository(db)

    async def login(self, email: str, password: str) -> CreatedSession:
        user = await self.repository.get_user_by_email(email)
        if (
            user is None
            or not user.is_active
            or user.password_hash is None
            or not verify_password(user.password_hash, password)
        ):
            raise InvalidCredentialsError
        return await self._create_session(user, "auth.login")

    async def demo(self) -> CreatedSession:
        user = await self.repository.get_demo_analyst()
        if user is None:
            raise AuthenticationError
        return await self._create_session(user, "auth.demo")

    async def _create_session(self, user: User, action: str) -> CreatedSession:
        token = generate_token()
        csrf_token = generate_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_session_token(token),
            csrf_token=csrf_token,
            expires_at=datetime.now(UTC) + timedelta(hours=self.settings.session_expiry_hours),
        )
        self.repository.add_session(session)
        await self.db.flush()
        self.repository.add_audit(
            AuditLog(
                actor_id=user.id,
                action=action,
                resource_type="session",
                resource_id=session.id,
            )
        )
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return CreatedSession(user=user, token=token, csrf_token=csrf_token)

    async def logout(self, session: Session) -> None:
        session.revoked_at = datetime.now(UTC)
        self.repository.add_audit(
            AuditLog(
                actor_id=session.user_id,
                action="auth.logout",
                resource_type="session",
                resource_id=session.id,
            )
        )
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
