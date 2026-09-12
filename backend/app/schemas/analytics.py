from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MetricProvenance(BaseModel):
    synthetic: bool
    data_source: str
    methodology: str
    sample_count: int = Field(ge=0)
    window_start: datetime | None
    window_end: datetime | None
    dataset_version: str | None
    workflow_versions: list[str]


class TicketCountMetric(BaseModel):
    total_tickets: int = Field(ge=0)
    open_tickets: int = Field(ge=0)
    resolved_tickets: int = Field(ge=0)
    escalated_tickets: int = Field(ge=0)
    resolution_rate: float = Field(ge=0, le=1)
    sample_count: int = Field(ge=0)
    provenance: MetricProvenance


class WorkflowMetric(BaseModel):
    name: Literal["analysis", "investigation", "assessment"]
    workflow_version: str
    total: int = Field(ge=0)
    completed: int = Field(ge=0)
    failed: int = Field(ge=0)
    completion_rate: float = Field(ge=0, le=1)
    failure_rate: float = Field(ge=0, le=1)
    median_duration_ms: float = Field(ge=0)
    provenance: MetricProvenance


class AnalyticsOverview(BaseModel):
    synthetic: bool
    source: str
    methodology: str
    measured_at: datetime
    dataset_version: str
    tickets: TicketCountMetric
    workflows: list[WorkflowMetric]


class EvaluationProvenance(BaseModel):
    synthetic: bool
    data_source: str
    methodology: str
    sample_count: int = Field(ge=0)
    window_start: datetime | None
    window_end: datetime | None
    dataset_version: str
    dataset_checksum: str
    workflow_versions: list[str]
    runner_version: str
    provider: str
    model: str | None


class EvaluationRunResponse(BaseModel):
    id: str
    dataset_version: str
    dataset_checksum: str
    runner_version: str
    workflow_version: str
    provider: str
    model: str | None
    sample_count: int = Field(ge=0)
    metrics: dict[str, Any]
    methodology: dict[str, Any]
    completed_at: datetime
    provenance: EvaluationProvenance


class AIPerformanceResponse(BaseModel):
    synthetic: bool
    source: str
    methodology: str
    latest_run: EvaluationRunResponse | None
