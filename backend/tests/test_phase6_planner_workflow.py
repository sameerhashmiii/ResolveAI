from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest

from app.investigations.planner import PlannedTool, plan_investigation
from app.investigations.workflow import InvestigationState, build_investigation_graph
from app.models.domain import AIAnalysis, Ticket, User
from app.models.enums import AnalysisStatus, Role, TicketStatus
from app.schemas.investigations import ToolResult
from app.services.investigation_tools import InvestigationToolService, status_state


def objects(
    title: str, category: str, location: str | None = "Dallas"
) -> tuple[Ticket, AIAnalysis]:
    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        name="Demo",
        email="phase6@example.test",
        role=Role.SUPPORT_ANALYST,
        is_active=True,
        is_demo=True,
    )
    ticket = Ticket(
        id=uuid4(),
        number=1200,
        title=title,
        description="The service is unavailable during a synthetic workflow",
        requester_name="Requester",
        location=location,
        application="PayrollPro" if "Payroll" in title else None,
        status=TicketStatus.NEW,
        created_by=user,
        created_at=now,
        updated_at=now,
    )
    analysis = AIAnalysis(
        id=uuid4(),
        ticket_id=ticket.id,
        requested_by_id=user.id,
        workflow_version="4.0",
        provider="local_demo",
        mode="local_demo",
        status=AnalysisStatus.COMPLETED,
        category=category,
        requires_manual_review=False,
        created_at=now,
    )
    return ticket, analysis


@pytest.mark.parametrize(
    ("title", "category", "expected"),
    [
        ("VPN connected but Payroll unavailable", "vpn", {"VPN", "DNS"}),
        ("Microsoft 365 login unavailable", "email", {"Microsoft 365"}),
        ("Chicago Wi-Fi disconnected", "wifi", {"Wi-Fi"}),
    ],
)
def test_planner_selects_relevant_bounded_tools(
    title: str, category: str, expected: set[str]
) -> None:
    ticket, analysis = objects(title, category, "Chicago" if "Wi-Fi" in title else "Dallas")
    plan = plan_investigation(ticket, analysis)
    services = {
        cast(str, item["arguments"].get("service"))
        for item in plan
        if item["arguments"].get("service")
    }
    assert expected <= services
    assert len(plan) <= 10
    assert len({item["step_key"] for item in plan}) == len(plan)
    assert [item["tool_name"] for item in plan[:3]] == [
        "search_knowledge_base",
        "search_similar_tickets",
        "get_ticket_history",
    ]


def test_generic_planner_only_uses_required_tools() -> None:
    ticket, analysis = objects("Request for a standard peripheral", "other", None)
    assert len(plan_investigation(ticket, analysis)) == 3


def test_status_thresholds_are_deterministic() -> None:
    assert status_state(99.9, 20, 0.1) == "operational"
    assert status_state(98.9, 20, 0.1) == "degraded"
    assert status_state(99.9, 500, 0.1) == "degraded"
    assert status_state(91.2, 240, 8.7) == "degraded"
    assert status_state(79.9, 20, 0.1) == "outage"


class FakeTools:
    async def search_knowledge_base(self, **_: Any) -> ToolResult:
        return ToolResult(
            tool_name="search_knowledge_base",
            input_summary={"top_k": 5},
            result={"items": [{"source_id": "KA-0001"}]},
            source_ids=["KA-0001"],
            source_count=1,
        )

    async def search_similar_tickets(self, **_: Any) -> ToolResult:
        raise ValueError("synthetic failure")


async def test_real_langgraph_compiles_invokes_and_keeps_safe_observations() -> None:
    now = datetime.now(UTC)
    plan: list[PlannedTool] = [
        {
            "step_key": "knowledge",
            "label": "Knowledge",
            "tool_name": "search_knowledge_base",
            "arguments": {"query": "vpn", "top_k": 5},
        },
        {
            "step_key": "similar",
            "label": "Similar",
            "tool_name": "search_similar_tickets",
            "arguments": {"title": "VPN", "description": "Unavailable", "top_k": 5},
        },
    ]
    state: InvestigationState = {
        "plan": plan,
        "reference_time": now,
        "observations": [],
        "limitations": [],
    }
    graph = build_investigation_graph(cast(InvestigationToolService, FakeTools()))
    output = cast(InvestigationState, await graph.ainvoke(state))
    assert len(output["observations"]) == 2
    assert output["observations"][1]["error_code"] == "tool_failed"
    assert output["limitations"] == ["search_similar_tickets did not complete"]
    serialized = str(output).casefold()
    assert "root_cause" not in serialized
    assert "recommendation" not in serialized
    assert "confidence" not in serialized
