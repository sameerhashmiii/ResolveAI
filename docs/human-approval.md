# Human Approval And Resolution

## Principle

ResolveAI separates AI assistance from human authority. Recommendations and generated communication are drafts until a named authenticated user records a decision. No endpoint performs account, access, credential, infrastructure, or delivery actions.

```text
Completed assessment
  -> proposed recommendation
  -> human approve / reject / modify
  -> grounded response draft
  -> human edit
  -> human response approval (not delivery)
  -> explicit resolve OR explicit internal escalation
  -> immutable activity and audit records
```

## Recommendation Decisions

Every completed assessment creates exactly one proposed recommendation. Existing completed assessments are backfilled during migration `0007`.

Decision options:

- **Approve:** accept the original instructions.
- **Reject:** stop the assisted resolution path.
- **Modify:** replace instructions and accept the human-authored version.

Every decision requires a reason and records actor, timestamp, ticket event, and audit entry. A decided recommendation cannot be silently decided again.

## High-Impact Policy

Deterministic policy detects instructions involving account reset, MFA reset, credential reset, permission/access changes, account unlock/disable, grant, or revoke operations. Approving or modifying these recommendations requires the Manager or Administrator role.

The policy checks common action word orders such as both `MFA reset` and `reset MFA`. Escalating a case does not execute a high-impact recommendation.

## Grounded Response Drafts

Response generation receives only bounded ticket context, the probable inference, limitations, and human-accepted recommendation. Local mode creates a deterministic professional draft; optional hosted mode uses strict structured output with one repair attempt.

Generated text must:

- Use uncertainty language such as “appears,” “probable,” or “based on evidence.”
- Recommend only accepted instructions.
- Avoid claims that ResolveAI reset, changed, restored, sent, disabled, enabled, fixed, resolved, unlocked, granted, or revoked anything.

The same unsupported-action check applies to human-edited drafts because the product has no recorded remediation executor. Unsafe text is rejected with a validation error rather than approved.

## Approval Is Not Sending

Response states are only `draft`, `approved`, and `rejected`. There is no `sent` state, `sent_at` field, send endpoint, or delivery adapter.

Approval copies the current saved/edited draft into `final_body`, records the approver and timestamp, and emits an event explicitly stating that no delivery occurred. The API returns `approval_semantics=approval_only_not_sent`.

## Ticket Outcomes

### Resolve

The dedicated resolve endpoint requires:

- A nonterminal ticket
- An approved response belonging to the ticket
- A final response body
- An approved or modified recommendation belonging to the ticket
- A human-authored resolution summary

The transaction sets ticket status and resolution timestamp/summary and marks the recommendation completed. It records that response delivery was not performed.

### Escalate

The dedicated escalation endpoint requires a completed assessment, destination, and reason. It records internal routing only. If the proposal itself was an escalation, the explicit routing action completes that recommendation with human decision metadata.

Generic ticket PATCH accepts only `new` and `in_progress`; it cannot resolve or escalate. Terminal tickets cannot be reopened, reassigned, re-decided, edited, or approved through ordinary workflow APIs.

## Concurrency

Rows are locked with PostgreSQL `FOR UPDATE OF` scoped to the primary table so eager-loaded nullable relationships do not broaden locks to outer joins. Unique active-draft constraints and state checks prevent duplicate decisions and conflicting outcomes.

## APIs

- `GET /api/v1/tickets/{ticket_id}/recommendations/latest`
- `POST /api/v1/recommendations/{recommendation_id}/decision`
- `GET /api/v1/tickets/{ticket_id}/responses/latest`
- `POST /api/v1/tickets/{ticket_id}/responses`
- `PATCH /api/v1/responses/{response_id}`
- `POST /api/v1/responses/{response_id}/approve`
- `POST /api/v1/responses/{response_id}/reject`
- `POST /api/v1/tickets/{ticket_id}/resolve`
- `POST /api/v1/tickets/{ticket_id}/escalate`

All require authentication. Mutations require CSRF protection.

## Future Delivery

A future real delivery adapter would need explicit configuration, destination validation, delivery receipts, retries, authorization, audit events, and a distinct user action. Approval alone would still not be treated as proof of delivery.
