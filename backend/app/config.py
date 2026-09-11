from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RESOLVEAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ResolveAI"
    app_version: str = "0.3.0"
    environment: str = "production"
    log_level: str = "INFO"
    database_url: str = Field(
        description="SQLAlchemy PostgreSQL URL using the postgresql+asyncpg driver"
    )
    session_cookie_name: str = "resolveai_session"
    session_cookie_secure: bool = True
    session_expiry_hours: int = Field(default=8, ge=1, le=720)


@lru_cache
def get_settings() -> Settings:
    return Settings()
