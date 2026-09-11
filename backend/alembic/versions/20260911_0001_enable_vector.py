"""Enable the pgvector extension.

Revision ID: 20260911_0001
Revises:
Create Date: 2026-09-11
"""
from alembic import op

revision: str = "20260911_0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
