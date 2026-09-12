from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import RecommendationActionType, RecommendationStatus


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    assessment_id: UUID
    title: str
    original_instructions: str
    instructions: str
    action_type: RecommendationActionType
    requires_approval: bool
    status: RecommendationStatus
    decided_by_id: UUID | None
    decision_reason: str | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RecommendationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject", "modify"]
    reason: str = Field(min_length=5, max_length=500)
    modified_instructions: str | None = Field(default=None, min_length=10, max_length=1000)

    @field_validator("reason", "modified_instructions")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def modification_matches_decision(self) -> "RecommendationDecision":
        if self.decision == "modify" and self.modified_instructions is None:
            raise ValueError("modified_instructions is required for modify")
        if self.decision != "modify" and self.modified_instructions is not None:
            raise ValueError("modified_instructions is only allowed for modify")
        if len(self.reason) < 5:
            raise ValueError("reason must contain at least 5 characters")
        if self.modified_instructions is not None and len(self.modified_instructions) < 10:
            raise ValueError("modified_instructions must contain at least 10 characters")
        return self
