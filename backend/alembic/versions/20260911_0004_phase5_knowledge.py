"""Add Phase 5 knowledge documents and vector chunks.

Revision ID: 20260911_0004
Revises: 20260911_0003
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "20260911_0004"
down_revision: str | None = "20260911_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("article_id", sa.String(50), nullable=False, unique=True),
        sa.Column("slug", sa.String(160), nullable=False, unique=True),
        sa.Column("source_path", sa.String(500), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_knowledge_documents_active_category",
        "knowledge_documents",
        ["is_active", "category"],
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(300)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("embedding_model", sa.String(100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("token_count > 0", name="ck_knowledge_chunks_token_count"),
        sa.CheckConstraint("length(trim(content)) > 0", name="ck_knowledge_chunks_content"),
    )
    op.create_index(
        "uq_knowledge_chunks_document_index",
        "knowledge_chunks",
        ["document_id", "chunk_index"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_chunks_embedding_model", "knowledge_chunks", ["embedding_model"]
    )


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
