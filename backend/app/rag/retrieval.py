from dataclasses import dataclass
from math import ceil
from uuid import UUID

from app.rag.embeddings import technical_tokens

VECTOR_WEIGHT = 0.75
LEXICAL_WEIGHT = 0.25


@dataclass(frozen=True)
class RetrievalCandidate:
    source_id: UUID
    document_id: UUID
    article_id: str
    title: str
    category: str
    heading: str | None
    content: str
    source_path: str
    chunk_index: int
    vector_similarity: float


@dataclass(frozen=True)
class RankedChunk:
    candidate: RetrievalCandidate
    relevance_score: float


def hybrid_rerank(
    query: str,
    candidates: list[RetrievalCandidate],
    *,
    top_k: int,
    max_per_document: int = 2,
    max_per_category: int | None = None,
    preferred_categories: tuple[str, ...] = (),
) -> list[RankedChunk]:
    """Rank by 0.75 normalized cosine similarity + 0.25 query-token recall."""
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    if max_per_document < 1:
        raise ValueError("max_per_document must be positive")
    category_limit = max_per_category or max(1, ceil(top_k * 0.6))
    query_tokens = set(technical_tokens(query))
    scored: list[RankedChunk] = []
    seen_sources: set[UUID] = set()
    for candidate in candidates:
        if candidate.source_id in seen_sources:
            continue
        seen_sources.add(candidate.source_id)
        content_tokens = set(technical_tokens(candidate.content))
        lexical = len(query_tokens & content_tokens) / len(query_tokens) if query_tokens else 0.0
        vector = min(1.0, max(0.0, candidate.vector_similarity))
        score = VECTOR_WEIGHT * vector + LEXICAL_WEIGHT * lexical
        scored.append(RankedChunk(candidate, min(1.0, max(0.0, score))))
    scored.sort(
        key=lambda item: (
            -item.relevance_score,
            item.candidate.article_id,
            item.candidate.chunk_index,
            str(item.candidate.source_id),
        )
    )
    selected: list[RankedChunk] = []
    counts: dict[UUID, int] = {}
    category_counts: dict[str, int] = {}

    def select_item(item: RankedChunk) -> bool:
        count = counts.get(item.candidate.document_id, 0)
        category_count = category_counts.get(item.candidate.category, 0)
        if count >= max_per_document or category_count >= category_limit:
            return False
        selected.append(item)
        counts[item.candidate.document_id] = count + 1
        category_counts[item.candidate.category] = category_count + 1
        return True

    for category in preferred_categories:
        match = next(
            (
                item
                for item in scored
                if item.candidate.category == category and item not in selected
            ),
            None,
        )
        if match is not None:
            select_item(match)
        if len(selected) == top_k:
            return selected

    for item in scored:
        if item in selected:
            continue
        select_item(item)
        if len(selected) == top_k:
            break
    selected.sort(
        key=lambda item: (
            -item.relevance_score,
            item.candidate.article_id,
            item.candidate.chunk_index,
            str(item.candidate.source_id),
        )
    )
    return selected
