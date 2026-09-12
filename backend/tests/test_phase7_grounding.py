from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.ai.providers import InvalidProviderResponse, ProviderUnavailable
from app.models.domain import AIAnalysis, Ticket
from app.models.enums import (
    AnalysisStatus,
    InvestigationStatus,
    InvestigationStepStatus,
    TicketStatus,
)
from app.models.operational import Investigation, InvestigationStep
from app.root_cause.confidence import calculate_confidence
from app.root_cause.evidence import EXCERPT_LIMIT, collect_evidence
from app.root_cause.providers import (
    LocalGroundedInferenceProvider,
    OpenAICompatibleGroundedProvider,
)
from app.root_cause.schemas import EvidenceSnapshot, GroundedInference, GroundedInferenceInput


def evidence(
    kind: str, source: str, *, service: str | None = "DNS", state: str | None = None
) -> EvidenceSnapshot:
    metadata = {"service": service} if service else {}
    if state:
        metadata["state"] = state
    return EvidenceSnapshot(
        evidence_type=kind,
        source_id=source,
        title=f"DNS {kind}",
        excerpt="Dallas DNS degradation observed",
        supports="A decision factor",
        relevance_score=0.9 if kind == "knowledge_chunk" else None,
        metadata=metadata,
    )


def primary_evidence() -> list[EvidenceSnapshot]:
    return [
        evidence("incident", "incident:1"),
        evidence("system_status", "status:1", state="degraded"),
        evidence("telemetry", "telemetry:1"),
        evidence("log", "log:1"),
        evidence("similar_ticket", "ticket:old"),
        evidence("knowledge_chunk", "knowledge:1"),
    ]


def inference_input(items: list[EvidenceSnapshot]) -> GroundedInferenceInput:
    return GroundedInferenceInput(
        ticket_id=uuid4(),
        title="VPN connected but PayrollPro is unavailable",
        description="Dallas user cannot reach PayrollPro",
        location="Dallas",
        application="PayrollPro",
        evidence=items,
    )


async def test_local_primary_and_weak_inference_are_cautious() -> None:
    provider = LocalGroundedInferenceProvider()
    primary = await provider.infer(inference_input(primary_evidence()))
    assert primary.probable_root_cause == "Dallas DNS service degradation"
    assert primary.inference_key == "dns_service_degradation"
    assert set(primary.selected_source_ids) <= {item.source_id for item in primary_evidence()}
    assert "probable cause" in primary.recommended_action

    weak_item = evidence("ticket_fact", "ticket:1", service=None)
    weak = await provider.infer(inference_input([weak_item]))
    assert weak.probable_root_cause == "Insufficient correlated evidence"
    assert "human investigation" in weak.recommended_action


def test_confidence_v1_primary_weak_contradiction_and_factor_sum() -> None:
    probable = GroundedInference(
        probable_root_cause="Dallas DNS service degradation",
        inference_key="dns_service_degradation",
        recommended_action="Verify DNS and escalate if persistent",
        selected_source_ids=[],
        limitations=[],
    )
    primary = calculate_confidence(probable, primary_evidence())
    assert primary.version == "confidence-v1"
    assert primary.score == pytest.approx(0.91)
    assert primary.score == pytest.approx(
        sum(item.weight for item in primary.factors if item.applied)
    )
    assert calculate_confidence(probable, []).score < 0.70

    contradictory = primary_evidence() + [
        evidence("system_status", "status:healthy", state="operational")
    ]
    assert calculate_confidence(probable, contradictory).score == pytest.approx(0.79)
    assert "confidence" not in GroundedInference.model_fields
    with pytest.raises(ValueError):
        GroundedInference.model_validate(
            {
                **probable.model_dump(),
                "confidence": 0.99,
            }
        )


def test_deduplicated_status_observation_can_supply_telemetry_factor() -> None:
    probable = GroundedInference(
        probable_root_cause="Dallas DNS service degradation",
        inference_key="dns_service_degradation",
        recommended_action="Verify DNS",
        selected_source_ids=[],
        limitations=[],
    )
    items = primary_evidence()
    items = [item for item in items if item.evidence_type != "telemetry"]
    status = next(item for item in items if item.evidence_type == "system_status")
    status.metadata.update({"availability": 91.0, "latency_ms": 600, "error_rate": 8.0})
    result = calculate_confidence(probable, items)
    telemetry_factor = next(
        item for item in result.factors if item.key == "anomalous_telemetry"
    )
    assert telemetry_factor.applied
    assert telemetry_factor.source_ids == [status.source_id]


def test_evidence_normalization_all_shapes_bounds_dedupes_and_rejects_hidden() -> None:
    now = datetime.now(UTC)
    ticket = Ticket(
        id=uuid4(),
        number=1700,
        title="VPN connected but PayrollPro unavailable",
        description="x" * 2000,
        requester_name="Requester",
        location="Dallas",
        application="PayrollPro",
        created_by_id=uuid4(),
        status=TicketStatus.NEW,
        created_at=now,
        updated_at=now,
    )
    analysis = AIAnalysis(
        id=uuid4(),
        ticket_id=ticket.id,
        requested_by_id=uuid4(),
        workflow_version="4.0",
        provider="local_demo",
        mode="local_demo",
        status=AnalysisStatus.COMPLETED,
        requires_manual_review=False,
        created_at=now,
    )
    results = [
        (
            "search_knowledge_base",
            {
                "items": [
                    {
                        "source_id": "k1",
                        "title": "DNS guide",
                        "excerpt": "z" * 2000,
                        "relevance_score": 0.9,
                    }
                ]
            },
        ),
        (
            "search_similar_tickets",
            {
                "items": [
                    {
                        "source_id": "s1",
                        "title": "Same symptom",
                        "description": "VPN symptom",
                        "resolution": "Reset resolver",
                        "similarity": 0.8,
                    }
                ]
            },
        ),
        (
            "get_ticket_history",
            {
                "events": [
                    {
                        "source_id": "h1",
                        "event_type": "created",
                        "summary": "Ticket created",
                        "created_at": now.isoformat(),
                    }
                ]
            },
        ),
        (
            "get_system_status",
            {
                "services": [
                    {
                        "source_id": "st1",
                        "service": "DNS",
                        "location": "Dallas",
                        "state": "degraded",
                        "timestamp": now.isoformat(),
                    }
                ]
            },
        ),
        (
            "get_telemetry",
            {
                "observations": [
                    {
                        "source_id": "t1",
                        "timestamp": now.isoformat(),
                        "availability": 91.0,
                        "latency_ms": 600,
                        "error_rate": 8.0,
                    }
                ]
            },
        ),
        (
            "search_logs",
            {
                "records": [
                    {
                        "source_id": "l1",
                        "severity": "error",
                        "message": "resolver timeout",
                        "timestamp": now.isoformat(),
                    }
                ]
            },
        ),
        (
            "get_related_incident",
            {
                "incidents": [
                    {
                        "source_id": "i1",
                        "title": "Dallas DNS",
                        "public_summary": "DNS degraded",
                        "services": ["DNS"],
                        "start_at": now.isoformat(),
                    }
                ]
            },
        ),
        (
            "search_logs",
            {
                "records": [
                    {
                        "source_id": "evil",
                        "severity": "error",
                        "message": "bad",
                        "private_secret": "do not expose",
                    }
                ]
            },
        ),
        (
            "search_knowledge_base",
            {"items": [{"source_id": "k1", "title": "duplicate", "excerpt": "duplicate"}]},
        ),
    ]
    steps = [
        InvestigationStep(
            id=uuid4(),
            investigation_id=uuid4(),
            step_key=f"step-{index}",
            step_order=index,
            label=tool,
            tool_name=tool,
            status=InvestigationStepStatus.COMPLETED,
            sanitized_inputs={"service": "DNS", "location": "Dallas"},
            result=result,
            source_count=1,
            duration_ms=1,
            created_at=now,
        )
        for index, (tool, result) in enumerate(results, 1)
    ]
    investigation = Investigation(
        id=uuid4(),
        ticket_id=ticket.id,
        analysis_id=analysis.id,
        requested_by_id=uuid4(),
        workflow_version="6.0",
        status=InvestigationStatus.COMPLETED,
        reference_time=now,
        reference_basis="ticket_created_at",
        planned_tools=[],
        created_at=now,
        steps=steps,
    )
    normalized, limitations = collect_evidence(investigation, ticket, analysis)
    assert limitations == []
    assert {item.evidence_type for item in normalized} == {
        "ticket_fact",
        "knowledge_chunk",
        "similar_ticket",
        "ticket_history",
        "system_status",
        "telemetry",
        "log",
        "incident",
    }
    assert len({item.source_id for item in normalized}) == len(normalized)
    assert "evil" not in {item.source_id for item in normalized}
    assert all(len(item.excerpt) <= EXCERPT_LIMIT for item in normalized)
    assert all("secret" not in str(item.model_dump()).casefold() for item in normalized)


async def test_hosted_adapter_valid_bad_citation_malformed_and_timeout() -> None:
    valid = GroundedInference(
        probable_root_cause="Probable DNS degradation",
        inference_key="dns_degradation",
        recommended_action="Verify DNS",
        selected_source_ids=["incident:1"],
        limitations=[],
    ).model_dump_json()

    def response(content: str) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    valid_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response(valid)))
    provider = OpenAICompatibleGroundedProvider(
        base_url="https://llm.test", api_key="key", model="model", timeout=1, client=valid_client
    )
    assert (
        await provider.infer(inference_input(primary_evidence()))
    ).inference_key == "dns_degradation"
    await valid_client.aclose()

    for content in (
        valid.replace("incident:1", "not-supplied"),
        "not-json",
    ):
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _, body=content: response(body))
        )
        bad = OpenAICompatibleGroundedProvider(
            base_url="https://llm.test", api_key="key", model="model", timeout=1, client=client
        )
        with pytest.raises(InvalidProviderResponse):
            await bad.infer(inference_input(primary_evidence()))
        await client.aclose()

    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    timeout_client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
    unavailable = OpenAICompatibleGroundedProvider(
        base_url="https://llm.test", api_key="key", model="model", timeout=1, client=timeout_client
    )
    with pytest.raises(ProviderUnavailable):
        await unavailable.infer(inference_input(primary_evidence()))
    await timeout_client.aclose()
