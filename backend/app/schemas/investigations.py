from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InvestigationStatus, InvestigationStepStatus


class SimilarTicketResponse(BaseModel):
    source_id: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    resolution: str | None
    resolution_time_minutes: int | None
    opened_at: datetime
    similarity: float = Field(ge=0, le=1)
    incident_id: str | None


class ToolResult(BaseModel):
    tool_name: str
    input_summary: dict[str, Any]
    result: dict[str, Any]
    source_ids: list[str]
    source_count: int = Field(ge=0)


class InvestigationStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_key: str
    step_order: int
    label: str
    tool_name: str | None
    status: InvestigationStepStatus
    sanitized_inputs: dict[str, Any]
    result: dict[str, Any] | None
    source_count: int
    duration_ms: int
    created_at: datetime


class InvestigationResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    analysis_id: UUID | None
    requested_by_id: UUID
    workflow_version: str
    status: InvestigationStatus
    reference_time: datetime
    reference_basis: Literal["ticket_created_at", "curated_demo_scenario"]
    simulated_reference: bool
    planned_tools: list[dict[str, Any]]
    limitations: list[str]
    error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    created_at: datetime
    steps: list[InvestigationStepResponse]


class InvestigationAccepted(BaseModel):
    investigation_id: UUID
    status: InvestigationStatus
