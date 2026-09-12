from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSnapshot(StrictModel):
    evidence_type: Literal[
        "ticket_fact",
        "knowledge_chunk",
        "similar_ticket",
        "system_status",
        "telemetry",
        "log",
        "incident",
        "ticket_history",
    ]
    source_id: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=300)
    excerpt: str = Field(min_length=1, max_length=1200)
    supports: str = Field(min_length=1, max_length=300)
    relevance_score: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GroundedInference(StrictModel):
    probable_root_cause: str = Field(min_length=1, max_length=500)
    inference_key: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")
    recommended_action: str = Field(min_length=1, max_length=1000)
    selected_source_ids: list[str] = Field(max_length=30)
    limitations: list[str] = Field(max_length=20)


class GroundedInferenceInput(StrictModel):
    ticket_id: UUID
    title: str = Field(max_length=200)
    description: str = Field(max_length=1000)
    location: str | None = Field(default=None, max_length=120)
    application: str | None = Field(default=None, max_length=120)
    evidence: list[EvidenceSnapshot] = Field(max_length=50)


class ConfidenceFactor(StrictModel):
    key: str
    label: str
    weight: float
    applied: bool
    source_ids: list[str]


class ConfidenceResult(StrictModel):
    score: float = Field(ge=0.05, le=0.95)
    version: Literal["confidence-v1"] = "confidence-v1"
    factors: list[ConfidenceFactor]
