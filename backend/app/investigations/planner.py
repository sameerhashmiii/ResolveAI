from typing import Any, TypedDict
from uuid import UUID

from app.models.domain import AIAnalysis, Ticket

MAX_TOOL_INVOCATIONS = 10


class PlannedTool(TypedDict):
    step_key: str
    label: str
    tool_name: str
    arguments: dict[str, Any]


def plan_investigation(ticket: Ticket, analysis: AIAnalysis) -> list[PlannedTool]:
    text = " ".join(
        value
        for value in (
            ticket.title,
            ticket.description,
            ticket.category,
            analysis.category,
            ticket.application,
        )
        if value
    ).casefold()
    location = ticket.location
    application = ticket.application
    plan: list[PlannedTool] = [
        {
            "step_key": "knowledge",
            "label": "Search approved knowledge",
            "tool_name": "search_knowledge_base",
            "arguments": {
                "query": f"{ticket.title} {ticket.description}",
                "category": None,
                "top_k": 5,
            },
        },
        {
            "step_key": "similar-tickets",
            "label": "Search similar historical tickets",
            "tool_name": "search_similar_tickets",
            "arguments": {"title": ticket.title, "description": ticket.description, "top_k": 5},
        },
        {
            "step_key": "ticket-history",
            "label": "Read ticket history",
            "tool_name": "get_ticket_history",
            "arguments": {"ticket_id": str(ticket.id), "max_records": 50},
        },
    ]
    services: list[str] = []
    if "vpn" in text:
        services.append("VPN")
        if any(token in text for token in ("payrollpro", "internal", "dns", "unavailable")):
            services.append("DNS")
    elif any(token in text for token in ("microsoft 365", "office 365", "m365", "outlook")):
        services.append("Microsoft 365")
    elif any(token in text for token in ("wi-fi", "wifi", "wireless")):
        services.append("Wi-Fi")
    elif any(token in text for token in ("password", "mfa", "account lockout")):
        services.append("Active Directory")
    elif application and any(token in text for token in ("application", "outage", "unavailable")):
        services.append(application)
    elif "network" in text:
        services.append("Network")

    if location:
        for service in services:
            slug = service.casefold().replace(" ", "-")
            common = {
                "service": service,
                "location": location,
                "reference_time": None,
            }
            plan.extend(
                [
                    {
                        "step_key": f"{slug}-status",
                        "label": f"Inspect {service} status",
                        "tool_name": "get_system_status",
                        "arguments": dict(common),
                    },
                    {
                        "step_key": f"{slug}-telemetry",
                        "label": f"Inspect {service} telemetry",
                        "tool_name": "get_telemetry",
                        "arguments": {**common, "window_minutes": 60, "max_records": 100},
                    },
                    {
                        "step_key": f"{slug}-logs",
                        "label": f"Inspect {service} synthetic logs",
                        "tool_name": "search_logs",
                        "arguments": {**common, "window_minutes": 60, "max_records": 50},
                    },
                ]
            )
        if services:
            incident_service = services[-1]
            plan.append(
                {
                    "step_key": "related-incident",
                    "label": "Read related public incident facts",
                    "tool_name": "get_related_incident",
                    "arguments": {
                        "service": incident_service,
                        "location": location,
                        "application": application if incident_service != "VPN" else None,
                        "reference_time": None,
                    },
                }
            )
    unique: list[PlannedTool] = []
    seen: set[tuple[str, str]] = set()
    for item in plan:
        key = (item["tool_name"], item["step_key"])
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique[:MAX_TOOL_INVOCATIONS]


def ticket_uuid(value: str) -> UUID:
    return UUID(value)
