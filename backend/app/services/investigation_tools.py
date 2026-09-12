import hashlib
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational import SyntheticLocation, SyntheticLogRecord, TelemetryRecord
from app.repositories.operational import OperationalRepository
from app.repositories.tickets import TicketRepository
from app.schemas.investigations import ToolResult
from app.services.knowledge import KnowledgeSearchService
from app.services.similar_tickets import SimilarTicketService


def status_state(availability: float, latency_ms: int, error_rate: float) -> str:
    if availability < 80 or error_rate >= 20:
        return "outage"
    if availability < 99 or latency_ms >= 500 or error_rate >= 2:
        return "degraded"
    return "operational"


class InvestigationToolService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        operational: OperationalRepository | None = None,
        knowledge: KnowledgeSearchService | None = None,
        similar: SimilarTicketService | None = None,
        tickets: TicketRepository | None = None,
    ) -> None:
        self.operational = operational or OperationalRepository(db)
        self.knowledge = knowledge or KnowledgeSearchService(db)
        self.similar = similar or SimilarTicketService(db)
        self.tickets = tickets or TicketRepository(db)

    async def search_knowledge_base(
        self, query: str, category: str | None = None, top_k: int = 5
    ) -> ToolResult:
        query = self._text(query, "query", 500)
        top_k = self._limit(top_k, 1, 10)
        response = await self.knowledge.search(query, category, top_k)
        items = [item.model_dump(mode="json") for item in response.items]
        source_ids = [str(item.source_id) for item in response.items]
        return ToolResult(
            tool_name="search_knowledge_base",
            input_summary={"query": query, "category": category, "top_k": top_k},
            result={"items": items, "embedding_model": response.embedding_model},
            source_ids=source_ids,
            source_count=len(source_ids),
        )

    async def search_similar_tickets(
        self, title: str, description: str, top_k: int = 5
    ) -> ToolResult:
        top_k = self._limit(top_k, 1, 10)
        items = await self.similar.search(
            self._text(title, "title", 300), self._text(description, "description", 5000), top_k
        )
        source_ids = [item.source_id for item in items]
        return ToolResult(
            tool_name="search_similar_tickets",
            input_summary={"top_k": top_k},
            result={"items": [item.model_dump(mode="json") for item in items]},
            source_ids=source_ids,
            source_count=len(source_ids),
        )

    async def get_ticket_history(self, ticket_id: UUID, max_records: int = 50) -> ToolResult:
        max_records = self._limit(max_records, 1, 100)
        events = (await self.tickets.events(ticket_id))[:max_records]
        source_ids = [f"ticket-event:{event.id}" for event in events]
        return ToolResult(
            tool_name="get_ticket_history",
            input_summary={"ticket_id": str(ticket_id), "max_records": max_records},
            result={
                "events": [
                    {
                        "source_id": source_id,
                        "event_type": event.event_type,
                        "summary": event.summary,
                        "created_at": event.created_at.isoformat(),
                    }
                    for source_id, event in zip(source_ids, events, strict=True)
                ]
            },
            source_ids=source_ids,
            source_count=len(source_ids),
        )

    async def get_system_status(
        self, service: str, location: str, reference_time: datetime
    ) -> ToolResult:
        service = self._text(service, "service", 120)
        at = self._time(reference_time)
        location_row = await self._location(location)
        record = await self.operational.nearest_telemetry(service, location_row.source_id, at)
        if record is None:
            raise ValueError("no synthetic telemetry for service and location")
        incidents = await self.operational.incidents(service, location_row.source_id, None, at)
        source_ids = [incident.source_id for incident in incidents]
        telemetry_id = self._telemetry_source_id(record)
        source_ids.insert(0, telemetry_id)
        state = status_state(record.availability, record.latency_ms, record.error_rate)
        observation = {
            "source_id": telemetry_id,
            "timestamp": record.timestamp.isoformat(),
            "availability": record.availability,
            "latency_ms": record.latency_ms,
            "error_rate": record.error_rate,
        }
        return ToolResult(
            tool_name="get_system_status",
            input_summary={"service": service, "location": location_row.name, "at": at.isoformat()},
            result={
                "state": state,
                "nearest_observation": observation,
                "active_public_incident_count": len(incidents),
                "services": [
                    {
                        "source_id": telemetry_id,
                        "service": service,
                        "location": location_row.name,
                        "state": state,
                        "timestamp": record.timestamp.isoformat(),
                        "availability": record.availability,
                        "latency_ms": record.latency_ms,
                        "error_rate": record.error_rate,
                        "active_public_incident_count": len(incidents),
                    }
                ],
            },
            source_ids=source_ids,
            source_count=len(source_ids),
        )

    async def get_telemetry(
        self,
        service: str,
        location: str,
        reference_time: datetime,
        window_minutes: int = 60,
        max_records: int = 100,
    ) -> ToolResult:
        service = self._text(service, "service", 120)
        window_minutes = self._limit(window_minutes, 1, 720)
        max_records = self._limit(max_records, 1, 200)
        at = self._time(reference_time)
        location_row = await self._location(location)
        delta = timedelta(minutes=window_minutes)
        rows = await self.operational.telemetry(
            service, location_row.source_id, at - delta, at + delta, max_records
        )
        observations = [
            {
                "source_id": self._telemetry_source_id(row),
                "timestamp": row.timestamp.isoformat(),
                "availability": row.availability,
                "latency_ms": row.latency_ms,
                "error_rate": row.error_rate,
                "incident_id": row.incident_id,
            }
            for row in rows
        ]
        source_ids = [item["source_id"] for item in observations]
        states = [status_state(row.availability, row.latency_ms, row.error_rate) for row in rows]
        return ToolResult(
            tool_name="get_telemetry",
            input_summary={
                "service": service,
                "location": location_row.name,
                "reference_time": at.isoformat(),
                "window_minutes": window_minutes,
                "max_records": max_records,
            },
            result={
                "observations": observations,
                "anomaly_summary": {
                    "degraded_observations": states.count("degraded"),
                    "outage_observations": states.count("outage"),
                },
            },
            source_ids=source_ids,
            source_count=len(source_ids),
        )

    async def search_logs(
        self,
        service: str,
        location: str,
        reference_time: datetime,
        window_minutes: int = 60,
        max_records: int = 50,
    ) -> ToolResult:
        service = self._text(service, "service", 120)
        window_minutes = self._limit(window_minutes, 1, 720)
        max_records = self._limit(max_records, 1, 100)
        at = self._time(reference_time)
        location_row = await self._location(location)
        delta = timedelta(minutes=window_minutes)
        rows = await self.operational.logs(
            service, location_row.source_id, at - delta, at + delta, max_records
        )
        records = [
            {
                "source_id": self._log_source_id(row),
                "host": row.host,
                "timestamp": row.timestamp.isoformat(),
                "severity": row.severity,
                "message": row.message,
                "incident_id": row.incident_id,
            }
            for row in rows
        ]
        source_ids = [item["source_id"] for item in records]
        return ToolResult(
            tool_name="search_logs",
            input_summary={
                "service": service,
                "location": location_row.name,
                "reference_time": at.isoformat(),
                "window_minutes": window_minutes,
                "max_records": max_records,
            },
            result={"records": records},
            source_ids=source_ids,
            source_count=len(source_ids),
        )

    async def get_related_incident(
        self,
        reference_time: datetime,
        service: str | None = None,
        location: str | None = None,
        application: str | None = None,
    ) -> ToolResult:
        if not any((service, location, application)):
            raise ValueError("at least one incident filter is required")
        at = self._time(reference_time)
        location_row = await self._location(location) if location else None
        application_row = await self.operational.application(application) if application else None
        if application and application_row is None:
            raise ValueError("unknown synthetic application")
        normalized_service = self._text(service, "service", 120) if service else None
        rows = await self.operational.incidents(
            normalized_service,
            location_row.source_id if location_row else None,
            application_row.source_id if application_row else None,
            at,
        )
        facts = [
            {
                "source_id": row.source_id,
                "title": row.title,
                "start_at": row.start_at.isoformat(),
                "end_at": row.end_at.isoformat(),
                "affected_location_ids": row.affected_location_ids,
                "affected_application_ids": row.affected_application_ids,
                "services": row.services,
                "public_summary": row.public_summary,
                "resolution": row.resolution,
                "related_ticket_ids": row.related_ticket_ids,
            }
            for row in rows
        ]
        source_ids = [row.source_id for row in rows]
        return ToolResult(
            tool_name="get_related_incident",
            input_summary={
                "service": normalized_service,
                "location": location_row.name if location_row else None,
                "application": application_row.name if application_row else None,
                "reference_time": at.isoformat(),
            },
            result={"incidents": facts},
            source_ids=source_ids,
            source_count=len(source_ids),
        )

    async def _location(self, value: str) -> SyntheticLocation:
        location = await self.operational.location(self._text(value, "location", 120))
        if location is None:
            raise ValueError("unknown synthetic location")
        return location

    @staticmethod
    def _text(value: str, label: str, maximum: int) -> str:
        value = value.strip()
        if not value or len(value) > maximum:
            raise ValueError(f"invalid {label}")
        return value

    @staticmethod
    def _limit(value: int, minimum: int, maximum: int) -> int:
        if not minimum <= value <= maximum:
            raise ValueError("result limit is out of bounds")
        return value

    @staticmethod
    def _time(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("reference time must include a timezone")
        return value

    @staticmethod
    def _telemetry_source_id(record: TelemetryRecord) -> str:
        return (
            f"telemetry:{record.dataset_version}:{record.service}:"
            f"{record.location_id}:{record.timestamp.isoformat()}"
        )

    @staticmethod
    def _log_source_id(record: SyntheticLogRecord) -> str:
        message_digest = hashlib.sha256(record.message.encode("utf-8")).hexdigest()[:12]
        return (
            f"synthetic-log:{record.dataset_version}:{record.host}:"
            f"{record.timestamp.isoformat()}:{message_digest}"
        )
