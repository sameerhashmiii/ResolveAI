"""Add Phase 7 root cause assessments.

Revision ID: 20260911_0006
Revises: 20260911_0005
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "20260911_0006"
down_revision: str | None = "20260911_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    status = sa.Enum(
        "queued", "running", "completed", "failed", "timed_out", name="root_cause_status"
    )
    op.create_table(
        "root_cause_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "investigation_id",
            sa.Uuid(),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("analysis_id", sa.Uuid(), sa.ForeignKey("ai_analyses.id", ondelete="SET NULL")),
        sa.Column("requested_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workflow_version", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("probable_root_cause", sa.String(500)),
        sa.Column("inference_key", sa.String(100)),
        sa.Column("confidence", sa.Float()),
        sa.Column("confidence_version", sa.String(30), nullable=False),
        sa.Column("recommendation", sa.String(1000)),
        sa.Column("requires_escalation", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("limitations", JSONB(), nullable=False),
        sa.Column("confidence_factors", JSONB(), nullable=False),
        sa.Column("error_code", sa.String(50)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("mode IN ('local_demo', 'hosted')", name="ck_root_cause_mode"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_root_cause_confidence",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0", name="ck_root_cause_duration"
        ),
        sa.CheckConstraint(
            "status != 'completed' OR "
            "(probable_root_cause IS NOT NULL AND recommendation IS NOT NULL)",
            name="ck_root_cause_completed_fields",
        ),
    )
    op.create_index(
        "ix_root_cause_assessments_ticket_created",
        "root_cause_assessments",
        ["ticket_id", "created_at"],
    )
    op.create_index(
        "uq_root_cause_assessments_investigation",
        "root_cause_assessments",
        ["investigation_id"],
        unique=True,
    )
    op.create_index(
        "uq_root_cause_assessments_active_ticket",
        "root_cause_assessments",
        ["ticket_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_table(
        "assessment_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.Uuid(),
            sa.ForeignKey("root_cause_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(500), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("supports", sa.String(300), nullable=False),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("metadata", JSONB(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)",
            name="ck_assessment_evidence_relevance",
        ),
        sa.CheckConstraint("length(excerpt) <= 1200", name="ck_assessment_evidence_excerpt"),
    )
    op.create_index(
        "uq_assessment_evidence_source",
        "assessment_evidence",
        ["assessment_id", "source_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("assessment_evidence")
    op.drop_table("root_cause_assessments")
    sa.Enum(name="root_cause_status").drop(op.get_bind(), checkfirst=True)
