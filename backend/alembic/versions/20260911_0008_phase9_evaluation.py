"""Add Phase 9 aggregate evaluation runs.

Revision ID: 20260911_0008
Revises: 20260911_0007
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260911_0008"
down_revision: str | None = "20260911_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dataset_version", sa.String(80), nullable=False),
        sa.Column("dataset_checksum", sa.String(64), nullable=False),
        sa.Column("runner_version", sa.String(30), nullable=False),
        sa.Column("workflow_version", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("methodology", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("error_code", sa.String(50)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_evaluation_runs_status",
        ),
        sa.CheckConstraint("sample_count > 0", name="ck_evaluation_runs_sample_count"),
        sa.CheckConstraint("length(dataset_checksum) = 64", name="ck_evaluation_runs_checksum"),
        sa.CheckConstraint("synthetic", name="ck_evaluation_runs_synthetic"),
        sa.CheckConstraint(
            "(status = 'running' AND completed_at IS NULL AND error_code IS NULL) OR "
            "(status = 'completed' AND completed_at IS NOT NULL AND error_code IS NULL) OR "
            "(status = 'failed' AND completed_at IS NOT NULL AND error_code IS NOT NULL)",
            name="ck_evaluation_runs_lifecycle",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_evaluation_runs_timestamps",
        ),
    )
    op.create_index(
        "ix_evaluation_runs_status_created", "evaluation_runs", ["status", "created_at"]
    )
    op.create_index(
        "ix_evaluation_runs_dataset_created", "evaluation_runs", ["dataset_version", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("evaluation_runs")
