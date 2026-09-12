from collections.abc import Callable
from typing import Any

from app.models.domain import AIAnalysis, Ticket
from app.models.enums import InvestigationStepStatus
from app.models.operational import Investigation
from app.root_cause.schemas import EvidenceSnapshot

EXCERPT_LIMIT = 1200
_FORBIDDEN = ("ground_truth", "hidden", "private", "secret", "chain_of_thought")
_CAPS = {
    "search_knowledge_base": 5,
    "search_similar_tickets": 5,
    "get_ticket_history": 10,
    "get_system_status": 5,
    "get_telemetry": 8,
    "search_logs": 8,
    "get_related_incident": 5,
}


def collect_evidence(
    investigation: Investigation, ticket: Ticket, analysis: AIAnalysis | None
) -> tuple[list[EvidenceSnapshot], list[str]]:
    del analysis  # Classification is context, not source evidence.
    evidence = [_ticket_fact(ticket)]
    limitations: list[str] = []
    handlers: dict[str, Callable[[dict[str, Any], dict[str, Any]], list[EvidenceSnapshot]]] = {
        "search_knowledge_base": _knowledge,
        "search_similar_tickets": _similar,
        "get_ticket_history": _history,
        "get_system_status": _status,
        "get_telemetry": _telemetry,
        "search_logs": _logs,
        "get_related_incident": _incidents,
    }
    for step in sorted(investigation.steps, key=lambda item: item.step_order):
        if step.tool_name and step.status == InvestigationStepStatus.FAILED:
            limitations.append(f"{step.tool_name} did not complete")
            continue
        if (
            step.status != InvestigationStepStatus.COMPLETED
            or step.tool_name not in handlers
            or not isinstance(step.result, dict)
            or _unsafe(step.result)
        ):
            continue
        inputs = step.sanitized_inputs if isinstance(step.sanitized_inputs, dict) else {}
        try:
            values = handlers[step.tool_name](step.result, inputs)
        except (TypeError, ValueError):
            continue
        evidence.extend(values[: _CAPS[step.tool_name]])
    unique: dict[str, EvidenceSnapshot] = {}
    for item in evidence:
        unique.setdefault(item.source_id, item)
    return list(unique.values()), list(dict.fromkeys(limitations))


def _ticket_fact(ticket: Ticket) -> EvidenceSnapshot:
    facts = [ticket.title, ticket.description]
    for label, value in (
        ("Location", ticket.location),
        ("Application", ticket.application),
        ("Device", ticket.device),
    ):
        if value:
            facts.append(f"{label}: {value}")
    return _evidence(
        "ticket_fact",
        f"ticket:{ticket.id}",
        "Reported ticket facts",
        " | ".join(facts),
        "The requester's reported symptoms and context",
        metadata={"location": ticket.location, "service": ticket.application},
    )


def _knowledge(result: dict[str, Any], _: dict[str, Any]) -> list[EvidenceSnapshot]:
    return [
        _evidence(
            "knowledge_chunk",
            _source(item),
            _text(item, "title"),
            _text(item, "excerpt"),
            "Relevant published troubleshooting guidance",
            _score(item.get("relevance_score")),
            _knowledge_metadata(item),
        )
        for item in _items(result, "items")
        if _valid_item(item, "source_id", "title", "excerpt")
    ]


def _knowledge_metadata(item: dict[str, Any]) -> dict[str, str]:
    category = _optional_text(item.get("category"))
    services = {
        "DNS / Name Resolution": "DNS",
        "VPN / Remote Access": "VPN",
        "Wi-Fi / Wireless": "Wi-Fi",
        "Outlook / Email": "Email",
        "Microsoft 365": "Microsoft 365",
        "Password / MFA": "Active Directory",
        "Account Lockout": "Active Directory",
    }
    metadata: dict[str, str] = {}
    if category:
        metadata["category"] = category
        if category in services:
            metadata["service"] = services[category]
    return metadata


def _similar(result: dict[str, Any], _: dict[str, Any]) -> list[EvidenceSnapshot]:
    values: list[EvidenceSnapshot] = []
    for item in _items(result, "items"):
        if not _valid_item(item, "source_id", "title"):
            continue
        resolution = item.get("resolution")
        description = item.get("description")
        excerpt = resolution if isinstance(resolution, str) and resolution.strip() else description
        if not isinstance(excerpt, str) or not excerpt.strip():
            continue
        values.append(
            _evidence(
                "similar_ticket",
                _source(item),
                _text(item, "title"),
                excerpt,
                "Symptoms or resolution from a similar resolved ticket",
                _score(item.get("similarity")),
                {"incident_id": _optional_text(item.get("incident_id"))},
            )
        )
    return values


def _history(result: dict[str, Any], _: dict[str, Any]) -> list[EvidenceSnapshot]:
    return [
        _evidence(
            "ticket_history",
            _source(item),
            _text(item, "event_type"),
            _text(item, "summary"),
            "Recorded public ticket history",
            metadata={"timestamp": _optional_text(item.get("created_at"))},
        )
        for item in _items(result, "events")
        if _valid_item(item, "source_id", "event_type", "summary")
    ]


def _status(result: dict[str, Any], inputs: dict[str, Any]) -> list[EvidenceSnapshot]:
    values: list[EvidenceSnapshot] = []
    for item in _items(result, "services"):
        if not _valid_item(item, "source_id", "service", "state"):
            continue
        service, state = _text(item, "service"), _text(item, "state")
        location = _optional_text(item.get("location")) or _optional_text(inputs.get("location"))
        values.append(
            _evidence(
                "system_status",
                _source(item),
                f"{service} system status",
                f"{service} at {location or 'reported location'} was {state}",
                f"Observed {service} service state: {state}",
                metadata={
                    "service": service,
                    "location": location,
                    "state": state,
                    "timestamp": _optional_text(item.get("timestamp")),
                    "availability": _number(item.get("availability")),
                    "latency_ms": _number(item.get("latency_ms")),
                    "error_rate": _number(item.get("error_rate")),
                },
            )
        )
    return values


def _telemetry(result: dict[str, Any], inputs: dict[str, Any]) -> list[EvidenceSnapshot]:
    service = _optional_text(inputs.get("service"))
    location = _optional_text(inputs.get("location"))
    values: list[EvidenceSnapshot] = []
    for item in _items(result, "observations"):
        if not _valid_item(item, "source_id", "timestamp"):
            continue
        availability = _number(item.get("availability"))
        latency = _number(item.get("latency_ms"))
        errors = _number(item.get("error_rate"))
        if availability is None or latency is None or errors is None:
            continue
        anomalous = availability < 99 or latency >= 500 or errors >= 2
        if not anomalous:
            continue
        excerpt = f"availability {availability:g}%, latency {latency:g}ms, error rate {errors:g}%"
        values.append(
            _evidence(
                "telemetry",
                _source(item),
                f"{service or 'Service'} anomalous telemetry",
                excerpt,
                "Anomalous operational telemetry",
                metadata={
                    "service": service,
                    "location": location,
                    "timestamp": _optional_text(item.get("timestamp")),
                    "incident_id": _optional_text(item.get("incident_id")),
                },
            )
        )
    return values


def _logs(result: dict[str, Any], inputs: dict[str, Any]) -> list[EvidenceSnapshot]:
    service = _optional_text(inputs.get("service"))
    location = _optional_text(inputs.get("location"))
    values: list[EvidenceSnapshot] = []
    for item in _items(result, "records"):
        if not _valid_item(item, "source_id", "severity", "message"):
            continue
        severity = _text(item, "severity").casefold()
        if severity not in {"warning", "warn", "error", "critical"}:
            continue
        values.append(
            _evidence(
                "log",
                _source(item),
                f"{service or 'Service'} {severity} log",
                _text(item, "message"),
                "Warning or error log observation",
                metadata={
                    "service": service,
                    "location": location,
                    "timestamp": _optional_text(item.get("timestamp")),
                    "severity": severity,
                    "incident_id": _optional_text(item.get("incident_id")),
                },
            )
        )
    return values


def _incidents(result: dict[str, Any], _: dict[str, Any]) -> list[EvidenceSnapshot]:
    values: list[EvidenceSnapshot] = []
    for item in _items(result, "incidents"):
        if not _valid_item(item, "source_id", "title", "public_summary"):
            continue
        services = item.get("services")
        service = (
            services[0]
            if isinstance(services, list) and services and isinstance(services[0], str)
            else None
        )
        values.append(
            _evidence(
                "incident",
                _source(item),
                _text(item, "title"),
                _text(item, "public_summary"),
                "Related public incident",
                metadata={
                    "service": service,
                    "timestamp": _optional_text(item.get("start_at")),
                },
            )
        )
    return values


def _evidence(
    evidence_type: str,
    source_id: str,
    title: str,
    excerpt: str,
    supports: str,
    relevance_score: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> EvidenceSnapshot:
    safe_metadata = {key: value for key, value in (metadata or {}).items() if value is not None}
    return EvidenceSnapshot(
        evidence_type=evidence_type,
        source_id=source_id.strip()[:500],
        title=" ".join(title.split())[:300],
        excerpt=" ".join(excerpt.split())[:EXCERPT_LIMIT],
        supports=" ".join(supports.split())[:300],
        relevance_score=relevance_score,
        metadata=safe_metadata,
    )


def _items(result: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = result.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict) and not _unsafe(item)]


def _valid_item(item: dict[str, Any], *fields: str) -> bool:
    return all(isinstance(item.get(field), str) and item[field].strip() for field in fields)


def _source(item: dict[str, Any]) -> str:
    return _text(item, "source_id")


def _text(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError
    return value


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _score(value: object) -> float | None:
    number = _number(value)
    return number if number is not None and 0 <= number <= 1 else None


def _unsafe(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            any(token in str(key).casefold() for token in _FORBIDDEN) or _unsafe(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_unsafe(item) for item in value)
    return False
