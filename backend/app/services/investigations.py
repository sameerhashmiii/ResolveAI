import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Any, cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db.session import session_factory
from app.errors import ConflictError, NotFoundError
from app.investigations.planner import PlannedTool, plan_investigation
from app.investigations.workflow import InvestigationState, build_investigation_graph
from app.models.domain import AuditLog, Ticket, TicketEvent, User
from app.models.enums import InvestigationStatus, InvestigationStepStatus
from app.models.operational import Investigation, InvestigationStep, SyntheticIncident
from app.repositories.investigations import InvestigationRepository
from app.repositories.operational import OperationalRepository
from app.schemas.investigations import (
    InvestigationResponse,
    InvestigationStepResponse,
)
from app.services.investigation_tools import InvestigationToolService

WORKFLOW_VERSION = "6.0"


def investigation_response(value: Investigation) -> InvestigationResponse:
    steps = sorted(value.steps, key=lambda item: item.step_order)
    return InvestigationResponse(
        id=value.id,
        ticket_id=value.ticket_id,
        analysis_id=value.analysis_id,
        requested_by_id=value.requested_by_id,
        workflow_version=value.workflow_version,
        status=value.status,
        reference_time=value.reference_time,
        reference_basis=cast(Any, value.reference_basis),
        simulated_reference=value.reference_basis == "curated_demo_scenario",
        planned_tools=value.planned_tools,
        limitations=[
            f"{step.tool_name or step.label} did not complete"
            for step in steps
            if step.status == InvestigationStepStatus.FAILED
        ],
        error_code=value.error_code,
        started_at=value.started_at,
        completed_at=value.completed_at,
        duration_ms=value.duration_ms,
        created_at=value.created_at,
        steps=[InvestigationStepResponse.model_validate(step) for step in steps],
    )


class InvestigationService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
        tools: InvestigationToolService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repository = InvestigationRepository(db)
        self.operational = OperationalRepository(db)
        self.tools = tools or InvestigationToolService(db)

    async def request(self, ticket_id: UUID, actor: User) -> Investigation:
        ticket = await self.repository.ticket(ticket_id)
        if ticket is None:
            raise NotFoundError
        analysis = await self.repository.latest_completed_analysis(ticket_id)
        if analysis is None or await self.repository.active(ticket_id) is not None:
            raise ConflictError
        reference_time, basis = await self._reference_time(ticket, actor.is_demo)
        plan = plan_investigation(ticket, analysis)
        investigation = Investigation(
            ticket_id=ticket.id,
            analysis_id=analysis.id,
            requested_by_id=actor.id,
            workflow_version=WORKFLOW_VERSION,
            status=InvestigationStatus.QUEUED,
            reference_time=reference_time,
            reference_basis=basis,
            planned_tools=_safe_plan(plan),
        )
        self.repository.add(investigation)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError from exc
        self._record(
            investigation, "queued", "Investigation queued", "ticket.investigation.requested"
        )
        await self._commit(investigation)
        return investigation

    async def get(self, investigation_id: UUID) -> Investigation:
        value = await self.repository.get(investigation_id)
        if value is None:
            raise NotFoundError
        return value

    async def latest(self, ticket_id: UUID) -> Investigation | None:
        if await self.repository.ticket(ticket_id) is None:
            raise NotFoundError
        return await self.repository.latest(ticket_id)

    async def retry(self, investigation_id: UUID, actor: User) -> Investigation:
        value = await self.get(investigation_id)
        if value.status not in {InvestigationStatus.FAILED, InvestigationStatus.TIMED_OUT}:
            raise ConflictError
        if await self.repository.active(value.ticket_id) is not None:
            raise ConflictError
        for step in list(value.steps):
            await self.db.delete(step)
        value.steps.clear()
        value.requested_by_id = actor.id
        value.status = InvestigationStatus.QUEUED
        value.error_code = None
        value.started_at = None
        value.completed_at = None
        value.duration_ms = None
        self._record(value, "queued", "Investigation retry queued", "ticket.investigation.retried")
        await self._commit(value)
        return value

    async def execute(self, investigation_id: UUID) -> None:
        value = await self.get(investigation_id)
        if value.status != InvestigationStatus.QUEUED:
            return
        value.status = InvestigationStatus.RUNNING
        value.started_at = datetime.now(UTC)
        await self._commit(value)
        ticket = await self.repository.ticket(value.ticket_id)
        analysis = await self.repository.latest_completed_analysis(value.ticket_id)
        if ticket is None or analysis is None:
            await self._fail(value, InvestigationStatus.FAILED, "required_context_missing")
            return
        plan = plan_investigation(ticket, analysis)
        value.planned_tools = _safe_plan(plan)
        started = monotonic()
        try:
            graph = build_investigation_graph(self.tools)
            initial: InvestigationState = {
                "plan": plan,
                "reference_time": value.reference_time,
                "observations": [],
                "limitations": [],
                "ticket_id": str(value.ticket_id),
                "investigation_id": str(value.id),
            }
            async with asyncio.timeout(self.settings.investigation_timeout_seconds):
                output = cast(InvestigationState, await graph.ainvoke(initial))
            self._persist_steps(value, plan, output)
            value.status = InvestigationStatus.COMPLETED
            value.error_code = None
            value.completed_at = datetime.now(UTC)
            value.duration_ms = max(0, round((monotonic() - started) * 1000))
            self._record(
                value,
                "completed",
                "Investigation completed",
                "ticket.investigation.completed",
                {"limitations": len(output["limitations"])},
            )
            await self._commit(value)
        except TimeoutError:
            self._planning_step(value, plan)
            await self._fail(value, InvestigationStatus.TIMED_OUT, "investigation_timeout", started)
        except Exception:
            await self.db.rollback()
            value = await self.get(investigation_id)
            await self._fail(value, InvestigationStatus.FAILED, "investigation_failed", started)

    async def _reference_time(self, ticket: Ticket, is_demo: bool) -> tuple[datetime, str]:
        if not is_demo:
            return ticket.created_at, "ticket_created_at"
        text = f"{ticket.title} {ticket.description} {ticket.category or ''}".casefold()
        service: str | None = None
        if (
            "vpn" in text
            and "dallas" in f"{ticket.location or ''} {text}"
            and "payroll" in f"{ticket.application or ''} {text}"
        ):
            service = "DNS"
        elif any(token in text for token in ("microsoft 365", "m365", "outlook")):
            service = "Microsoft 365"
        elif (
            any(token in text for token in ("wi-fi", "wifi", "wireless"))
            and (ticket.location or "").casefold() == "chicago"
        ):
            service = "Wi-Fi"
        elif any(token in text for token in ("password", "mfa", "account lockout")):
            service = "Active Directory"
        elif ticket.application and any(token in text for token in ("outage", "unavailable")):
            service = ticket.application
        if service is None:
            return ticket.created_at, "ticket_created_at"
        location = await self.operational.location(ticket.location) if ticket.location else None
        application = (
            await self.operational.application(ticket.application) if ticket.application else None
        )
        incident = await self.operational.curated_incident(
            service,
            location.source_id if location else None,
            application.source_id if application and service == "DNS" else None,
        )
        if incident is None:
            return ticket.created_at, "ticket_created_at"
        return _midpoint(incident), "curated_demo_scenario"

    def _persist_steps(
        self, value: Investigation, plan: list[PlannedTool], output: InvestigationState
    ) -> None:
        self._planning_step(value, plan)
        for order, observation in enumerate(output["observations"], 2):
            self.repository.add(
                InvestigationStep(
                    investigation_id=value.id,
                    step_key=observation["step_key"],
                    step_order=order,
                    label=observation["label"],
                    tool_name=observation["tool_name"],
                    status=InvestigationStepStatus.FAILED
                    if observation["error_code"]
                    else InvestigationStepStatus.COMPLETED,
                    sanitized_inputs=observation["input_summary"],
                    result=observation["result"]
                    if observation["error_code"] is None
                    else {"error_code": observation["error_code"]},
                    source_count=observation["source_count"],
                    duration_ms=observation["duration_ms"],
                )
            )

    def _planning_step(self, value: Investigation, plan: list[PlannedTool]) -> None:
        self.repository.add(
            InvestigationStep(
                investigation_id=value.id,
                step_key="classification-planning",
                step_order=1,
                label="Classification and bounded tool planning",
                tool_name=None,
                status=InvestigationStepStatus.COMPLETED,
                sanitized_inputs={"analysis_id": str(value.analysis_id)},
                result={"planned_tools": _safe_plan(plan)},
                source_count=1,
                duration_ms=0,
            )
        )

    async def _fail(
        self,
        value: Investigation,
        status: InvestigationStatus,
        error_code: str,
        started: float | None = None,
    ) -> None:
        value.status = status
        value.error_code = error_code
        value.completed_at = datetime.now(UTC)
        if started is not None:
            value.duration_ms = max(0, round((monotonic() - started) * 1000))
        self._record(
            value,
            "timed_out" if status == InvestigationStatus.TIMED_OUT else "failed",
            "Investigation timed out"
            if status == InvestigationStatus.TIMED_OUT
            else "Investigation failed",
            "ticket.investigation.timed_out"
            if status == InvestigationStatus.TIMED_OUT
            else "ticket.investigation.failed",
            {"error_code": error_code},
        )
        await self._commit(value)

    def _record(
        self,
        value: Investigation,
        event_type: str,
        summary: str,
        action: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.repository.add(
            TicketEvent(
                ticket_id=value.ticket_id,
                actor_id=value.requested_by_id,
                event_type=event_type,
                summary=summary,
                data=data,
            )
        )
        self.repository.add(
            AuditLog(
                actor_id=value.requested_by_id,
                action=action,
                resource_type="ticket.investigation",
                resource_id=value.id,
                data=data,
            )
        )

    async def _commit(self, value: Investigation) -> None:
        try:
            await self.db.commit()
            await self.db.refresh(value)
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError from exc
        except Exception:
            await self.db.rollback()
            raise


def _safe_plan(plan: list[PlannedTool]) -> list[dict[str, Any]]:
    return [
        {
            "step_key": item["step_key"],
            "label": item["label"],
            "tool_name": item["tool_name"],
            "input_keys": sorted(item["arguments"]),
        }
        for item in plan
    ]


def _midpoint(incident: SyntheticIncident) -> datetime:
    return incident.start_at + (incident.end_at - incident.start_at) / 2


async def run_investigation_job(
    investigation_id: UUID,
    *,
    settings: Settings | None = None,
    session_maker: async_sessionmaker[AsyncSession] | Callable[[], Any] = session_factory,
) -> None:
    async with session_maker() as db:
        await InvestigationService(db, settings).execute(investigation_id)
