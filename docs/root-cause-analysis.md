# Root-Cause Analysis And Trust

## Product Boundary

Phase 7 converts a completed, persisted investigation into a separate probable-cause assessment. It does not confirm a diagnosis, execute remediation, approve a response, or resolve a ticket.

```text
Persisted investigation steps
        -> known-shape evidence normalization
        -> grounded inference provider
        -> citation subset validation
        -> deterministic confidence-v1
        -> escalation gate
        -> human-readable assessment and explanation
```

The UI always orders observed evidence before inference and recommendation.

## Evidence Normalization

Only completed, known Phase 6 tool results are eligible. The collector understands exact shapes for knowledge chunks, similar resolved tickets, system status, anomalous telemetry, warning/error logs, public incidents, and ticket history.

Every evidence item contains:

- Evidence type
- Persisted source ID
- Source title
- Bounded exact excerpt or observation summary
- Concise statement of what the source supports
- Optional retrieval relevance
- Safe service/location/time metadata

Entries without real source IDs are ignored. Source IDs are deterministically deduplicated, excerpts are limited to 1,200 characters, and per-type caps prevent prompt or UI flooding. Keys containing ground truth, hidden/private data, secrets, or chain-of-thought markers cause that untrusted result to be excluded.

The operational importer never reads the ground-truth file, so assessment code cannot retrieve it from PostgreSQL.

## Inference Providers

### Deterministic Demo

The local provider correlates public incident facts with matching degraded status, telemetry, and logs. For the primary Dallas scenario it returns:

- Probable root cause: `Dallas DNS service degradation`
- Inference key: `dns_service_degradation`
- Recommendation: verify resolver path, reconnect VPN, and escalate to Network Operations if persistent

This output is labeled **Deterministic demo inference**. It is not represented as an LLM call.

### Hosted Grounded Model

Optional OpenAI-compatible mode receives only bounded ticket context and normalized evidence. It must return strict JSON with a probable cause, key, recommendation, selected source IDs, and limitations. It cannot return confidence.

The adapter treats evidence as untrusted content, requires citations to be a subset of supplied IDs, uses temperature zero and timeout controls, and permits one malformed-output repair attempt. Raw prompts and responses are not persisted or logged.

## Confidence V1

Confidence is a deterministic evidence-coverage score, not measured model accuracy.

| Factor | Weight |
|---|---:|
| Base grounded assessment | +0.25 |
| Related public incident | +0.18 |
| Matching degraded status | +0.12 |
| Matching anomalous telemetry | +0.10 |
| Matching warning/error log | +0.10 |
| Aligned similar resolved tickets | +0.08 |
| Relevant knowledge guidance | +0.05 |
| Agreement across operational source types | +0.03 |
| Matching operational status contradiction | -0.12 |

Scores are clamped to 0.05-0.95. Healthy VPN status does not contradict a DNS candidate; contradictions must match the inferred service. Similar tickets align by incident source or matching service. Under `local-hash-v1`, relevant knowledge for this formula uses a documented 0.45 retrieval threshold because verified DNS-specific primary sources score approximately 0.46-0.48.

The complete primary evidence pattern scores 0.91. Weak evidence remains below the default 0.70 threshold. A matching operational contradiction lowers the score.

## Escalation

`RESOLVEAI_ROOT_CAUSE_CONFIDENCE_THRESHOLD` defaults to `0.70`.

Below threshold, the API sets escalation required and the UI states:

> AI confidence is low. Human investigation recommended.

The frontend does not calculate its own threshold. It displays the server decision, threshold, and reason.

## Show Me Why

The explanation endpoint returns:

- Safe persisted investigation labels, statuses, and source counts
- Supporting evidence already owned by the assessment
- Applied and unapplied signed confidence factors
- A fixed disclosure that hidden chain-of-thought is not stored or exposed

It does not return raw tool arguments, model prompts, hidden reasoning, or ground truth. This is auditable rationale, not chain-of-thought disclosure.

## Failure Behavior

Queued/running/completed/failed/timed-out states are persisted. Provider unavailability, invalid citations, malformed output, timeout, and missing context produce stable safe error codes. Failed assessments require escalation and can be explicitly retried; they do not update ticket status or execute an action.

## APIs

- `POST /api/v1/tickets/{ticket_id}/assessments`
- `GET /api/v1/tickets/{ticket_id}/assessments/latest`
- `GET /api/v1/assessments/{assessment_id}`
- `POST /api/v1/assessments/{assessment_id}/retry`
- `GET /api/v1/assessments/{assessment_id}/explanation`

All endpoints require authentication. Mutations also require CSRF protection.

## Remaining Human Boundary

Phase 8 introduces response drafting, recommendation approval/rejection/modification, and explicit resolve/escalate transitions. Until then, Phase 7 recommendations are display-only and no action is considered approved or sent.
