from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import AuditLog, Session, User
from app.models.enums import Role


class AuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        return cast(User | None, await self.db.scalar(select(User).where(User.email == email)))

    async def get_demo_analyst(self) -> User | None:
        return cast(
            User | None,
            await self.db.scalar(
                select(User).where(
                    User.role == Role.SUPPORT_ANALYST,
                    User.is_demo.is_(True),
                    User.is_active.is_(True),
                )
            ),
        )

    async def get_active_session(self, token_hash: str) -> Session | None:
        return cast(
            Session | None,
            await self.db.scalar(
                select(Session).where(
                    Session.token_hash == token_hash,
                    Session.revoked_at.is_(None),
                    Session.expires_at > func.now(),
                )
            ),
        )

    def add_session(self, session: Session) -> None:
        self.db.add(session)

    def add_audit(self, audit: AuditLog) -> None:
        self.db.add(audit)
