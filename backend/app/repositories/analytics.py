from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessments import RootCauseAssessment
from app.models.domain import AIAnalysis, Ticket
from app.models.enums import AnalysisStatus, InvestigationStatus, RootCauseStatus, TicketStatus
from app.models.evaluation import EvaluationRun
from app.models.operational import DatasetImport, Investigation


@dataclass(frozen=True)
class TicketAggregate:
    total: int
    open: int
    resolved: int
    escalated: int
    window_start: datetime | None
    window_end: datetime | None


@dataclass(frozen=True)
class WorkflowAggregate:
    total: int
    completed: int
    failed: int
    median_latency_ms: float | None
    window_start: datetime | None
    window_end: datetime | None
    workflow_versions: list[str]


class AnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ticket_counts(self) -> TicketAggregate:
        row = (
            await self.db.execute(
                select(
                    func.count(Ticket.id),
                    func.count(Ticket.id).filter(
                        Ticket.status.in_([TicketStatus.NEW, TicketStatus.IN_PROGRESS])
                    ),
                    func.count(Ticket.id).filter(Ticket.status == TicketStatus.RESOLVED),
                    func.count(Ticket.id).filter(Ticket.status == TicketStatus.ESCALATED),
                    func.min(Ticket.created_at),
                    func.max(Ticket.created_at),
                )
            )
        ).one()
        return TicketAggregate(
            total=int(row[0] or 0),
            open=int(row[1] or 0),
            resolved=int(row[2] or 0),
            escalated=int(row[3] or 0),
            window_start=row[4],
            window_end=row[5],
        )

    async def analysis_workflow(self) -> WorkflowAggregate:
        return await self._workflow_aggregate(
            AIAnalysis,
            completed=AnalysisStatus.COMPLETED,
            failed=(AnalysisStatus.FAILED, AnalysisStatus.TIMED_OUT),
        )

    async def investigation_workflow(self) -> WorkflowAggregate:
        return await self._workflow_aggregate(
            Investigation,
            completed=InvestigationStatus.COMPLETED,
            failed=(InvestigationStatus.FAILED, InvestigationStatus.TIMED_OUT),
        )

    async def assessment_workflow(self) -> WorkflowAggregate:
        return await self._workflow_aggregate(
            RootCauseAssessment,
            completed=RootCauseStatus.COMPLETED,
            failed=(RootCauseStatus.FAILED, RootCauseStatus.TIMED_OUT),
        )

    async def active_dataset_version(self) -> str | None:
        return cast(
            str | None,
            await self.db.scalar(
                select(DatasetImport.dataset_version)
                .where(DatasetImport.status == "completed")
                .order_by(DatasetImport.completed_at.desc())
                .limit(1)
            ),
        )

    async def _workflow_aggregate(
        self, model: Any, *, completed: object, failed: tuple[object, ...]
    ) -> WorkflowAggregate:
        row = (
            await self.db.execute(
                select(
                    func.count(model.id),
                    func.count(model.id).filter(model.status == completed),
                    func.count(model.id).filter(model.status.in_(failed)),
                    func.percentile_cont(0.5)
                    .within_group(
                        case((model.status == completed, model.duration_ms), else_=None)
                    ),
                    func.min(model.created_at),
                    func.max(model.created_at),
                    func.array_agg(func.distinct(model.workflow_version)),
                )
            )
        ).one()
        return WorkflowAggregate(
            total=int(row[0] or 0),
            completed=int(row[1] or 0),
            failed=int(row[2] or 0),
            median_latency_ms=float(row[3]) if row[3] is not None else None,
            window_start=row[4],
            window_end=row[5],
            workflow_versions=sorted(value for value in (row[6] or []) if value),
        )

    async def latest_completed_evaluation(self) -> EvaluationRun | None:
        return cast(
            EvaluationRun | None,
            await self.db.scalar(
                select(EvaluationRun)
                .where(EvaluationRun.status == "completed")
                .order_by(EvaluationRun.completed_at.desc(), EvaluationRun.created_at.desc())
                .limit(1)
            ),
        )
