# API Guide

## Contract

The FastAPI application serves OpenAPI UI at `/docs`, ReDoc at `/redoc`, and JSON at `/openapi.json`. The deterministic checked-in contract is [openapi.json](openapi.json). All application routes use the `/api/v1` prefix.

## Authentication, CSRF, And Roles

`POST /auth/login` and `POST /auth/demo` return the current user plus a CSRF token and set the opaque `resolveai_session` cookie. The cookie is database-backed, HTTP-only, SameSite=Lax, path `/`, and secure when `RESOLVEAI_SESSION_COOKIE_SECURE=true`. Clients must retain the cookie.

Every business endpoint requires authentication except login, demo login, and health. Every state-changing authenticated operation requires `X-CSRF-Token` with the token returned by login or `/auth/me`. A missing/expired session returns `401`; insufficient role or invalid CSRF returns `403`.

Roles are hierarchical: `support_analyst`, `manager`, `administrator`. Most ticket workflows require any authenticated user. `/analytics/overview` requires Analyst or higher, `/analytics/ai-performance` requires Manager or higher, and `/admin/health` requires Administrator. Deterministically identified high-impact recommendation decisions also require Manager or Administrator.

## Rate Limits

Login and demo login share per-client-address fixed-window limits (default 10 per 60 seconds). Analysis, investigation, assessment, their retries, and response generation use per-user/per-route limits (default 20 per 60 seconds). A limited request returns `429`, JSON `{"detail":"Too many requests"}`, and `Retry-After`.

The limiter is memory-bound to one API process. It is neither shared across replicas nor durable across restarts. CRUD, decisions, edits, approval, resolve, and escalation are not currently rate-limited by this application control.

## Errors And Request IDs

Typical errors use FastAPI's JSON shape:

```json
{"detail": "Authentication required"}
```

Validation errors use HTTP `422` with FastAPI's structured `detail` array. Domain conflicts generally return `409`; missing resources `404`; unavailable provider configuration `503`; unsafe generated/edited response content `422`; and safe generation failures `502`. Unexpected errors return `500` with `{"detail":"Internal server error"}`.

Every response includes `X-Request-ID`. A syntactically valid client `X-Request-ID` is preserved; otherwise the API generates one. Error schemas listed in generated OpenAPI are not exhaustive because several dependency and service errors are runtime responses.

## Endpoint Inventory

All paths below are relative to `/api/v1`.

| Method | Path | Purpose / access |
|---|---|---|
| GET | `/health/live` | Process liveness; public |
| GET | `/health/ready` | Database readiness; public; may return 503 |
| POST | `/auth/login` | Password login; public and rate-limited |
| POST | `/auth/demo` | Synthetic analyst login; public and rate-limited |
| GET | `/auth/me` | Session user and CSRF token |
| POST | `/auth/logout` | Revoke session; CSRF |
| GET | `/dashboard/overview` | Ticket aggregate and recent tickets |
| GET | `/users` | Active assignment users |
| POST | `/tickets` | Create ticket; CSRF |
| GET | `/tickets` | Search/filter/paginate tickets |
| GET | `/tickets/{ticket_id}` | Ticket detail |
| PATCH | `/tickets/{ticket_id}` | Nonterminal ordinary update; CSRF |
| POST | `/tickets/{ticket_id}/assign` | Assign ticket; CSRF |
| GET | `/tickets/{ticket_id}/events` | Activity timeline |
| GET | `/tickets/{ticket_id}/audit` | Bounded application audit view; Manager+; no-store |
| POST | `/tickets/{ticket_id}/priority-override` | Human override with reason; CSRF |
| POST | `/tickets/{ticket_id}/analyses` | Queue triage; CSRF and workflow limit |
| GET | `/tickets/{ticket_id}/analyses/latest` | Latest triage |
| GET | `/analyses/{analysis_id}` | Triage by ID |
| POST | `/analyses/{analysis_id}/retry` | Retry failed/timed-out triage; CSRF and workflow limit |
| GET | `/tickets/{ticket_id}/similar` | Similar resolved synthetic tickets |
| POST | `/tickets/{ticket_id}/investigations` | Queue bounded investigation; CSRF and workflow limit |
| GET | `/tickets/{ticket_id}/investigations/latest` | Latest investigation |
| GET | `/investigations/{investigation_id}` | Investigation by ID |
| POST | `/investigations/{investigation_id}/retry` | Retry investigation; CSRF and workflow limit |
| POST | `/tickets/{ticket_id}/assessments` | Queue probable-cause assessment; CSRF and workflow limit |
| GET | `/tickets/{ticket_id}/assessments/latest` | Latest assessment |
| GET | `/assessments/{assessment_id}` | Assessment by ID |
| GET | `/assessments/{assessment_id}/explanation` | Sources and confidence factors, not chain of thought |
| POST | `/assessments/{assessment_id}/retry` | Retry assessment; CSRF and workflow limit |
| GET | `/knowledge/search` | Hybrid knowledge search |
| GET | `/knowledge/documents/{document_id}` | Persisted knowledge document and chunks |
| GET | `/tickets/{ticket_id}/recommendations/latest` | Latest proposed/decided guidance |
| POST | `/recommendations/{recommendation_id}/decision` | Approve, reject, or modify with reason; CSRF; high-impact role policy |
| POST | `/tickets/{ticket_id}/responses` | Generate response draft; CSRF and workflow limit |
| GET | `/tickets/{ticket_id}/responses/latest` | Latest response draft/decision |
| PATCH | `/responses/{response_id}` | Edit safe draft; CSRF |
| POST | `/responses/{response_id}/approve` | Approve draft only; CSRF |
| POST | `/responses/{response_id}/reject` | Reject draft with reason; CSRF |
| POST | `/tickets/{ticket_id}/resolve` | Explicit internal resolve transition; CSRF |
| POST | `/tickets/{ticket_id}/escalate` | Explicit internal routing transition; CSRF |
| GET | `/analytics/overview` | Operational aggregates; Analyst+; no-store |
| GET | `/analytics/evaluation-summary` | Latest aggregate evaluation; Analyst+; no-store |
| GET | `/analytics/ai-performance` | Latest aggregate evaluation; Manager+; no-store |
| GET | `/admin/health` | Sanitized component health; Administrator; no-store |

## Approval Is Not Delivery

Response states are `draft`, `approved`, and `rejected`; there is no sent state or send endpoint. Approval returns `approval_semantics=approval_only_not_sent`. Resolve records an internal ticket outcome after an accepted recommendation and approved response. Escalate records an internal destination and reason. Neither endpoint remediates a system, updates an external service desk, contacts a requester, or proves delivery.

## Exporting The Contract

From `backend/`:

```bash
uv run --frozen python ../scripts/export_openapi.py
git diff --exit-code ../docs/openapi.json
```

The exporter sets a non-connecting placeholder database URL and writes sorted, stable JSON. CI reruns it and fails on contract drift.
