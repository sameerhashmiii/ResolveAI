"""Add Phase 6 synthetic operations and investigations.

Revision ID: 20260911_0005
Revises: 20260911_0004
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "20260911_0005"
down_revision: str | None = "20260911_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    investigation_status = sa.Enum(
        "queued", "running", "completed", "failed", "timed_out", name="investigation_status"
    )
    step_status = sa.Enum(
        "started", "completed", "skipped", "failed", name="investigation_step_status"
    )
    op.create_table(
        "dataset_imports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dataset_version", sa.String(100), nullable=False, unique=True),
        sa.Column("manifest_checksum", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("counts", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "synthetic_locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("network_metadata", JSONB(), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=False),
    )
    op.create_index(
        "ix_synthetic_locations_dataset_name", "synthetic_locations", ["dataset_version", "name"]
    )
    op.create_index(
        "uq_synthetic_locations_dataset_source",
        "synthetic_locations",
        ["dataset_version", "source_id"],
        unique=True,
    )
    op.create_table(
        "synthetic_applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("owner", sa.String(160), nullable=False),
        sa.Column("criticality", sa.String(20), nullable=False),
        sa.Column("environment", sa.String(100), nullable=False),
        sa.Column("normal_availability", sa.Float(), nullable=False),
        sa.Column("dependencies", JSONB(), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=False),
        sa.CheckConstraint(
            "normal_availability >= 0 AND normal_availability <= 100",
            name="ck_synthetic_app_availability",
        ),
    )
    op.create_index("ix_synthetic_applications_name", "synthetic_applications", ["name"])
    op.create_index(
        "uq_synthetic_applications_dataset_source",
        "synthetic_applications",
        ["dataset_version", "source_id"],
        unique=True,
    )
    op.create_table(
        "historical_tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.String(30), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(30), nullable=False),
        sa.Column("location_id", sa.String(30), nullable=False),
        sa.Column("location_name", sa.String(120), nullable=False),
        sa.Column("application_id", sa.String(30)),
        sa.Column("device", sa.String(120)),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("assigned_team", sa.String(120), nullable=False),
        sa.Column("resolution", sa.Text()),
        sa.Column("resolution_code", sa.String(100)),
        sa.Column("resolution_time_minutes", sa.Integer()),
        sa.Column("incident_id", sa.String(30)),
        sa.Column("knowledge_article_ids", JSONB(), nullable=False),
        sa.Column("related_ticket_ids", JSONB(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("embedding_model", sa.String(100), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=False),
        sa.CheckConstraint(
            "resolution_time_minutes IS NULL OR resolution_time_minutes >= 0",
            name="ck_historical_ticket_resolution_minutes",
        ),
    )
    for name, columns in (
        ("ix_historical_tickets_dataset_category", ["dataset_version", "category"]),
        ("ix_historical_tickets_dataset_priority", ["dataset_version", "priority"]),
        ("ix_historical_tickets_opened_at", ["opened_at"]),
        ("ix_historical_tickets_incident", ["incident_id"]),
        ("ix_historical_tickets_embedding_model", ["embedding_model"]),
    ):
        op.create_index(name, "historical_tickets", columns)
    op.create_index(
        "uq_historical_tickets_dataset_source",
        "historical_tickets",
        ["dataset_version", "source_id"],
        unique=True,
    )
    op.create_table(
        "synthetic_incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.String(30), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("affected_location_ids", JSONB(), nullable=False),
        sa.Column("affected_application_ids", JSONB(), nullable=False),
        sa.Column("affected_user_ids", JSONB(), nullable=False),
        sa.Column("services", JSONB(), nullable=False),
        sa.Column("public_summary", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False),
        sa.Column("related_ticket_ids", JSONB(), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=False),
        sa.CheckConstraint("end_at >= start_at", name="ck_synthetic_incident_window"),
    )
    op.create_index("ix_synthetic_incidents_start_at", "synthetic_incidents", ["start_at"])
    op.create_index("ix_synthetic_incidents_end_at", "synthetic_incidents", ["end_at"])
    op.create_index(
        "uq_synthetic_incidents_dataset_source",
        "synthetic_incidents",
        ["dataset_version", "source_id"],
        unique=True,
    )
    op.create_table(
        "telemetry_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service", sa.String(120), nullable=False),
        sa.Column("location_id", sa.String(30), nullable=False),
        sa.Column("availability", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=False),
        sa.Column("incident_id", sa.String(30)),
        sa.Column("dataset_version", sa.String(100), nullable=False),
        sa.CheckConstraint(
            "availability >= 0 AND availability <= 100", name="ck_telemetry_availability"
        ),
        sa.CheckConstraint("latency_ms >= 0", name="ck_telemetry_latency"),
        sa.CheckConstraint("error_rate >= 0 AND error_rate <= 100", name="ck_telemetry_error_rate"),
    )
    op.create_index(
        "uq_telemetry_source",
        "telemetry_records",
        ["timestamp", "service", "location_id", "dataset_version"],
        unique=True,
    )
    op.create_index(
        "ix_telemetry_lookup",
        "telemetry_records",
        ["dataset_version", "service", "location_id", "timestamp"],
    )
    op.create_table(
        "synthetic_log_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("service", sa.String(120), nullable=False),
        sa.Column("location_id", sa.String(30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("incident_id", sa.String(30)),
        sa.Column("dataset_version", sa.String(100), nullable=False),
    )
    op.create_index(
        "uq_synthetic_log_source",
        "synthetic_log_records",
        ["host", "timestamp", "service", "location_id", "message", "dataset_version"],
        unique=True,
    )
    op.create_index(
        "ix_synthetic_log_lookup",
        "synthetic_log_records",
        ["dataset_version", "service", "location_id", "timestamp"],
    )
    op.create_table(
        "investigations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("analysis_id", sa.Uuid(), sa.ForeignKey("ai_analyses.id", ondelete="SET NULL")),
        sa.Column("requested_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workflow_version", sa.String(30), nullable=False),
        sa.Column("status", investigation_status, nullable=False),
        sa.Column("reference_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_basis", sa.String(40), nullable=False),
        sa.Column("planned_tools", JSONB(), nullable=False),
        sa.Column("error_code", sa.String(50)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "reference_basis IN ('ticket_created_at', 'curated_demo_scenario')",
            name="ck_investigation_reference_basis",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0", name="ck_investigation_duration"
        ),
    )
    op.create_index(
        "ix_investigations_ticket_created", "investigations", ["ticket_id", "created_at"]
    )
    op.create_index(
        "uq_investigations_active_ticket",
        "investigations",
        ["ticket_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_table(
        "investigation_steps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "investigation_id",
            sa.Uuid(),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_key", sa.String(100), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("tool_name", sa.String(80)),
        sa.Column("status", step_status, nullable=False),
        sa.Column("sanitized_inputs", JSONB(), nullable=False),
        sa.Column("result", JSONB()),
        sa.Column("source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("source_count >= 0", name="ck_investigation_step_sources"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_investigation_step_duration"),
    )
    op.create_index(
        "uq_investigation_step_key",
        "investigation_steps",
        ["investigation_id", "step_key"],
        unique=True,
    )
    op.create_index(
        "uq_investigation_step_order",
        "investigation_steps",
        ["investigation_id", "step_order"],
        unique=True,
    )


def downgrade() -> None:
    for table in (
        "investigation_steps",
        "investigations",
        "synthetic_log_records",
        "telemetry_records",
        "synthetic_incidents",
        "historical_tickets",
        "synthetic_applications",
        "synthetic_locations",
        "dataset_imports",
    ):
        op.drop_table(table)
    sa.Enum(name="investigation_step_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="investigation_status").drop(op.get_bind(), checkfirst=True)
