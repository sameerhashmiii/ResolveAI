from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeSearchItem(BaseModel):
    source_id: UUID
    document_id: UUID
    article_id: str
    title: str
    category: str
    heading: str | None
    excerpt: str
    relevance_score: float = Field(ge=0, le=1)
    source_path: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    embedding_model: str
    items: list[KnowledgeSearchItem]


class KnowledgeDocumentChunk(BaseModel):
    source_id: UUID
    chunk_index: int
    heading: str | None
    content: str
    token_count: int
    embedding_model: str


class KnowledgeDocumentResponse(BaseModel):
    document_id: UUID
    article_id: str
    title: str
    category: str
    version: str
    checksum: str
    source_path: str
    is_active: bool
    ingested_at: datetime
    created_at: datetime
    updated_at: datetime
    chunks: list[KnowledgeDocumentChunk]
