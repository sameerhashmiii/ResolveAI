from dataclasses import dataclass
from datetime import datetime
from typing import cast

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational import (
    DatasetImport,
    HistoricalTicket,
    SyntheticApplication,
    SyntheticIncident,
    SyntheticLocation,
    SyntheticLogRecord,
    TelemetryRecord,
)


@dataclass(frozen=True)
class SimilarCandidate:
    ticket: HistoricalTicket
    vector_similarity: float


class OperationalRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _active_dataset(self) -> object:
        return (
            select(DatasetImport.dataset_version)
            .where(DatasetImport.status == "completed")
            .order_by(DatasetImport.completed_at.desc())
            .limit(1)
            .scalar_subquery()
        )

    async def similar_candidates(
        self, embedding: list[float], embedding_model: str, limit: int
    ) -> list[SimilarCandidate]:
        distance = HistoricalTicket.embedding.cosine_distance(embedding).label("distance")
        rows = (
            await self.db.execute(
                select(HistoricalTicket, distance)
                .where(
                    HistoricalTicket.dataset_version == self._active_dataset(),
                    HistoricalTicket.embedding_model == embedding_model,
                    HistoricalTicket.resolution.is_not(None),
                    HistoricalTicket.status.in_(["resolved", "closed"]),
                )
                .order_by(distance, HistoricalTicket.source_id)
                .limit(limit)
            )
        ).all()
        return [
            SimilarCandidate(ticket, min(1.0, max(0.0, 1.0 - float(distance) / 2.0)))
            for ticket, distance in rows
        ]

    async def location(self, value: str) -> SyntheticLocation | None:
        return cast(
            SyntheticLocation | None,
            await self.db.scalar(
                select(SyntheticLocation).where(
                    SyntheticLocation.dataset_version == self._active_dataset(),
                    or_(
                        func.lower(SyntheticLocation.source_id) == value.casefold(),
                        func.lower(SyntheticLocation.name) == value.casefold(),
                    ),
                )
            ),
        )

    async def application(self, value: str) -> SyntheticApplication | None:
        return cast(
            SyntheticApplication | None,
            await self.db.scalar(
                select(SyntheticApplication).where(
                    SyntheticApplication.dataset_version == self._active_dataset(),
                    or_(
                        func.lower(SyntheticApplication.source_id) == value.casefold(),
                        func.lower(SyntheticApplication.name) == value.casefold(),
                    ),
                )
            ),
        )

    async def telemetry(
        self, service: str, location_id: str, start: datetime, end: datetime, limit: int
    ) -> list[TelemetryRecord]:
        rows = await self.db.scalars(
            select(TelemetryRecord)
            .where(
                TelemetryRecord.dataset_version == self._active_dataset(),
                func.lower(TelemetryRecord.service) == service.casefold(),
                TelemetryRecord.location_id == location_id,
                TelemetryRecord.timestamp.between(start, end),
            )
            .order_by(TelemetryRecord.timestamp, TelemetryRecord.id)
            .limit(limit)
        )
        return list(rows)

    async def nearest_telemetry(
        self, service: str, location_id: str, at: datetime
    ) -> TelemetryRecord | None:
        return cast(
            TelemetryRecord | None,
            await self.db.scalar(
                select(TelemetryRecord)
                .where(
                    TelemetryRecord.dataset_version == self._active_dataset(),
                    func.lower(TelemetryRecord.service) == service.casefold(),
                    TelemetryRecord.location_id == location_id,
                )
                .order_by(
                    func.abs(func.extract("epoch", TelemetryRecord.timestamp - at)),
                    TelemetryRecord.timestamp,
                )
                .limit(1)
            ),
        )

    async def logs(
        self, service: str, location_id: str, start: datetime, end: datetime, limit: int
    ) -> list[SyntheticLogRecord]:
        rows = await self.db.scalars(
            select(SyntheticLogRecord)
            .where(
                SyntheticLogRecord.dataset_version == self._active_dataset(),
                func.lower(SyntheticLogRecord.service) == service.casefold(),
                SyntheticLogRecord.location_id == location_id,
                SyntheticLogRecord.timestamp.between(start, end),
            )
            .order_by(SyntheticLogRecord.timestamp, SyntheticLogRecord.id)
            .limit(limit)
        )
        return list(rows)

    async def incidents(
        self,
        service: str | None,
        location_id: str | None,
        application_id: str | None,
        at: datetime,
    ) -> list[SyntheticIncident]:
        filters = [
            SyntheticIncident.dataset_version == self._active_dataset(),
            SyntheticIncident.start_at <= at,
            SyntheticIncident.end_at >= at,
        ]
        if service:
            filters.append(SyntheticIncident.services.contains([service]))
        if location_id:
            filters.append(SyntheticIncident.affected_location_ids.contains([location_id]))
        if application_id:
            filters.append(SyntheticIncident.affected_application_ids.contains([application_id]))
        rows = await self.db.scalars(
            select(SyntheticIncident)
            .where(*filters)
            .order_by(SyntheticIncident.start_at, SyntheticIncident.source_id)
            .limit(25)
        )
        return list(rows)

    async def curated_incident(
        self, service: str, location_id: str | None, application_id: str | None
    ) -> SyntheticIncident | None:
        filters = [
            SyntheticIncident.dataset_version == self._active_dataset(),
            SyntheticIncident.services.contains([service]),
        ]
        if location_id:
            filters.append(SyntheticIncident.affected_location_ids.contains([location_id]))
        if application_id:
            filters.append(SyntheticIncident.affected_application_ids.contains([application_id]))
        return cast(
            SyntheticIncident | None,
            await self.db.scalar(
                select(SyntheticIncident)
                .where(*filters)
                .order_by(SyntheticIncident.source_id)
                .limit(1)
            ),
        )
