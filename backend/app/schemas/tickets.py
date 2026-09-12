from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Role, TicketPriority, TicketStatus
from app.schemas.auth import UserResponse


class AttachmentMetadata(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size: int = Field(ge=0, le=10_000_000)


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20_000)
    requester_name: str = Field(min_length=1, max_length=120)
    requester_department: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    device: str | None = Field(default=None, max_length=120)
    application: str | None = Field(default=None, max_length=120)
    attachment_metadata: list[AttachmentMetadata] = Field(default_factory=list, max_length=10)

    @field_validator("title", "description", "requester_name")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("requester_department", "location", "device", "application")
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=20_000)
    status: Literal[TicketStatus.NEW, TicketStatus.IN_PROGRESS] | None = None

    @field_validator("title", "description")
    @classmethod
    def non_blank(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("status")
    @classmethod
    def status_not_null(cls, value: TicketStatus | None) -> TicketStatus:
        if value is None:
            raise ValueError("must not be null")
        return value


class AssignTicketRequest(BaseModel):
    assigned_to_id: UUID | None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_number: str
    title: str
    description: str
    requester_name: str
    requester_department: str | None
    location: str | None
    device: str | None
    application: str | None
    attachment_metadata: list[dict[str, Any]] | None
    category: str | None
    priority: TicketPriority | None
    priority_overridden: bool
    priority_override_reason: str | None
    status: TicketStatus
    resolved_at: datetime | None
    escalated_at: datetime | None
    escalation_destination: str | None
    escalation_reason: str | None
    resolution_summary: str | None
    assigned_to: UserResponse | None
    created_by: UserResponse
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    page: int
    page_size: int
    total: int
    has_next: bool


class TicketEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    summary: str
    actor: UserResponse | None
    created_at: datetime


class AuditActorResponse(BaseModel):
    display_name: str
    role: Role


class TicketAuditRecordResponse(BaseModel):
    action: str
    resource_type: str
    resource_id: UUID | None
    metadata: dict[str, str | int | float | bool | None]
    actor: AuditActorResponse | None
    created_at: datetime
