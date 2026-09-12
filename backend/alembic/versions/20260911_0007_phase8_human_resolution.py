"""Add Phase 8 human-controlled response and outcome workflow.

Revision ID: 20260911_0007
Revises: 20260911_0006
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0007"
down_revision: str | None = "20260911_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    action_type = sa.Enum(
        "troubleshoot",
        "request_information",
        "high_impact",
        "escalate",
        name="recommendation_action_type",
    )
    recommendation_status = sa.Enum(
        "proposed",
        "approved",
        "modified",
        "rejected",
        "completed",
        name="recommendation_status",
    )
    generated_by = sa.Enum("ai", "human", name="response_generated_by")
    response_status = sa.Enum("draft", "approved", "rejected", name="support_response_status")

    op.add_column("tickets", sa.Column("resolved_at", sa.DateTime(timezone=True)))
    op.add_column("tickets", sa.Column("escalated_at", sa.DateTime(timezone=True)))
    op.add_column("tickets", sa.Column("escalation_destination", sa.String(200)))
    op.add_column("tickets", sa.Column("escalation_reason", sa.String(500)))
    op.add_column("tickets", sa.Column("resolution_summary", sa.String(1000)))
    op.execute(
        "UPDATE tickets SET resolved_at = COALESCE(updated_at, now()), "
        "resolution_summary = 'Resolved before the human-approval workflow migration.' "
        "WHERE status = 'resolved'"
    )
    op.execute(
        "UPDATE tickets SET escalated_at = COALESCE(updated_at, now()), "
        "escalation_destination = 'Legacy escalation queue', "
        "escalation_reason = 'Escalated before the human-approval workflow migration.' "
        "WHERE status = 'escalated'"
    )
    op.create_check_constraint(
        "ck_tickets_single_terminal_outcome",
        "tickets",
        "resolved_at IS NULL OR escalated_at IS NULL",
    )
    op.create_check_constraint(
        "ck_tickets_resolved_excludes_escalation",
        "tickets",
        "status != 'resolved' OR (escalated_at IS NULL AND escalation_destination IS NULL "
        "AND escalation_reason IS NULL)",
    )
    op.create_check_constraint(
        "ck_tickets_escalated_excludes_resolution",
        "tickets",
        "status != 'escalated' OR (resolved_at IS NULL AND resolution_summary IS NULL)",
    )
    op.create_check_constraint(
        "ck_tickets_resolved_fields",
        "tickets",
        "status != 'resolved' OR (resolved_at IS NOT NULL AND resolution_summary IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_tickets_escalated_fields",
        "tickets",
        "status != 'escalated' OR (escalated_at IS NOT NULL AND "
        "escalation_destination IS NOT NULL AND escalation_reason IS NOT NULL)",
    )

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "assessment_id",
            sa.Uuid(),
            sa.ForeignKey("root_cause_assessments.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("original_instructions", sa.String(1000), nullable=False),
        sa.Column("instructions", sa.String(1000), nullable=False),
        sa.Column("action_type", action_type, nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "status",
            recommendation_status,
            server_default="proposed",
            nullable=False,
        ),
        sa.Column("decided_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decision_reason", sa.String(500)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("requires_approval", name="ck_recommendations_requires_approval"),
        sa.CheckConstraint(
            "(status = 'proposed' AND decided_by_id IS NULL AND decision_reason IS NULL "
            "AND decided_at IS NULL) OR (status != 'proposed' AND decided_by_id IS NOT NULL "
            "AND decision_reason IS NOT NULL AND decided_at IS NOT NULL)",
            name="ck_recommendations_decision_fields",
        ),
    )
    op.create_index(
        "ix_recommendations_ticket_created", "recommendations", ["ticket_id", "created_at"]
    )
    op.execute(
        """
        INSERT INTO recommendations (
            id, ticket_id, assessment_id, title, original_instructions, instructions,
            action_type, requires_approval, status
        )
        SELECT gen_random_uuid(), ticket_id, id, 'Recommended support action', recommendation,
               recommendation,
               CASE WHEN requires_escalation THEN 'escalate'::recommendation_action_type
                    ELSE 'troubleshoot'::recommendation_action_type END,
               true, 'proposed'::recommendation_status
        FROM root_cause_assessments
        WHERE status = 'completed' AND recommendation IS NOT NULL
        """
    )

    op.create_table(
        "support_responses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "assessment_id",
            sa.Uuid(),
            sa.ForeignKey("root_cause_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recommendation_id",
            sa.Uuid(),
            sa.ForeignKey("recommendations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("generated_by", generated_by, nullable=False),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("draft_body", sa.Text(), nullable=False),
        sa.Column("final_body", sa.Text()),
        sa.Column("status", response_status, nullable=False),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("rejected_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("rejection_reason", sa.String(500)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("mode IN ('local_demo', 'hosted')", name="ck_support_responses_mode"),
        sa.CheckConstraint(
            "status != 'approved' OR (final_body IS NOT NULL AND approved_by_id IS NOT NULL "
            "AND approved_at IS NOT NULL)",
            name="ck_support_responses_approved_fields",
        ),
        sa.CheckConstraint(
            "status != 'rejected' OR (rejected_by_id IS NOT NULL AND rejection_reason IS NOT NULL "
            "AND rejected_at IS NOT NULL)",
            name="ck_support_responses_rejected_fields",
        ),
    )
    op.create_index(
        "ix_support_responses_ticket_created", "support_responses", ["ticket_id", "created_at"]
    )
    op.create_index(
        "uq_support_responses_active_draft",
        "support_responses",
        ["ticket_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )


def downgrade() -> None:
    op.drop_table("support_responses")
    op.drop_table("recommendations")
    sa.Enum(name="support_response_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="response_generated_by").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="recommendation_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="recommendation_action_type").drop(op.get_bind(), checkfirst=True)
    op.drop_constraint("ck_tickets_escalated_fields", "tickets", type_="check")
    op.drop_constraint("ck_tickets_resolved_fields", "tickets", type_="check")
    op.drop_constraint("ck_tickets_escalated_excludes_resolution", "tickets", type_="check")
    op.drop_constraint("ck_tickets_resolved_excludes_escalation", "tickets", type_="check")
    op.drop_constraint("ck_tickets_single_terminal_outcome", "tickets", type_="check")
    op.drop_column("tickets", "resolution_summary")
    op.drop_column("tickets", "escalation_reason")
    op.drop_column("tickets", "escalation_destination")
    op.drop_column("tickets", "escalated_at")
    op.drop_column("tickets", "resolved_at")
