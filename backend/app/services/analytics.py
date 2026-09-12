import re
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.repositories.analytics import AnalyticsRepository, WorkflowAggregate
from app.schemas.analytics import (
    AIPerformanceResponse,
    AnalyticsOverview,
    EvaluationProvenance,
    EvaluationRunResponse,
    MetricProvenance,
    TicketCountMetric,
    WorkflowMetric,
)

_HIDDEN_DATA_KEY = re.compile(
    r"body|case|ticket|prompt|input|output|expected|ground.?truth|message|email|"
    r"description|excerpt|content|customer|requester",
    re.IGNORECASE,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.repository = AnalyticsRepository(db)

    async def overview(self) -> AnalyticsOverview:
        tickets = await self.repository.ticket_counts()
        analyses = await self.repository.analysis_workflow()
        investigations = await self.repository.investigation_workflow()
        assessments = await self.repository.assessment_workflow()
        dataset_version = await self.repository.active_dataset_version()
        ticket_provenance = MetricProvenance(
            synthetic=True,
            data_source="operational tickets database",
            methodology="Current status counts across all operational tickets.",
            sample_count=tickets.total,
            window_start=tickets.window_start,
            window_end=tickets.window_end,
            dataset_version=dataset_version,
            workflow_versions=[],
        )
        return AnalyticsOverview(
            synthetic=True,
            source="stored operational database snapshot",
            methodology=(
                "Current ticket statuses and stored workflow outcomes; no live workflow calls."
            ),
            measured_at=datetime.now(UTC),
            dataset_version=dataset_version or "not_applicable",
            tickets=TicketCountMetric(
                total_tickets=tickets.total,
                open_tickets=tickets.open,
                resolved_tickets=tickets.resolved,
                escalated_tickets=tickets.escalated,
                resolution_rate=tickets.resolved / tickets.total if tickets.total else 0.0,
                sample_count=tickets.total,
                provenance=ticket_provenance,
            ),
            workflows=[
                self._workflow_metric("analysis", analyses),
                self._workflow_metric("investigation", investigations),
                self._workflow_metric("assessment", assessments),
            ],
        )

    async def ai_performance(self) -> AIPerformanceResponse:
        run = await self.repository.latest_completed_evaluation()
        if run is None:
            return AIPerformanceResponse(
                synthetic=True,
                source="stored completed evaluation runs",
                methodology="Latest completed run by completion time; no live workflow calls.",
                latest_run=None,
            )
        if run.completed_at is None:
            raise NotFoundError
        provenance = EvaluationProvenance(
            synthetic=bool(run.synthetic),
            data_source="stored completed evaluation run",
            methodology="Stored aggregate metrics only; no per-case records or ground truth.",
            sample_count=run.sample_count,
            window_start=run.started_at,
            window_end=run.completed_at,
            dataset_version=run.dataset_version,
            dataset_checksum=run.dataset_checksum,
            workflow_versions=[run.workflow_version],
            runner_version=run.runner_version,
            provider=run.provider,
            model=run.model,
        )
        return AIPerformanceResponse(
            synthetic=bool(run.synthetic),
            source="stored completed evaluation runs",
            methodology="Latest completed run by completion time; no live workflow calls.",
            latest_run=EvaluationRunResponse(
                id=str(run.id),
                dataset_version=run.dataset_version,
                dataset_checksum=run.dataset_checksum,
                runner_version=run.runner_version,
                workflow_version=run.workflow_version,
                provider=run.provider,
                model=run.model,
                sample_count=run.sample_count,
                metrics=self._safe_aggregate(run.metrics),
                methodology=self._safe_methodology(run.methodology),
                completed_at=run.completed_at,
                provenance=provenance,
            ),
        )

    @staticmethod
    def _workflow_metric(
        workflow: Literal["analysis", "investigation", "assessment"],
        aggregate: WorkflowAggregate,
    ) -> WorkflowMetric:
        denominator = aggregate.total
        provenance = MetricProvenance(
            synthetic=True,
            data_source=f"stored operational {workflow} workflow runs",
            methodology=(
                "Rates use all stored runs as the denominator; failures include failed and "
                "timed-out runs; latency is the median duration of completed runs only."
            ),
            sample_count=denominator,
            window_start=aggregate.window_start,
            window_end=aggregate.window_end,
            dataset_version=None,
            workflow_versions=aggregate.workflow_versions,
        )
        return WorkflowMetric(
            name=workflow,
            workflow_version=", ".join(aggregate.workflow_versions) or "not_available",
            total=denominator,
            completed=aggregate.completed,
            failed=aggregate.failed,
            completion_rate=aggregate.completed / denominator if denominator else 0.0,
            failure_rate=aggregate.failed / denominator if denominator else 0.0,
            median_duration_ms=aggregate.median_latency_ms or 0.0,
            provenance=provenance,
        )

    @staticmethod
    def _safe_aggregate(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        result: dict[str, Any] = {}
        for key, metric in list(value.items())[:50]:
            if _HIDDEN_DATA_KEY.search(str(key)):
                continue
            if isinstance(metric, dict):
                result[str(key)] = AnalyticsService._safe_aggregate(metric)
            elif isinstance(metric, (int, float)) and not isinstance(metric, bool):
                result[str(key)] = metric
        return result

    @staticmethod
    def _safe_methodology(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {
            str(key): item
            for key, item in list(value.items())[:30]
            if not _HIDDEN_DATA_KEY.search(str(key))
            and isinstance(item, (str, int, float, bool))
            and len(str(item)) <= 500
        }
