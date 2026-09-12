from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.knowledge import KnowledgeDocument
from app.rag.embeddings import EmbeddingProvider, LocalHashEmbedding
from app.rag.expansion import category_hints, expand_query
from app.rag.retrieval import RankedChunk, RetrievalCandidate, hybrid_rerank
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import (
    KnowledgeDocumentChunk,
    KnowledgeDocumentResponse,
    KnowledgeSearchItem,
    KnowledgeSearchResponse,
)


class RetrievalRepository(Protocol):
    async def vector_candidates(
        self,
        embedding: list[float],
        embedding_model: str,
        *,
        category: str | None,
        limit: int,
    ) -> list[RetrievalCandidate]: ...

    async def document(self, document_id: UUID) -> KnowledgeDocument | None: ...


class KnowledgeSearchService:
    def __init__(
        self,
        db: AsyncSession,
        embedder: EmbeddingProvider | None = None,
        repository: RetrievalRepository | None = None,
    ) -> None:
        self.embedder = embedder or LocalHashEmbedding()
        self.repository = repository or KnowledgeRepository(db)

    async def search(self, query: str, category: str | None, top_k: int) -> KnowledgeSearchResponse:
        expanded = expand_query(query)
        candidates = await self.repository.vector_candidates(
            self.embedder.embed(expanded),
            self.embedder.name,
            category=category,
            limit=min(200, max(40, top_k * 10)),
        )
        ranked = hybrid_rerank(
            expanded,
            candidates,
            top_k=top_k,
            preferred_categories=category_hints(query),
        )
        return KnowledgeSearchResponse(
            query=query,
            embedding_model=self.embedder.name,
            items=[self._search_item(item) for item in ranked],
        )

    async def get_document(self, document_id: UUID) -> KnowledgeDocumentResponse:
        document = await self.repository.document(document_id)
        if document is None:
            raise NotFoundError
        return self._document_response(document)

    @staticmethod
    def _search_item(item: RankedChunk) -> KnowledgeSearchItem:
        value = item.candidate
        return KnowledgeSearchItem(
            source_id=value.source_id,
            document_id=value.document_id,
            article_id=value.article_id,
            title=value.title,
            category=value.category,
            heading=value.heading,
            excerpt=value.content,
            relevance_score=round(item.relevance_score, 8),
            source_path=value.source_path,
        )

    @staticmethod
    def _document_response(document: KnowledgeDocument) -> KnowledgeDocumentResponse:
        return KnowledgeDocumentResponse(
            document_id=document.id,
            article_id=document.article_id,
            title=document.title,
            category=document.category,
            version=document.version,
            checksum=document.checksum,
            source_path=document.source_path,
            is_active=document.is_active,
            ingested_at=document.ingested_at,
            created_at=document.created_at,
            updated_at=document.updated_at,
            chunks=[
                KnowledgeDocumentChunk(
                    source_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    heading=chunk.heading,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    embedding_model=chunk.embedding_model,
                )
                for chunk in sorted(document.chunks, key=lambda value: value.chunk_index)
            ],
        )
