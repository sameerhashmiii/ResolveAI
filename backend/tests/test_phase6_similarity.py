from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational import HistoricalTicket
from app.repositories.operational import OperationalRepository, SimilarCandidate
from app.services.similar_tickets import SimilarTicketService


class FakeRepository:
    def __init__(self, candidates: list[SimilarCandidate]) -> None:
        self.candidates = candidates

    async def similar_candidates(
        self, embedding: list[float], embedding_model: str, limit: int
    ) -> list[SimilarCandidate]:
        assert len(embedding) == 384
        assert embedding_model == "local-hash-v1"
        assert limit >= 40
        return self.candidates


def historical(source_id: str, title: str) -> HistoricalTicket:
    now = datetime.now(UTC)
    return HistoricalTicket(
        source_id=source_id,
        opened_at=now,
        updated_at=now,
        user_id="USR-00001",
        location_id="LOC-001",
        location_name="Dallas",
        title=title,
        description="VPN connection unavailable",
        category="VPN / Remote Access",
        subcategory="VPN",
        priority="P2",
        status="resolved",
        assigned_team="Network",
        resolution="Synthetic configuration restored",
        resolution_time_minutes=30,
        knowledge_article_ids=[],
        related_ticket_ids=[],
        embedding=[0.0] * 384,
        embedding_model="local-hash-v1",
        dataset_version="test-v1",
    )


async def test_similar_ranking_is_stable_and_source_faithful() -> None:
    repository = FakeRepository(
        [
            SimilarCandidate(historical("TKT-000002", "Printer issue"), 0.8),
            SimilarCandidate(historical("TKT-000001", "VPN unavailable"), 0.8),
        ]
    )
    service = SimilarTicketService(
        cast(AsyncSession, object()), repository=cast(OperationalRepository, repository)
    )
    results = await service.search("VPN unavailable", "VPN connection unavailable", 2)
    assert [item.source_id for item in results] == ["TKT-000001", "TKT-000002"]
    assert results[0].title == "VPN unavailable"
    assert all(0 <= item.similarity <= 1 for item in results)
