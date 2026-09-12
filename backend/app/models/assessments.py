from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RootCauseStatus
from app.models.operational import Investigation

root_cause_status_enum = Enum(
    RootCauseStatus,
    name="root_cause_status",
    values_callable=lambda enum: [item.value for item in enum],
)


class RootCauseAssessment(Base):
    __tablename__ = "root_cause_assessments"
    __table_args__ = (
        Index("ix_root_cause_assessments_ticket_created", "ticket_id", "created_at"),
        Index("uq_root_cause_assessments_investigation", "investigation_id", unique=True),
        Index(
            "uq_root_cause_assessments_active_ticket",
            "ticket_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
        CheckConstraint("mode IN ('local_demo', 'hosted')", name="ck_root_cause_mode"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_root_cause_confidence",
        ),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_root_cause_duration"),
        CheckConstraint(
            "status != 'completed' OR "
            "(probable_root_cause IS NOT NULL AND recommendation IS NOT NULL)",
            name="ck_root_cause_completed_fields",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"))
    investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_analyses.id", ondelete="SET NULL")
    )
    requested_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[RootCauseStatus] = mapped_column(root_cause_status_enum, nullable=False)
    probable_root_cause: Mapped[str | None] = mapped_column(String(500))
    inference_key: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float | None] = mapped_column(Float)
    confidence_version: Mapped[str] = mapped_column(String(30), nullable=False)
    recommendation: Mapped[str | None] = mapped_column(String(1000))
    requires_escalation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    limitations: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence_factors: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    error_code: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    investigation: Mapped[Investigation] = relationship(lazy="selectin")
    evidence: Mapped[list["AssessmentEvidence"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentEvidence.display_order",
        lazy="selectin",
    )


class AssessmentEvidence(Base):
    __tablename__ = "assessment_evidence"
    __table_args__ = (
        Index("uq_assessment_evidence_source", "assessment_id", "source_id", unique=True),
        CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_assessment_evidence_relevance",
        ),
        CheckConstraint("length(excerpt) <= 1200", name="ck_assessment_evidence_excerpt"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("root_cause_assessments.id", ondelete="CASCADE"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    supports: Mapped[str] = mapped_column(String(300), nullable=False)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assessment: Mapped[RootCauseAssessment] = relationship(back_populates="evidence")
