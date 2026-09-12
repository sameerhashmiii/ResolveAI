from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag.retrieval import RetrievalCandidate


class KnowledgeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def vector_candidates(
        self,
        embedding: list[float],
        embedding_model: str,
        *,
        category: str | None,
        limit: int,
    ) -> list[RetrievalCandidate]:
        distance = KnowledgeChunk.embedding.cosine_distance(embedding).label("distance")
        statement = (
            select(KnowledgeChunk, KnowledgeDocument, distance)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.is_active.is_(True))
            .where(KnowledgeChunk.embedding_model == embedding_model)
        )
        if category is not None:
            statement = statement.where(KnowledgeDocument.category == category)
        rows = (
            await self.db.execute(statement.order_by(distance, KnowledgeChunk.id).limit(limit))
        ).all()
        return [
            RetrievalCandidate(
                source_id=chunk.id,
                document_id=document.id,
                article_id=document.article_id,
                title=document.title,
                category=document.category,
                heading=chunk.heading,
                content=chunk.content,
                source_path=document.source_path,
                chunk_index=chunk.chunk_index,
                vector_similarity=min(1.0, max(0.0, 1.0 - float(raw_distance) / 2.0)),
            )
            for chunk, document, raw_distance in rows
        ]

    async def document(self, document_id: UUID) -> KnowledgeDocument | None:
        return cast(
            KnowledgeDocument | None,
            await self.db.scalar(
                select(KnowledgeDocument)
                .options(selectinload(KnowledgeDocument.chunks))
                .where(KnowledgeDocument.id == document_id)
                .where(KnowledgeDocument.is_active.is_(True))
            ),
        )
