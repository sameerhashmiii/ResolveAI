from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.demo.corpus import OperationalCorpus, load_operational_corpus
from app.models.operational import (
    DatasetImport,
    HistoricalTicket,
    SyntheticApplication,
    SyntheticIncident,
    SyntheticLocation,
    SyntheticLogRecord,
    TelemetryRecord,
)
from app.rag.embeddings import EmbeddingProvider, LocalHashEmbedding

MODEL_BY_COUNT: dict[str, Any] = {
    "locations": SyntheticLocation,
    "applications": SyntheticApplication,
    "tickets": HistoricalTicket,
    "incidents": SyntheticIncident,
    "telemetry": TelemetryRecord,
    "logs": SyntheticLogRecord,
}


@dataclass(frozen=True)
class OperationalImportReport:
    dataset_version: str
    manifest_checksum: str
    status: str
    created: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)


class OperationalIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        data_dir: Path,
        embedder: EmbeddingProvider | None = None,
        *,
        batch_size: int = 500,
    ) -> None:
        self.session = session
        self.data_dir = data_dir
        self.embedder = embedder or LocalHashEmbedding()
        self.batch_size = batch_size

    async def ingest(self) -> OperationalImportReport:
        corpus = load_operational_corpus(self.data_dir)
        version = corpus.manifest.dataset_version
        existing = await self.session.scalar(
            select(DatasetImport).where(DatasetImport.dataset_version == version)
        )
        if (
            existing is not None
            and existing.status == "completed"
            and existing.manifest_checksum == corpus.manifest_checksum
            and existing.counts == corpus.counts
            and await self._database_counts(version) == corpus.counts
        ):
            return OperationalImportReport(
                version, corpus.manifest_checksum, "skipped", {}, corpus.counts
            )
        try:
            for model in reversed(tuple(MODEL_BY_COUNT.values())):
                await self.session.execute(delete(model).where(model.dataset_version == version))
            if existing is None:
                existing = DatasetImport(
                    dataset_version=version,
                    manifest_checksum=corpus.manifest_checksum,
                    status="running",
                    counts={},
                )
                self.session.add(existing)
            else:
                existing.manifest_checksum = corpus.manifest_checksum
                existing.status = "running"
                existing.completed_at = None
                existing.counts = {}
            for values in self._model_batches(corpus):
                self.session.add_all(values)
                await self.session.flush()
            existing.status = "completed"
            existing.completed_at = datetime.now(UTC)
            existing.counts = corpus.counts
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return OperationalImportReport(
            version, corpus.manifest_checksum, "completed", corpus.counts, {}
        )

    async def _database_counts(self, version: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for name, model in MODEL_BY_COUNT.items():
            count = await self.session.scalar(
                select(func.count()).select_from(model).where(model.dataset_version == version)
            )
            result[name] = int(count or 0)
        return result

    def _model_batches(self, corpus: OperationalCorpus) -> list[list[Any]]:
        version = corpus.manifest.dataset_version
        groups: list[list[Any]] = [
            [
                SyntheticLocation(
                    source_id=row.location_id,
                    name=row.name,
                    network_metadata=row.network_metadata(),
                    dataset_version=version,
                )
                for row in corpus.locations
            ],
            [
                SyntheticApplication(
                    source_id=row.application_id,
                    name=row.name,
                    owner=row.owner,
                    criticality=row.criticality,
                    environment=row.environment,
                    normal_availability=row.normal_availability,
                    dependencies=row.dependencies,
                    dataset_version=version,
                )
                for row in corpus.applications
            ],
            [
                HistoricalTicket(
                    source_id=row.ticket_id,
                    opened_at=row.created_at,
                    updated_at=row.updated_at,
                    user_id=row.user_id,
                    location_id=row.location_id,
                    location_name=row.location_name,
                    application_id=row.affected_application_id,
                    device=row.affected_device,
                    title=row.title,
                    description=row.description,
                    category=row.category,
                    subcategory=row.subcategory,
                    priority=row.priority,
                    status=row.status,
                    assigned_team=row.assigned_team,
                    resolution=row.resolution,
                    resolution_code=row.resolution_code,
                    resolution_time_minutes=row.resolution_time_minutes,
                    incident_id=row.incident_id,
                    knowledge_article_ids=row.knowledge_article_ids,
                    related_ticket_ids=row.related_ticket_ids,
                    embedding=self.embedder.embed(f"{row.title}\n{row.description}"),
                    embedding_model=self.embedder.name,
                    dataset_version=version,
                )
                for row in corpus.tickets
            ],
            [
                SyntheticIncident(
                    source_id=row.incident_id,
                    title=row.title,
                    start_at=row.start_at,
                    end_at=row.end_at,
                    affected_location_ids=row.affected_location_ids,
                    affected_application_ids=row.affected_application_ids,
                    affected_user_ids=row.affected_user_ids,
                    services=row.affected_services,
                    public_summary=row.public_summary,
                    resolution=row.resolution,
                    related_ticket_ids=row.related_ticket_ids,
                    dataset_version=version,
                )
                for row in corpus.incidents
            ],
            [
                TelemetryRecord(
                    timestamp=row.timestamp,
                    service=row.service,
                    location_id=row.location_id,
                    availability=row.availability,
                    latency_ms=row.latency_ms,
                    error_rate=row.error_rate,
                    incident_id=row.incident_id,
                    dataset_version=version,
                )
                for row in corpus.telemetry
            ],
            [
                SyntheticLogRecord(
                    host=row.host,
                    timestamp=row.timestamp,
                    severity=row.severity,
                    service=row.service,
                    location_id=row.location_id,
                    message=row.message,
                    incident_id=row.incident_id,
                    dataset_version=version,
                )
                for row in corpus.logs
            ],
        ]
        return [
            group[start : start + self.batch_size]
            for group in groups
            for start in range(0, len(group), self.batch_size)
        ]
