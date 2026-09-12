import logging
from datetime import datetime
from time import monotonic
from typing import Any, NotRequired, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from sqlalchemy.exc import SQLAlchemyError

from app.investigations.planner import PlannedTool, ticket_uuid
from app.schemas.investigations import ToolResult
from app.services.investigation_tools import InvestigationToolService

logger = logging.getLogger(__name__)


class ToolObservation(TypedDict):
    step_key: str
    label: str
    tool_name: str
    input_summary: dict[str, Any]
    result: dict[str, Any] | None
    source_count: int
    duration_ms: int
    error_code: str | None


class InvestigationState(TypedDict):
    plan: list[PlannedTool]
    reference_time: datetime
    observations: list[ToolObservation]
    limitations: list[str]
    ticket_id: NotRequired[str]
    investigation_id: NotRequired[str]


def build_investigation_graph(tools: InvestigationToolService) -> Any:
    async def plan(state: InvestigationState) -> dict[str, object]:
        return {"plan": state["plan"][:10]}

    async def execute_tools(state: InvestigationState) -> dict[str, object]:
        observations: list[ToolObservation] = []
        for item in state["plan"][:10]:
            arguments = dict(item["arguments"])
            if "reference_time" in arguments:
                arguments["reference_time"] = state["reference_time"]
            if item["tool_name"] == "get_ticket_history":
                arguments["ticket_id"] = ticket_uuid(cast(str, arguments["ticket_id"]))
            started = monotonic()
            try:
                method = getattr(tools, item["tool_name"])
                value = cast(ToolResult, await method(**arguments))
                observations.append(
                    {
                        "step_key": item["step_key"],
                        "label": item["label"],
                        "tool_name": item["tool_name"],
                        "input_summary": _safe_arguments(value.input_summary),
                        "result": value.result,
                        "source_count": value.source_count,
                        "duration_ms": max(0, round((monotonic() - started) * 1000)),
                        "error_code": None,
                    }
                )
                logger.info(
                    "Investigation tool completed",
                    extra={
                        "tool_name": item["tool_name"],
                        "step_key": item["step_key"],
                        "source_count": value.source_count,
                        "ticket_id": state.get("ticket_id"),
                        "investigation_id": state.get("investigation_id"),
                    },
                )
            except SQLAlchemyError:
                raise
            except Exception:
                observations.append(
                    {
                        "step_key": item["step_key"],
                        "label": item["label"],
                        "tool_name": item["tool_name"],
                        "input_summary": _safe_arguments(arguments),
                        "result": None,
                        "source_count": 0,
                        "duration_ms": max(0, round((monotonic() - started) * 1000)),
                        "error_code": "tool_failed",
                    }
                )
                logger.warning(
                    "Investigation tool failed",
                    extra={
                        "tool_name": item["tool_name"],
                        "step_key": item["step_key"],
                        "ticket_id": state.get("ticket_id"),
                        "investigation_id": state.get("investigation_id"),
                    },
                )
        return {"observations": observations}

    async def finalize(state: InvestigationState) -> dict[str, object]:
        limitations = [
            f"{item['tool_name']} did not complete"
            for item in state["observations"]
            if item["error_code"] is not None
        ]
        return {"limitations": limitations}

    graph = StateGraph(InvestigationState)
    graph.add_node("plan", plan)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute_tools")
    graph.add_edge("execute_tools", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def _safe_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.isoformat()
        if isinstance(value, datetime)
        else str(value)
        if key == "ticket_id"
        else value
        for key, value in arguments.items()
        if key not in {"description", "query", "title"}
    }
