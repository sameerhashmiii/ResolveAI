from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneratedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=20, max_length=5000)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 20:
            raise ValueError("body must contain at least 20 characters")
        return value


class ResponseGenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: UUID
    requester_name: str = Field(max_length=120)
    title: str = Field(max_length=200)
    description: str = Field(max_length=1000)
    probable_root_cause: str = Field(max_length=500)
    recommendation: str = Field(max_length=1000)
    limitations: list[str] = Field(max_length=20)
    requires_escalation: bool
