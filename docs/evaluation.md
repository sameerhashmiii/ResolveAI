# Evaluation And Observability

## Scope

ResolveAI Phase 9 measures the deterministic local-demo workflow against a hidden, wholly synthetic evaluation set. These results demonstrate reproducibility and product instrumentation; they do not estimate production accuracy or performance on real organizations.

The checked-in `data/evaluation/ground_truth.json` contains 150 versioned cases. `data/manifest.json` records its SHA-256 checksum and evaluation schema version. Evaluation data is excluded from operational ingestion and product APIs.

## Reproduce A Run

Start PostgreSQL, apply migrations through `20260911_0008`, and ingest the checked-in knowledge corpus. From `backend/`, run:

```bash
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai \
.venv/bin/python ../evaluation/run_eval.py
```

`--limit N` runs the first `N` cases for bounded development checks. The release acceptance run uses all 150 cases.

The command verifies the evaluation checksum before scoring, prints a deterministic JSON report, and persists one aggregate `evaluation_runs` record. Failed executions retain only a safe error code and provenance.

## Metrics

- Classification accuracy is exact agreement with the explicit AI taxonomy label.
- Priority accuracy is exact agreement after applying the production deterministic priority policy. Under-prioritization is reported separately.
- Retrieval recall@5, precision@5, and mean reciprocal rank use article IDs. Duplicate chunks from one article count once. Queries use ticket title and description without expected-category filtering.
- Response rubric rates measure uncertainty language, recommendation grounding, escalation language where required, professional structure, and absence of unsupported completed-action claims.

Every report includes eligible denominators, dataset and runner versions, provider and embedding identifiers, checksum, synthetic status, and methodology. Empty eligible sets are reported as unavailable rather than as measured zero accuracy.

## Product Surfaces

- `GET /api/v1/analytics/overview` returns authenticated operational snapshots with source, window, denominator, and methodology labels.
- `GET /api/v1/analytics/evaluation-summary` returns the latest completed aggregate evaluation to authenticated analysts.
- `GET /api/v1/analytics/ai-performance` is Manager-only and returns only the latest completed aggregate evaluation.
- `GET /api/v1/admin/health` is Administrator-only and returns sanitized component status and check latency.
- `/admin/observability` presents these measurements to administrators and explicitly distinguishes workflow completion from evaluation accuracy.

Responses use `Cache-Control: no-store`. No endpoint exposes hidden expected outcomes, per-case results, ticket descriptions, prompts, model responses, database addresses, credentials, SQL, stack traces, or raw logs.

## Limitations

- The generator and deterministic local provider share a synthetic domain, so evaluation outcomes are not independently adjudicated.
- Relevant knowledge articles are deterministic synthetic relevance judgments rather than human relevance assessments.
- The response rubric checks bounded observable criteria; it is not a substitute for human review.
- Hosted model behavior is not included in the default reproducible run.
