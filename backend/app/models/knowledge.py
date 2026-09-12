from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index("ix_knowledge_documents_active_category", "is_active", "category"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    article_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    source_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="KnowledgeChunk.chunk_index",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        CheckConstraint("token_count > 0", name="ck_knowledge_chunks_token_count"),
        CheckConstraint("length(trim(content)) > 0", name="ck_knowledge_chunks_content"),
        Index("uq_knowledge_chunks_document_index", "document_id", "chunk_index", unique=True),
        Index("ix_knowledge_chunks_embedding_model", "embedding_model"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    heading: Mapped[str | None] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks", lazy="joined")
