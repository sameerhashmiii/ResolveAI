from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResolveTicketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_id: UUID
    resolution_summary: str = Field(min_length=10, max_length=1000)

    @field_validator("resolution_summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("resolution_summary must contain at least 10 characters")
        return value


class EscalateTicketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str = Field(min_length=3, max_length=200)
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("destination", "reason")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()
