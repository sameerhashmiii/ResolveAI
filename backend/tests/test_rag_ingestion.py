import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeDocument
from app.rag.embeddings import LocalHashEmbedding
from app.rag.ingestion import IngestionRepository, KnowledgeIngestionService


class ChangedModelEmbedding(LocalHashEmbedding):
    name = "local-hash-test-v2"


class MemoryRepository:
    def __init__(self) -> None:
        self.documents: dict[str, KnowledgeDocument] = {}
        self.commits = 0
        self.rollbacks = 0

    async def get(self, article_id: str) -> KnowledgeDocument | None:
        return self.documents.get(article_id)

    def add(self, document: KnowledgeDocument) -> None:
        self.documents[document.article_id] = document

    async def deactivate_absent(self, article_ids: set[str]) -> int:
        count = 0
        for article_id, document in self.documents.items():
            if article_id not in article_ids and document.is_active:
                document.is_active = False
                count += 1
        return count

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def write_corpus(path: Path, guidance: str = "Restore VPN access.") -> None:
    articles = path / "articles"
    articles.mkdir()
    source = f"""# VPN Guide

**Article ID:** KA-1

## Category
VPN / Remote Access

## Troubleshooting Steps
1. Check the VPN gateway.

## Resolution Guidance
{guidance}
"""
    (articles / "ka-1.md").write_text(source, encoding="utf-8")
    metadata: dict[str, object] = {
        "article_id": "KA-1",
        "category": "VPN / Remote Access",
        "environment": "Synthetic",
        "escalation_criteria": "Escalate safely",
        "file": "articles/ka-1.md",
        "related_systems": ["VPN"],
        "resolution_guidance": guidance,
        "symptoms": ["gateway failure"],
        "title": "VPN Guide",
        "troubleshooting_steps": ["Check the VPN gateway"],
    }
    (path / "index.json").write_text(json.dumps({"articles": [metadata]}), encoding="utf-8")


async def test_ingestion_create_skip_update_and_deactivate(tmp_path: Path) -> None:
    write_corpus(tmp_path)
    repository = MemoryRepository()
    repository.documents["KA-OLD"] = KnowledgeDocument(
        article_id="KA-OLD",
        slug="ka-old",
        source_path="articles/ka-old.md",
        title="Old Guide",
        category="Other",
        version="resolveai-phase3-v1",
        checksum="0" * 64,
        is_active=True,
        ingested_at=datetime.now(UTC),
    )
    service = KnowledgeIngestionService(
        cast(AsyncSession, object()),
        LocalHashEmbedding(),
        tmp_path,
        cast(IngestionRepository, repository),
    )

    created = await service.ingest()
    skipped = await service.ingest()
    original_contents = [chunk.content for chunk in repository.documents["KA-1"].chunks]
    (tmp_path / "articles" / "ka-1.md").unlink()
    (tmp_path / "articles").rmdir()
    write_corpus(tmp_path, "Restore VPN and DNS access.")
    updated = await service.ingest()
    model_updated = await KnowledgeIngestionService(
        cast(AsyncSession, object()),
        ChangedModelEmbedding(),
        tmp_path,
        cast(IngestionRepository, repository),
    ).ingest()

    assert (
        created.documents_created,
        created.documents_updated,
        created.documents_skipped,
    ) == (1, 0, 0)
    assert created.chunks_written > 0
    assert created.documents_deactivated == 1
    assert repository.documents["KA-OLD"].is_active is False
    assert (
        skipped.documents_created,
        skipped.documents_updated,
        skipped.documents_skipped,
    ) == (0, 0, 1)
    assert skipped.chunks_written == 0
    assert updated.documents_updated == 1
    assert updated.chunks_written == len(repository.documents["KA-1"].chunks)
    assert model_updated.documents_updated == 1
    assert all(
        chunk.embedding_model == "local-hash-test-v2"
        for chunk in repository.documents["KA-1"].chunks
    )
    assert original_contents != [chunk.content for chunk in repository.documents["KA-1"].chunks]
    assert repository.commits == 4
    assert repository.rollbacks == 0
