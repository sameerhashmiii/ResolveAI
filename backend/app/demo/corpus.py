import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.demo.schemas import (
    ApplicationRow,
    IncidentRow,
    LocationRow,
    LogRow,
    Manifest,
    TelemetryRow,
    TicketRow,
)

FILES = {
    "locations": "locations/locations.json",
    "applications": "applications/applications.json",
    "tickets": "tickets/tickets.jsonl",
    "incidents": "incidents/incidents.json",
    "telemetry": "telemetry/telemetry.jsonl",
    "logs": "logs/logs.jsonl",
}


@dataclass(frozen=True)
class OperationalCorpus:
    manifest: Manifest
    manifest_checksum: str
    locations: list[LocationRow]
    applications: list[ApplicationRow]
    tickets: list[TicketRow]
    incidents: list[IncidentRow]
    telemetry: list[TelemetryRow]
    logs: list[LogRow]

    @property
    def counts(self) -> dict[str, int]:
        return {name: len(getattr(self, name)) for name in FILES}


def _safe_file(root: Path, relative: str) -> Path:
    if relative == "evaluation/ground_truth.json" or relative.startswith("evaluation/"):
        raise ValueError("evaluation data is forbidden for operational ingestion")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("operational source path escapes data directory") from exc
    return candidate


def _read_checked(root: Path, relative: str, manifest: Manifest) -> bytes:
    expected = manifest.checksums.get(relative)
    if expected is None:
        raise ValueError(f"missing manifest checksum for {relative}")
    try:
        raw = _safe_file(root, relative).read_bytes()
    except OSError as exc:
        raise ValueError(f"could not read operational source {relative}") from exc
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"checksum mismatch for {relative}")
    return raw


def _json_rows[T: BaseModel](raw: bytes, model: type[T], source: str) -> list[T]:
    try:
        value = json.loads(raw)
        if not isinstance(value, list):
            raise ValueError
        return [model.model_validate(item) for item in value]
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"invalid operational rows in {source}") from exc


def _jsonl_rows[T: BaseModel](raw: bytes, model: type[T], source: str) -> list[T]:
    rows: list[T] = []
    try:
        text = raw.decode("utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                raise ValueError(f"blank JSONL row in {source}:{number}")
            rows.append(model.model_validate_json(line))
    except (UnicodeDecodeError, ValidationError) as exc:
        raise ValueError(f"invalid operational row in {source}") from exc
    return rows


def _unique(rows: Sequence[BaseModel], field: str, source: str) -> None:
    values = [getattr(row, field) for row in rows]
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {field} in {source}")


def load_operational_corpus(root: Path) -> OperationalCorpus:
    manifest_path = _safe_file(root, "manifest.json")
    try:
        manifest_raw = manifest_path.read_bytes()
        manifest = Manifest.model_validate_json(manifest_raw)
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise ValueError("invalid operational manifest") from exc
    loaded = {name: _read_checked(root, relative, manifest) for name, relative in FILES.items()}
    locations = _json_rows(loaded["locations"], LocationRow, FILES["locations"])
    applications = _json_rows(loaded["applications"], ApplicationRow, FILES["applications"])
    tickets = _jsonl_rows(loaded["tickets"], TicketRow, FILES["tickets"])
    incidents = _json_rows(loaded["incidents"], IncidentRow, FILES["incidents"])
    telemetry = _jsonl_rows(loaded["telemetry"], TelemetryRow, FILES["telemetry"])
    logs = _jsonl_rows(loaded["logs"], LogRow, FILES["logs"])
    _unique(locations, "location_id", "locations")
    _unique(applications, "application_id", "applications")
    _unique(tickets, "ticket_id", "tickets")
    _unique(incidents, "incident_id", "incidents")
    _validate_references(locations, applications, tickets, incidents, telemetry, logs)
    corpus = OperationalCorpus(
        manifest,
        hashlib.sha256(manifest_raw).hexdigest(),
        locations,
        applications,
        tickets,
        incidents,
        telemetry,
        logs,
    )
    expected = manifest.actual_counts
    aliases = {"logs": "log_records", "telemetry": "telemetry_records"}
    if any(corpus.counts[name] != expected.get(aliases.get(name, name)) for name in FILES):
        raise ValueError("operational row counts do not match manifest")
    return corpus


def _validate_references(
    locations: list[LocationRow],
    applications: list[ApplicationRow],
    tickets: list[TicketRow],
    incidents: list[IncidentRow],
    telemetry: list[TelemetryRow],
    logs: list[LogRow],
) -> None:
    location_ids = {row.location_id for row in locations}
    application_ids = {row.application_id for row in applications}
    ticket_ids = {row.ticket_id for row in tickets}
    incident_ids = {row.incident_id for row in incidents}
    for ticket in tickets:
        if (
            ticket.location_id not in location_ids
            or ticket.affected_application_id not in application_ids | {None}
        ):
            raise ValueError("ticket contains an unknown operational foreign key")
        if (
            ticket.incident_id not in incident_ids | {None}
            or not set(ticket.related_ticket_ids) <= ticket_ids
        ):
            raise ValueError("ticket contains an unknown ticket or incident reference")
    for incident in incidents:
        if (
            not set(incident.affected_location_ids) <= location_ids
            or not set(incident.affected_application_ids) <= application_ids
        ):
            raise ValueError("incident contains an unknown operational foreign key")
        if not set(incident.related_ticket_ids) <= ticket_ids:
            raise ValueError("incident contains an unknown ticket reference")
    seen_telemetry: set[tuple[datetime, str, str]] = set()
    seen_logs: set[tuple[str, datetime, str, str, str]] = set()
    for metric in telemetry:
        key = (metric.timestamp, metric.service, metric.location_id)
        if (
            key in seen_telemetry
            or metric.location_id not in location_ids
            or metric.incident_id not in incident_ids | {None}
        ):
            raise ValueError("duplicate or invalid telemetry row")
        seen_telemetry.add(key)
    for log in logs:
        log_key = (log.host, log.timestamp, log.service, log.location_id, log.message)
        if (
            log_key in seen_logs
            or log.location_id not in location_ids
            or log.incident_id not in incident_ids | {None}
        ):
            raise ValueError("duplicate or invalid log row")
        seen_logs.add(log_key)
