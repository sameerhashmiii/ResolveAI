from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings import EmbeddingProvider, LocalHashEmbedding, technical_tokens
from app.repositories.operational import OperationalRepository, SimilarCandidate
from app.schemas.investigations import SimilarTicketResponse


@dataclass(frozen=True)
class _Ranked:
    candidate: SimilarCandidate
    score: float


class SimilarTicketService:
    def __init__(
        self,
        db: AsyncSession,
        embedder: EmbeddingProvider | None = None,
        repository: OperationalRepository | None = None,
    ) -> None:
        self.embedder = embedder or LocalHashEmbedding()
        self.repository = repository or OperationalRepository(db)

    async def search(self, title: str, description: str, top_k: int) -> list[SimilarTicketResponse]:
        query = f"{title}\n{description}"
        candidates = await self.repository.similar_candidates(
            self.embedder.embed(query), self.embedder.name, min(200, max(40, top_k * 10))
        )
        query_tokens = set(technical_tokens(query))
        ranked = []
        for candidate in candidates:
            ticket_tokens = set(
                technical_tokens(f"{candidate.ticket.title} {candidate.ticket.description}")
            )
            lexical = len(query_tokens & ticket_tokens) / max(1, len(query_tokens | ticket_tokens))
            ranked.append(_Ranked(candidate, 0.8 * candidate.vector_similarity + 0.2 * lexical))
        ranked.sort(key=lambda item: (-item.score, item.candidate.ticket.source_id))
        return [self._response(item) for item in ranked[:top_k]]

    @staticmethod
    def _response(item: _Ranked) -> SimilarTicketResponse:
        ticket = item.candidate.ticket
        return SimilarTicketResponse(
            source_id=ticket.source_id,
            title=ticket.title,
            description=ticket.description,
            category=ticket.category,
            priority=ticket.priority,
            status=ticket.status,
            resolution=ticket.resolution,
            resolution_time_minutes=ticket.resolution_time_minutes,
            opened_at=ticket.opened_at,
            similarity=round(min(1.0, max(0.0, item.score)), 8),
            incident_id=ticket.incident_id,
        )
