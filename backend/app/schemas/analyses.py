from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ai.schemas import Category, ExtractedEntities, PriorityFactors
from app.models.enums import AnalysisStatus, TicketPriority


class AnalysisAccepted(BaseModel):
    analysis_id: UUID
    status: AnalysisStatus


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    requested_by_id: UUID
    workflow_version: str
    provider: str
    model: str | None
    mode: str
    status: AnalysisStatus
    category: Category | None
    category_confidence: float | None = Field(default=None, ge=0, le=1)
    recommended_priority: TicketPriority | None
    validated_priority: TicketPriority | None
    entities: ExtractedEntities | None
    priority_factors: PriorityFactors | None
    requires_manual_review: bool
    error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    created_at: datetime


class PriorityOverrideRequest(BaseModel):
    priority: TicketPriority
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("reason must contain at least 5 characters")
        return value
