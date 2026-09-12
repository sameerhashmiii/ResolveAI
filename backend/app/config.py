import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
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
    app_version: str = "0.11.0"
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
    auth_rate_limit: int = Field(default=10, ge=1, le=10_000)
    auth_rate_window_seconds: int = Field(default=60, ge=1, le=86_400)
    workflow_rate_limit: int = Field(default=20, ge=1, le=10_000)
    workflow_rate_window_seconds: int = Field(default=60, ge=1, le=86_400)
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "test", "backend"]
    )

    @field_validator("trusted_hosts")
    @classmethod
    def validate_trusted_hosts(cls, hosts: list[str]) -> list[str]:
        if not hosts:
            raise ValueError("trusted_hosts must not be empty")
        for host in hosts:
            candidate = host.removeprefix("*.")
            if (
                not candidate
                or host == "*"
                or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", candidate)
                or ".." in candidate
                or any(
                    label.startswith("-") or label.endswith("-")
                    for label in candidate.split(".")
                )
            ):
                raise ValueError("trusted_hosts contains an invalid hostname")
        return hosts


@lru_cache
def get_settings() -> Settings:
    return Settings()
