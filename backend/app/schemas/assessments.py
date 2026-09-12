from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import InvestigationStepStatus, RootCauseStatus
from app.root_cause.schemas import ConfidenceFactor


class EvidenceResponse(BaseModel):
    id: UUID
    evidence_type: str
    source_id: str
    title: str
    excerpt: str
    supports: str
    relevance_score: float | None
    metadata: dict[str, Any]
    display_order: int


class InferenceResponse(BaseModel):
    kind: Literal["probable"] = "probable"
    summary: str
    key: str | None


class RecommendationResponse(BaseModel):
    kind: Literal["recommendation"] = "recommendation"
    text: str


class ConfidenceResponse(BaseModel):
    score: float | None
    version: str
    factors: list[ConfidenceFactor]
    description: Literal["Deterministic evidence confidence; not measured accuracy"] = (
        "Deterministic evidence confidence; not measured accuracy"
    )


class EscalationResponse(BaseModel):
    required: bool
    threshold: float = Field(ge=0, le=1)
    reason: str


class AssessmentResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    investigation_id: UUID
    analysis_id: UUID | None
    requested_by_id: UUID
    workflow_version: str
    provider: str
    model: str | None
    mode: Literal["local_demo", "hosted"]
    mode_label: str
    status: RootCauseStatus
    observed_evidence: list[EvidenceResponse]
    inference: InferenceResponse | None
    confidence: ConfidenceResponse
    recommendation: RecommendationResponse | None
    limitations: list[str]
    escalation: EscalationResponse
    error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    created_at: datetime


class AssessmentAccepted(BaseModel):
    assessment_id: UUID
    status: RootCauseStatus


class TimelineStep(BaseModel):
    label: str
    status: InvestigationStepStatus
    source_count: int


class AssessmentExplanation(BaseModel):
    assessment: AssessmentResponse
    investigation_timeline: list[TimelineStep]
    supporting_evidence: list[EvidenceResponse]
    confidence_factors: list[ConfidenceFactor]
    reasoning_disclosure: Literal[
        "Auditable evidence and decision factors only; hidden chain-of-thought is not "
        "stored or exposed."
    ] = (
        "Auditable evidence and decision factors only; hidden chain-of-thought is not stored or "
        "exposed."
    )
