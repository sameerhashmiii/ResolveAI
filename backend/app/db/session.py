from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def create_engine() -> AsyncEngine:
    return create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
    )


engine = create_engine()
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        yield connection


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
