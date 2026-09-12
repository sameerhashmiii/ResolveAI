from app.root_cause.schemas import (
    ConfidenceFactor,
    ConfidenceResult,
    EvidenceSnapshot,
    GroundedInference,
)


def calculate_confidence(
    inference: GroundedInference, evidence: list[EvidenceSnapshot]
) -> ConfidenceResult:
    service = _candidate_service(inference, evidence)
    incident = _matching(evidence, "incident", service)
    statuses = _matching(evidence, "system_status", service)
    degraded = [item for item in statuses if item.metadata.get("state") in {"degraded", "outage"}]
    healthy = [item for item in statuses if item.metadata.get("state") == "operational"]
    telemetry = _matching(evidence, "telemetry", service)
    if not telemetry:
        telemetry = [item for item in degraded if _has_anomalous_measurement(item)]
    logs = _matching(evidence, "log", service)
    incident_ids = {item.source_id for item in incident}
    similar = [
        item
        for item in evidence
        if item.evidence_type == "similar_ticket"
        and (
            item.metadata.get("incident_id") in incident_ids
            or _matches_service(item, service)
        )
    ]
    knowledge = [
        item
        for item in _matching(evidence, "knowledge_chunk", service)
        if item.relevance_score is None or item.relevance_score >= 0.45
    ]
    agreeing_types = sum(bool(items) for items in (incident, degraded, telemetry, logs))
    specifications = [
        ("base", "Base grounded assessment", 0.25, True, []),
        ("public_incident", "Related public incident", 0.18, bool(incident), incident),
        ("degraded_status", "Matching degraded system status", 0.12, bool(degraded), degraded),
        ("anomalous_telemetry", "Matching anomalous telemetry", 0.10, bool(telemetry), telemetry),
        ("warning_error_log", "Matching warning or error log", 0.10, bool(logs), logs),
        ("similar_tickets", "Aligned similar resolved tickets", 0.08, bool(similar), similar),
        ("relevant_knowledge", "Relevant knowledge", 0.05, bool(knowledge), knowledge),
        (
            "cross_source_agreement",
            "Agreement across operational source types",
            0.03,
            agreeing_types >= 3,
            incident + degraded + telemetry + logs,
        ),
        (
            "operational_contradiction",
            "Matching operational status contradicts the candidate",
            -0.12,
            bool(healthy),
            healthy,
        ),
    ]
    factors = [
        ConfidenceFactor(
            key=key,
            label=label,
            weight=weight,
            applied=applied,
            source_ids=[item.source_id for item in sources],
        )
        for key, label, weight, applied, sources in specifications
    ]
    score = 0.0
    for factor in factors:
        if factor.applied:
            score += factor.weight
    return ConfidenceResult(score=round(min(0.95, max(0.05, score)), 2), factors=factors)


def _candidate_service(
    inference: GroundedInference, evidence: list[EvidenceSnapshot]
) -> str | None:
    text = f"{inference.inference_key} {inference.probable_root_cause}".casefold()
    services = {
        str(item.metadata["service"]).casefold(): str(item.metadata["service"])
        for item in evidence
        if item.metadata.get("service")
    }
    for normalized, original in services.items():
        if normalized in text:
            return original
    return None


def _matching(
    evidence: list[EvidenceSnapshot], evidence_type: str, service: str | None
) -> list[EvidenceSnapshot]:
    values = [item for item in evidence if item.evidence_type == evidence_type]
    if service is None:
        return values
    return [
        item
        for item in values
        if _matches_service(item, service)
    ]


def _matches_service(item: EvidenceSnapshot, service: str | None) -> bool:
    if service is None:
        return True
    return (
        str(item.metadata.get("service", "")).casefold() == service.casefold()
        or service.casefold() in f"{item.title} {item.excerpt}".casefold()
    )


def _has_anomalous_measurement(item: EvidenceSnapshot) -> bool:
    availability = item.metadata.get("availability")
    latency = item.metadata.get("latency_ms")
    errors = item.metadata.get("error_rate")
    return (
        isinstance(availability, int | float)
        and availability < 99
        or isinstance(latency, int | float)
        and latency >= 500
        or isinstance(errors, int | float)
        and errors >= 2
    )
