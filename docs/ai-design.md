# AI System Design

## Current End-To-End Flow

ResolveAI separates model-like assistance, deterministic policy, persisted evidence, and human authority:

```text
validated ticket
  -> structured triage provider
  -> deterministic priority policy
  -> bounded read-only investigation
  -> normalized persisted evidence
  -> probable-cause provider
  -> deterministic evidence-confidence policy
  -> proposed recommendation
  -> human decision
  -> grounded response provider and human edit
  -> human approval (not delivery)
  -> explicit internal resolve or escalation
```

The provider cannot directly update a ticket, choose persisted priority, invoke arbitrary tools, approve guidance, execute remediation, send a response, or resolve a ticket. Provider output is constrained by strict Pydantic schemas, allowed enums, lengths, citation-subset validation, timeouts, and one bounded malformed-output repair attempt.

## Modes And Data Boundary

### Deterministic Local Demo

`RESOLVEAI_AI_MODE=local_demo` is the default and needs no key. It uses versioned keyword/symptom triage, deterministic policy, signed-hash retrieval, bounded investigation planning, synthetic evidence correlation, and response templates. The UI identifies deterministic demo output. Reproducibility is not evidence of machine-learning or production accuracy.

### Hosted OpenAI-Compatible

`RESOLVEAI_AI_MODE=openai_compatible` calls a configured `/chat/completions` endpoint with schema response formatting, temperature zero, timeout enforcement, and one constrained repair attempt. It requires `RESOLVEAI_LLM_BASE_URL`, `RESOLVEAI_LLM_MODEL`, and `RESOLVEAI_LLM_API_KEY`.

**Hosted mode transmits bounded ticket context outside the local deployment.** Triage includes bounded title and description. Assessment includes bounded ticket context plus normalized evidence and allowed source IDs. Response generation includes bounded ticket context, probable inference/limitations, and the human-accepted recommendation. Ticket and evidence text are untrusted and the prompt instructs the provider not to follow embedded instructions, but prompt controls are not a security boundary. Provider terms govern processing and retention.

The key is represented as `SecretStr`, used for authorization, and not intentionally persisted or logged. Raw prompts and provider responses are not intentionally persisted. Missing configuration fails safely.

## Deterministic Policies

Triage returns a category, a category signal confidence, entities, and impact factors. Application code assigns P1-P4; urgency language alone cannot create P1. A human priority override with a reason prevents later analysis from overwriting the chosen priority.

Assessment confidence is a versioned deterministic evidence-coverage score based on persisted source types, agreement, and contradictions. **It is not calibrated accuracy, probability that the cause is correct, or provider confidence.** Below the configured threshold the workflow recommends human escalation.

The provider's selected citations must be a subset of normalized evidence supplied to it. The UI presents observed evidence before the probable inference and exposes safe timeline/factor rationale, not hidden chain of thought.

## Execution And Human Boundary

Analysis, investigation, and assessment are queued in PostgreSQL, then run as FastAPI in-process background tasks. They use fresh database sessions and retain completed/failed/timed-out lifecycle states. **The task mechanism is non-durable:** an API restart can interrupt work and there is no external worker queue, lease, or automatic crash recovery.

Recommendations are proposals. Ordinary guidance requires an authenticated human decision; deterministically recognized account/access/credential actions require Manager or Administrator. Generated responses can be edited and must be approved. There is **no remediation adapter and no message-delivery adapter**. Approval records `approval_only_not_sent`; resolution and escalation are internal state transitions only.

## Evaluation And Limitations

The measured local baseline and its material limitations are in [evaluation-results.md](evaluation-results.md). The synthetic generator and deterministic provider share a domain and are not independent. Hosted behavior is not covered by that baseline. Confidence is not an evaluation metric, retrieval relevance is synthetic, and rubric compliance is not factual correctness.

Further limitations:

- Ticket text can be incomplete, biased, adversarial, or wrong; schemas restrict effects but cannot make conclusions correct.
- Read-only tools observe a synthetic corpus, not live enterprise systems.
- Citation existence establishes provenance, not truth or causal sufficiency.
- The current deployment has one tenant, one API process, process-local rate limits, and no production privacy/compliance controls.

## Component References

- [Priority and triage details](#deterministic-policies)
- [RAG architecture](rag-architecture.md)
- [Investigation workflow](investigation-workflow.md)
- [Root-cause assessment and confidence factors](root-cause-analysis.md)
- [Human approval and resolution](human-approval.md)
- [Architecture and trust boundaries](architecture.md)
- [Evaluation methodology](evaluation.md)
