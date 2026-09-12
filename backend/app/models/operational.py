from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
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
from app.models.domain import AIAnalysis, Ticket, User
from app.models.enums import InvestigationStatus, InvestigationStepStatus

investigation_status_enum = Enum(
    InvestigationStatus,
    name="investigation_status",
    values_callable=lambda enum: [item.value for item in enum],
)
step_status_enum = Enum(
    InvestigationStepStatus,
    name="investigation_step_status",
    values_callable=lambda enum: [item.value for item in enum],
)


class DatasetImport(Base):
    __tablename__ = "dataset_imports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_version: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counts: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SyntheticLocation(Base):
    __tablename__ = "synthetic_locations"
    __table_args__ = (
        Index("ix_synthetic_locations_dataset_name", "dataset_version", "name"),
        Index(
            "uq_synthetic_locations_dataset_source",
            "dataset_version",
            "source_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    network_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)


class SyntheticApplication(Base):
    __tablename__ = "synthetic_applications"
    __table_args__ = (
        CheckConstraint(
            "normal_availability >= 0 AND normal_availability <= 100",
            name="ck_synthetic_app_availability",
        ),
        Index(
            "uq_synthetic_applications_dataset_source",
            "dataset_version",
            "source_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(160), nullable=False)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False)
    environment: Mapped[str] = mapped_column(String(100), nullable=False)
    normal_availability: Mapped[float] = mapped_column(Float, nullable=False)
    dependencies: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)


class HistoricalTicket(Base):
    __tablename__ = "historical_tickets"
    __table_args__ = (
        Index("ix_historical_tickets_dataset_category", "dataset_version", "category"),
        Index("ix_historical_tickets_dataset_priority", "dataset_version", "priority"),
        Index("ix_historical_tickets_opened_at", "opened_at"),
        Index("ix_historical_tickets_incident", "incident_id"),
        Index(
            "uq_historical_tickets_dataset_source",
            "dataset_version",
            "source_id",
            unique=True,
        ),
        CheckConstraint(
            "resolution_time_minutes IS NULL OR resolution_time_minutes >= 0",
            name="ck_historical_ticket_resolution_minutes",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[str] = mapped_column(String(30), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[str] = mapped_column(String(30), nullable=False)
    location_id: Mapped[str] = mapped_column(String(30), nullable=False)
    location_name: Mapped[str] = mapped_column(String(120), nullable=False)
    application_id: Mapped[str | None] = mapped_column(String(30))
    device: Mapped[str | None] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    assigned_team: Mapped[str] = mapped_column(String(120), nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolution_code: Mapped[str | None] = mapped_column(String(100))
    resolution_time_minutes: Mapped[int | None] = mapped_column(Integer)
    incident_id: Mapped[str | None] = mapped_column(String(30))
    knowledge_article_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    related_ticket_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)


class SyntheticIncident(Base):
    __tablename__ = "synthetic_incidents"
    __table_args__ = (
        CheckConstraint("end_at >= start_at", name="ck_synthetic_incident_window"),
        Index(
            "uq_synthetic_incidents_dataset_source",
            "dataset_version",
            "source_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    affected_location_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    affected_application_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    affected_user_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    services: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    public_summary: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str] = mapped_column(Text, nullable=False)
    related_ticket_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"
    __table_args__ = (
        Index(
            "uq_telemetry_source",
            "timestamp",
            "service",
            "location_id",
            "dataset_version",
            unique=True,
        ),
        Index("ix_telemetry_lookup", "dataset_version", "service", "location_id", "timestamp"),
        CheckConstraint(
            "availability >= 0 AND availability <= 100", name="ck_telemetry_availability"
        ),
        CheckConstraint("latency_ms >= 0", name="ck_telemetry_latency"),
        CheckConstraint("error_rate >= 0 AND error_rate <= 100", name="ck_telemetry_error_rate"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    service: Mapped[str] = mapped_column(String(120), nullable=False)
    location_id: Mapped[str] = mapped_column(String(30), nullable=False)
    availability: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_rate: Mapped[float] = mapped_column(Float, nullable=False)
    incident_id: Mapped[str | None] = mapped_column(String(30))
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)


class SyntheticLogRecord(Base):
    __tablename__ = "synthetic_log_records"
    __table_args__ = (
        Index(
            "uq_synthetic_log_source",
            "host",
            "timestamp",
            "service",
            "location_id",
            "message",
            "dataset_version",
            unique=True,
        ),
        Index("ix_synthetic_log_lookup", "dataset_version", "service", "location_id", "timestamp"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    service: Mapped[str] = mapped_column(String(120), nullable=False)
    location_id: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    incident_id: Mapped[str | None] = mapped_column(String(30))
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)


class Investigation(Base):
    __tablename__ = "investigations"
    __table_args__ = (
        Index("ix_investigations_ticket_created", "ticket_id", "created_at"),
        Index(
            "uq_investigations_active_ticket",
            "ticket_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
        CheckConstraint(
            "reference_basis IN ('ticket_created_at', 'curated_demo_scenario')",
            name="ck_investigation_reference_basis",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0", name="ck_investigation_duration"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_analyses.id", ondelete="SET NULL")
    )
    requested_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[InvestigationStatus] = mapped_column(investigation_status_enum, nullable=False)
    reference_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    planned_tools: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ticket: Mapped[Ticket] = relationship()
    analysis: Mapped[AIAnalysis | None] = relationship()
    requested_by: Mapped[User] = relationship()
    steps: Mapped[list["InvestigationStep"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
        order_by="InvestigationStep.step_order",
    )


class InvestigationStep(Base):
    __tablename__ = "investigation_steps"
    __table_args__ = (
        Index("uq_investigation_step_key", "investigation_id", "step_key", unique=True),
        Index("uq_investigation_step_order", "investigation_id", "step_order", unique=True),
        CheckConstraint("source_count >= 0", name="ck_investigation_step_sources"),
        CheckConstraint("duration_ms >= 0", name="ck_investigation_step_duration"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[InvestigationStepStatus] = mapped_column(step_status_enum, nullable=False)
    sanitized_inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    investigation: Mapped[Investigation] = relationship(back_populates="steps")
