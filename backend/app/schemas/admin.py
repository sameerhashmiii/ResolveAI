from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    name: str
    status: Literal["up", "down"]
    latency_ms: float = Field(ge=0)


class AdminHealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    environment: str
    version: str
    checked_at: datetime
    components: list[ComponentHealth]
