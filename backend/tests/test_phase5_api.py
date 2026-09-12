from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AuthContext, get_current_auth
from app.db.session import get_db_session
from app.main import app
from app.models.domain import Session, User
from app.models.enums import Role
from app.schemas.knowledge import (
    KnowledgeDocumentChunk,
    KnowledgeDocumentResponse,
    KnowledgeSearchItem,
    KnowledgeSearchResponse,
)
from app.services.knowledge import KnowledgeSearchService


class EmptyDb:
    pass


def auth_context() -> AuthContext:
    user = User(
        id=uuid4(),
        name="Knowledge Analyst",
        email="phase5@example.test",
        role=Role.SUPPORT_ANALYST,
        is_active=True,
        is_demo=True,
    )
    session = Session(
        id=uuid4(),
        user_id=user.id,
        token_hash="c" * 64,
        csrf_token="csrf-phase5",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        user=user,
    )
    return AuthContext(user=user, session=session)


async def test_knowledge_search_requires_authentication() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/knowledge/search", params={"q": "vpn failure"})
    assert response.status_code == 401


async def test_knowledge_search_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = auth_context()
    source_id = uuid4()
    document_id = uuid4()

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_search(
        _: KnowledgeSearchService, query: str, category: str | None, top_k: int
    ) -> KnowledgeSearchResponse:
        assert (query, category, top_k) == ("VPN connects but intranet unavailable", None, 5)
        return KnowledgeSearchResponse(
            query=query,
            embedding_model="local-hash-v1",
            items=[
                KnowledgeSearchItem(
                    source_id=source_id,
                    document_id=document_id,
                    article_id="KA-0001",
                    title="VPN Guide",
                    category="VPN / Remote Access",
                    heading="Troubleshooting Steps",
                    excerpt="## Troubleshooting Steps\nCheck DNS assigned by VPN.",
                    relevance_score=0.91,
                    source_path="articles/ka-0001.md",
                )
            ],
        )

    monkeypatch.setattr(KnowledgeSearchService, "search", fake_search)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/knowledge/search",
                params={"q": "VPN connects but intranet unavailable"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["embedding_model"] == "local-hash-v1"
    assert payload["items"][0]["source_id"] == str(source_id)
    assert payload["items"][0]["excerpt"].startswith("## Troubleshooting Steps")
    assert "embedding" not in payload["items"][0]


async def test_document_contract_has_ordered_source_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = auth_context()
    document_id = uuid4()
    now = datetime.now(UTC)

    async def db_override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, EmptyDb())

    async def auth_override() -> AuthContext:
        return auth

    async def fake_document(
        _: KnowledgeSearchService, requested_id: UUID
    ) -> KnowledgeDocumentResponse:
        assert requested_id == document_id
        return KnowledgeDocumentResponse(
            document_id=document_id,
            article_id="KA-0001",
            title="VPN Guide",
            category="VPN / Remote Access",
            version="resolveai-phase3-v1",
            checksum="a" * 64,
            source_path="articles/ka-0001.md",
            is_active=True,
            ingested_at=now,
            created_at=now,
            updated_at=now,
            chunks=[
                KnowledgeDocumentChunk(
                    source_id=uuid4(),
                    chunk_index=0,
                    heading="VPN Guide",
                    content="# VPN Guide",
                    token_count=2,
                    embedding_model="local-hash-v1",
                )
            ],
        )

    monkeypatch.setattr(KnowledgeSearchService, "get_document", fake_document)
    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_current_auth] = auth_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/knowledge/documents/{document_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["chunks"][0]["content"] == "# VPN Guide"
    assert "embedding" not in response.json()["chunks"][0]
