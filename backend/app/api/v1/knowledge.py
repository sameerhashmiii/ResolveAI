from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentAuth, DbSession
from app.schemas.knowledge import KnowledgeDocumentResponse, KnowledgeSearchResponse
from app.services.knowledge import KnowledgeSearchService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    auth: CurrentAuth,
    db: DbSession,
    q: Annotated[str, Query(min_length=2, max_length=500)],
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    top_k: Annotated[int, Query(ge=1, le=20)] = 5,
) -> KnowledgeSearchResponse:
    del auth
    return await KnowledgeSearchService(db).search(q, category, top_k)


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_knowledge_document(
    document_id: UUID, auth: CurrentAuth, db: DbSession
) -> KnowledgeDocumentResponse:
    del auth
    return await KnowledgeSearchService(db).get_document(document_id)
