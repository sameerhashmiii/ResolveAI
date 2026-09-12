# AI Triage Design

## Scope

Phase 4 implements ticket triage only: category classification, entity extraction, impact signals, deterministic priority assignment, and human override. It does not claim a root cause, retrieve knowledge, correlate incidents, or recommend remediation. Those capabilities require later evidence-backed phases.

## Trust Boundary

```text
Validated ticket input
        -> provider adapter
        -> strict ProviderSignals schema
        -> deterministic priority policy
        -> persisted advisory analysis
        -> human review or override
```

The provider cannot update a ticket, choose the persisted priority directly, invoke tools, or perform an action. It returns only category, confidence, entities, and boolean/scope factors. Pydantic rejects unknown fields, invalid enums, out-of-range confidence, and oversized entity strings.

Ticket content is treated as untrusted data. The hosted system contract instructs the model to ignore instructions embedded in ticket text. Regardless of prompt behavior, the strict schema and deterministic policy prevent provider output from bypassing allowed fields.

## Provider Modes

### Local Demo

`RESOLVEAI_AI_MODE=local_demo` is the zero-configuration default. It uses versioned deterministic keyword and symptom rules. The API and UI label this output as a deterministic demo analysis and never imply that an LLM was called.

This mode makes recruiter demonstrations predictable and supports offline development, tests, and failure handling without paid services.

### Hosted Structured Model

`RESOLVEAI_AI_MODE=openai_compatible` uses an explicitly configured `/chat/completions` endpoint with JSON-schema response formatting, temperature zero, timeout enforcement, and one constrained malformed-output repair attempt.

Required configuration:

- `RESOLVEAI_LLM_BASE_URL`
- `RESOLVEAI_LLM_MODEL`
- `RESOLVEAI_LLM_API_KEY`

The API key is held as a Pydantic `SecretStr`, sent only in the authorization header, and never persisted or logged. Missing hosted configuration returns a safe service-unavailable response rather than a stack trace.

## Structured Signals

Allowed categories:

- VPN
- Network
- Wi-Fi
- Email
- Password
- Account Access
- Hardware
- Software
- Application
- Security
- Other

Extracted entities contain user, location, application, device, issue type, affected scope, and urgency. Priority factors contain affected scope, business criticality, production outage, security risk, workaround availability, and information-request status.

## Priority Policy

| Priority | Deterministic conditions |
|---|---|
| P1 Critical | Explicit production outage, organization-wide scope, and critical urgency |
| P2 High | Security risk; multi-user/organization high impact; or business-critical function without a workaround |
| P3 Medium | Individual or ordinary productivity-impacting incident not matching P1/P2/P4 |
| P4 Low | Information request or low urgency without critical, outage, or security factors |

Urgency language alone cannot create P1. The primary VPN-connected/PayrollPro-unavailable scenario is P2 because a critical business workflow is blocked without a stated workaround, not because the provider arbitrarily selected P2.

## Workflow Lifecycle

1. An authenticated analyst requests analysis with CSRF protection.
2. ResolveAI rejects duplicate queued/running analysis for the same ticket.
3. A queued record, activity event, and audit entry commit atomically.
4. A bounded background task opens a fresh database session and marks the analysis running.
5. Provider output is validated and passed to priority policy.
6. Completed analysis updates ticket category and priority unless a human priority override already exists.
7. Timeout, unavailable provider, invalid output, and unexpected failure become safe persisted states with stable error codes.
8. Failed/timed-out analysis can be explicitly retried.

The UI polls only while status is queued or running. It displays provider mode, workflow version, confidence, entities, factors, duration, and manual-review status.

## Human Override

An analyst can override priority only by selecting P1-P4 and supplying a reason. The decision updates the ticket and writes an immutable ticket event and audit record in one transaction. Later analyses retain their own recommendation but cannot overwrite a human override.

## Limitations

- Local rules are deterministic product behavior, not machine-learning accuracy.
- Hosted integration is tested with mocked HTTP and requires user-supplied compatible credentials.
- Confidence currently represents category signal strength and has not yet been calibrated against the Phase 3 ground-truth dataset.
- Background tasks are suitable for the current single-instance portfolio deployment. A production multi-instance deployment would move jobs to a durable worker queue while retaining the same persisted lifecycle.
- No evidence or root-cause statement is produced in this phase.
