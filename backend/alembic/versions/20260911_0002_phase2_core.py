"""Create Phase 2 identity, session, ticket, event, and audit schema.

Revision ID: 20260911_0002
Revises: 20260911_0001
Create Date: 2026-09-11
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260911_0002"
down_revision: str | None = "20260911_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

role = postgresql.ENUM(
    "support_analyst", "manager", "administrator", name="user_role", create_type=False
)
ticket_status = postgresql.ENUM(
    "new", "in_progress", "resolved", "escalated", name="ticket_status", create_type=False
)
ticket_priority = postgresql.ENUM(
    "p1", "p2", "p3", "p4", name="ticket_priority", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    role.create(bind, checkfirst=True)
    ticket_status.create(bind, checkfirst=True)
    ticket_priority.create(bind, checkfirst=True)
    op.execute("CREATE SEQUENCE ticket_number_seq START WITH 1000")
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("role", role, nullable=False),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_token", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "number",
            sa.BigInteger(),
            server_default=sa.text("nextval('ticket_number_seq')"),
            nullable=False,
            unique=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requester_name", sa.String(120), nullable=False),
        sa.Column("requester_department", sa.String(120)),
        sa.Column("location", sa.String(120)),
        sa.Column("device", sa.String(120)),
        sa.Column("application", sa.String(120)),
        sa.Column("attachment_metadata", postgresql.JSONB()),
        sa.Column("category", sa.String(100)),
        sa.Column("priority", ticket_priority),
        sa.Column("status", ticket_status, server_default="new", nullable=False),
        sa.Column("assigned_to_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_tickets_assigned_to_id", "tickets", ["assigned_to_id"])
    op.create_index("ix_tickets_status_created_at", "tickets", ["status", "created_at"])
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("summary", sa.String(240), nullable=False),
        sa.Column("data", postgresql.JSONB()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.Uuid()),
        sa.Column("data", postgresql.JSONB()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("email", sa.String()),
        sa.column("role", role),
        sa.column("is_demo", sa.Boolean()),
    )
    op.bulk_insert(
        users,
        [
            {
                "id": UUID("10000000-0000-4000-8000-000000000001"),
                "name": "Avery Example",
                "email": "analyst.demo@resolveai.example",
                "role": "support_analyst",
                "is_demo": True,
            },
            {
                "id": UUID("10000000-0000-4000-8000-000000000002"),
                "name": "Morgan Example",
                "email": "manager.demo@resolveai.example",
                "role": "manager",
                "is_demo": True,
            },
            {
                "id": UUID("10000000-0000-4000-8000-000000000003"),
                "name": "Jordan Example",
                "email": "admin.demo@resolveai.example",
                "role": "administrator",
                "is_demo": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("ticket_events")
    op.drop_table("tickets")
    op.drop_table("sessions")
    op.drop_table("users")
    op.execute("DROP SEQUENCE ticket_number_seq")
    ticket_priority.drop(op.get_bind(), checkfirst=True)
    ticket_status.drop(op.get_bind(), checkfirst=True)
    role.drop(op.get_bind(), checkfirst=True)
