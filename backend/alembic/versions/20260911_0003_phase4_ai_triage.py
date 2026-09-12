"""Add Phase 4 AI triage workflow schema.

Revision ID: 20260911_0003
Revises: 20260911_0002
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260911_0003"
down_revision: str | None = "20260911_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

analysis_status = postgresql.ENUM(
    "queued",
    "running",
    "completed",
    "failed",
    "timed_out",
    name="analysis_status",
    create_type=False,
)
ticket_priority = postgresql.ENUM(
    "p1", "p2", "p3", "p4", name="ticket_priority", create_type=False
)


def upgrade() -> None:
    analysis_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "tickets",
        sa.Column("priority_overridden", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("tickets", sa.Column("priority_override_reason", sa.String(500)))
    op.create_check_constraint(
        "ck_tickets_priority_override_reason",
        "tickets",
        "NOT priority_overridden OR "
        "(priority_override_reason IS NOT NULL AND length(trim(priority_override_reason)) > 0)",
    )
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("requested_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workflow_version", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", analysis_status, nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("category_confidence", sa.Float()),
        sa.Column("recommended_priority", ticket_priority),
        sa.Column("validated_priority", ticket_priority),
        sa.Column("entities", postgresql.JSONB()),
        sa.Column("priority_factors", postgresql.JSONB()),
        sa.Column(
            "requires_manual_review", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("error_code", sa.String(50)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "category_confidence IS NULL OR "
            "(category_confidence >= 0 AND category_confidence <= 1)",
            name="ck_ai_analyses_confidence",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0", name="ck_ai_analyses_duration"
        ),
        sa.CheckConstraint("mode IN ('local_demo', 'hosted')", name="ck_ai_analyses_mode"),
    )
    op.create_index(
        "ix_ai_analyses_ticket_created_at", "ai_analyses", ["ticket_id", "created_at"]
    )
    op.create_index("ix_ai_analyses_status", "ai_analyses", ["status"])
    op.create_index(
        "uq_ai_analyses_active_ticket",
        "ai_analyses",
        ["ticket_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_table("ai_analyses")
    op.drop_constraint("ck_tickets_priority_override_reason", "tickets", type_="check")
    op.drop_column("tickets", "priority_override_reason")
    op.drop_column("tickets", "priority_overridden")
    analysis_status.drop(op.get_bind(), checkfirst=True)
