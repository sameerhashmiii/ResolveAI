from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_knowledge_data_dir() -> Path:
    container_path = Path("/data/knowledge")
    if container_path.is_dir():
        return container_path
    return Path(__file__).resolve().parents[2] / "data" / "knowledge"


def default_operational_data_dir() -> Path:
    container_path = Path("/data")
    if container_path.is_dir():
        return container_path
    return Path(__file__).resolve().parents[2] / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RESOLVEAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ResolveAI"
    app_version: str = "0.7.0"
    environment: str = "production"
    log_level: str = "INFO"
    database_url: str = Field(
        description="SQLAlchemy PostgreSQL URL using the postgresql+asyncpg driver"
    )
    session_cookie_name: str = "resolveai_session"
    session_cookie_secure: bool = True
    session_expiry_hours: int = Field(default=8, ge=1, le=720)
    ai_mode: Literal["local_demo", "openai_compatible"] = "local_demo"
    ai_timeout_seconds: float = Field(default=20.0, gt=0, le=300)
    ai_confidence_threshold: float = Field(default=0.70, ge=0, le=1)
    llm_base_url: str = Field(default="https://api.openai.com/v1", min_length=1)
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    knowledge_data_dir: Path = Field(default_factory=default_knowledge_data_dir)
    operational_data_dir: Path = Field(default_factory=default_operational_data_dir)
    investigation_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    root_cause_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    root_cause_confidence_threshold: float = Field(default=0.70, ge=0, le=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
