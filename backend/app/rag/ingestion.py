import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag.chunking import SourceChunk, chunk_markdown
from app.rag.embeddings import EmbeddingProvider
from app.rag.metadata import ArticleMetadata, load_index, manifest_details, resolve_source


@dataclass(frozen=True)
class IngestionReport:
    documents_created: int = 0
    documents_updated: int = 0
    documents_skipped: int = 0
    documents_deactivated: int = 0
    chunks_written: int = 0


class IngestionRepository(Protocol):
    async def get(self, article_id: str) -> KnowledgeDocument | None: ...

    def add(self, document: KnowledgeDocument) -> None: ...

    async def deactivate_absent(self, article_ids: set[str]) -> int: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class SqlIngestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, article_id: str) -> KnowledgeDocument | None:
        return cast(
            KnowledgeDocument | None,
            await self.session.scalar(
                select(KnowledgeDocument)
                .options(selectinload(KnowledgeDocument.chunks))
                .where(KnowledgeDocument.article_id == article_id)
            ),
        )

    def add(self, document: KnowledgeDocument) -> None:
        self.session.add(document)

    async def deactivate_absent(self, article_ids: set[str]) -> int:
        result = await self.session.execute(
            update(KnowledgeDocument)
            .where(KnowledgeDocument.is_active.is_(True))
            .where(KnowledgeDocument.article_id.not_in(article_ids))
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        return int(getattr(result, "rowcount", 0))

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


@dataclass(frozen=True)
class _SourceArticle:
    metadata: ArticleMetadata
    source_path: str
    content: str
    checksum: str
    chunks: list[SourceChunk]


class KnowledgeIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        embedder: EmbeddingProvider,
        data_dir: Path,
        repository: IngestionRepository | None = None,
    ) -> None:
        self.embedder = embedder
        self.data_dir = data_dir
        self.repository = repository or SqlIngestionRepository(session)

    def _load_sources(self) -> tuple[str, list[_SourceArticle]]:
        index = load_index(self.data_dir)
        version, expected_checksums = manifest_details(self.data_dir)
        sources: list[_SourceArticle] = []
        for metadata in index.articles:
            path = resolve_source(self.data_dir, metadata.file)
            try:
                raw = path.read_bytes()
                content = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise ValueError("Knowledge source could not be read") from exc
            checksum = hashlib.sha256(raw).hexdigest()
            manifest_key = f"{self.data_dir.name}/{metadata.file}"
            expected = expected_checksums.get(manifest_key)
            if expected_checksums and expected is None:
                raise ValueError("Knowledge source is missing from the dataset manifest")
            if expected is not None and expected != checksum:
                raise ValueError("Knowledge source checksum mismatch")
            if not content.startswith(f"# {metadata.title}\n"):
                raise ValueError("Knowledge source title does not match its metadata")
            if f"**Article ID:** {metadata.article_id}" not in content:
                raise ValueError("Knowledge source article ID does not match its metadata")
            sources.append(
                _SourceArticle(
                    metadata=metadata,
                    source_path=metadata.file,
                    content=content,
                    checksum=checksum,
                    chunks=chunk_markdown(content),
                )
            )
        return version, sources

    def _write_chunks(self, document: KnowledgeDocument, chunks: list[SourceChunk]) -> int:
        document.chunks.clear()
        document.chunks.extend(
            KnowledgeChunk(
                chunk_index=chunk.chunk_index,
                heading=chunk.heading,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=self.embedder.embed(chunk.content),
                embedding_model=self.embedder.name,
            )
            for chunk in chunks
        )
        return len(chunks)

    async def ingest(self) -> IngestionReport:
        version, sources = self._load_sources()
        created = updated = skipped = chunks_written = 0
        now = datetime.now(UTC)
        try:
            for source in sources:
                document = await self.repository.get(source.metadata.article_id)
                same_model = document is not None and bool(document.chunks) and all(
                    chunk.embedding_model == self.embedder.name for chunk in document.chunks
                )
                if (
                    document is not None
                    and document.checksum == source.checksum
                    and same_model
                    and document.is_active
                ):
                    skipped += 1
                    continue
                if document is None:
                    document = KnowledgeDocument(
                        article_id=source.metadata.article_id,
                        slug=Path(source.source_path).stem,
                        source_path=source.source_path,
                        title=source.metadata.title,
                        category=source.metadata.category,
                        version=version,
                        checksum=source.checksum,
                        is_active=True,
                        ingested_at=now,
                    )
                    self.repository.add(document)
                    created += 1
                else:
                    document.slug = Path(source.source_path).stem
                    document.source_path = source.source_path
                    document.title = source.metadata.title
                    document.category = source.metadata.category
                    document.version = version
                    document.checksum = source.checksum
                    document.is_active = True
                    document.ingested_at = now
                    updated += 1
                chunks_written += self._write_chunks(document, source.chunks)
            deactivated = await self.repository.deactivate_absent(
                {source.metadata.article_id for source in sources}
            )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return IngestionReport(created, updated, skipped, deactivated, chunks_written)
