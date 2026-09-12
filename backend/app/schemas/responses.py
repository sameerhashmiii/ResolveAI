from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ResponseGeneratedBy, SupportResponseStatus


class SupportResponseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    assessment_id: UUID
    recommendation_id: UUID
    generated_by: ResponseGeneratedBy
    provider: str
    model: str | None
    mode: Literal["local_demo", "hosted"]
    draft_body: str
    final_body: str | None
    status: SupportResponseStatus
    created_by_id: UUID
    approved_by_id: UUID | None
    rejected_by_id: UUID | None
    rejection_reason: str | None
    approved_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime
    updated_at: datetime
    approval_semantics: Literal["approval_only_not_sent"] = "approval_only_not_sent"


class ResponseEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_body: str = Field(min_length=20, max_length=5000)

    @field_validator("draft_body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 20:
            raise ValueError("draft_body must contain at least 20 characters")
        return value


class ResponseRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("reason must contain at least 5 characters")
        return value
