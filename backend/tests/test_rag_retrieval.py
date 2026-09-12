from uuid import UUID

import pytest

from app.rag.retrieval import RetrievalCandidate, hybrid_rerank


def candidate(
    source: int,
    document: int,
    article: str,
    content: str,
    similarity: float,
    category: str = "VPN / Remote Access",
) -> RetrievalCandidate:
    return RetrievalCandidate(
        source_id=UUID(int=source),
        document_id=UUID(int=document),
        article_id=article,
        title=f"Title {article}",
        category=category,
        heading="Troubleshooting",
        content=content,
        source_path=f"articles/{article.lower()}.md",
        chunk_index=source,
        vector_similarity=similarity,
    )


def test_hybrid_reranking_is_stable_bounded_and_deduplicated() -> None:
    candidates = [
        candidate(1, 10, "KA-1", "vpn dns hostname resolution", 0.9),
        candidate(2, 10, "KA-1", "vpn gateway", 0.88),
        candidate(3, 10, "KA-1", "vpn remote access", 0.87),
        candidate(4, 20, "KA-2", "dns hostname lookup", 0.8, "DNS / Name Resolution"),
    ]
    first = hybrid_rerank("vpn dns hostname", [*candidates, candidates[0]], top_k=4)
    second = hybrid_rerank("vpn dns hostname", list(reversed(candidates)), top_k=4)

    assert first == second
    assert len(first) == 3
    assert sum(item.candidate.document_id == UUID(int=10) for item in first) == 2
    assert all(0 <= item.relevance_score <= 1 for item in first)
    assert first[0].candidate.content == candidates[0].content
    dns_item = next(item for item in first if item.candidate.article_id == "KA-2")
    assert dns_item.candidate.category == "DNS / Name Resolution"
    assert dns_item.candidate.source_path == "articles/ka-2.md"


def test_preferred_category_is_not_crowded_out() -> None:
    candidates = [
        candidate(
            source,
            source,
            f"KA-DNS-{source}",
            "dns hostname resolution",
            0.9 - source / 100,
            "DNS / Name Resolution",
        )
        for source in range(1, 6)
    ]
    candidates.append(candidate(20, 20, "KA-VPN", "vpn remote gateway", 0.5))

    ranked = hybrid_rerank(
        "vpn connected internal unavailable",
        candidates,
        top_k=5,
        preferred_categories=("VPN / Remote Access", "DNS / Name Resolution"),
    )

    assert {item.candidate.category for item in ranked} == {
        "VPN / Remote Access",
        "DNS / Name Resolution",
    }


@pytest.mark.parametrize("top_k", [0, 21])
def test_hybrid_reranking_rejects_invalid_top_k(top_k: int) -> None:
    with pytest.raises(ValueError):
        hybrid_rerank("vpn", [], top_k=top_k)
