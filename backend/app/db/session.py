from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.config import get_settings


def create_engine() -> AsyncEngine:
    return create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
    )


engine = create_engine()


async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        yield connection
