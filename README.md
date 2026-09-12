# ResolveAI

AI-powered IT support ticket copilot designed around auditable evidence, deterministic policy, and human-approved resolution.

## Project Status

ResolveAI is being built incrementally against the reviewed [implementation plan](docs/implementation-plan.md). Phase 7 adds source-grounded probable root-cause assessment, deterministic confidence, low-confidence escalation, and an auditable “Show Me Why” explanation.

Current product foundation:

- React 19 and TypeScript frontend with accessible readiness states
- FastAPI backend with typed liveness and database readiness contracts
- PostgreSQL 16 with pgvector enabled by Alembic migration
- Structured request logging and request IDs
- Docker Compose startup with database, migration, API, and frontend health gates
- Opaque database-backed sessions in HTTP-only cookies with CSRF protection
- Password verification with Argon2id and role-based access controls
- Credential-free recruiter demo access with synthetic identities
- Ticket intake, search, filtering, pagination, assignment, status, and activity history
- Dashboard metrics calculated from persisted tickets
- Atomic ticket events and audit records for every mutation
- Reproducible enterprise data generator with relational incidents, telemetry, logs, and knowledge
- Versioned 1,000-ticket dataset with SHA-256 provenance and hidden evaluation truth
- Strict structured-output triage with deterministic local and optional hosted providers
- Policy-controlled P1-P4 recommendations that cannot be selected arbitrarily by a model
- Human priority override with reason, activity event, and audit record
- Idempotent Markdown ingestion with 300 source-preserving chunks and pgvector embeddings
- Hybrid vector/lexical retrieval with inspectable source excerpts and provenance
- Idempotent import of 1,000 historical tickets, 25 incidents, 10,800 telemetry observations, and 2,767 logs
- Bounded LangGraph investigation with seven read-only tools and a persisted auditable timeline
- Similar-ticket, system-status, telemetry, log, incident, history, and knowledge observations
- Evidence-normalized probable root-cause inference with validated source identifiers
- Versioned deterministic confidence factors and configurable low-confidence escalation
- “Show Me Why” timeline, supporting evidence, and decision-factor disclosure without chain-of-thought
- Backend and frontend tests, linting, formatting, and strict type checks

The ticket detail page clearly labels deterministic demo analysis versus hosted model output. ResolveAI does not display fabricated retrieval evidence, root causes, or quality metrics.

## Run With Docker

Requirements: Docker Desktop with Docker Compose.

```bash
docker compose up --build
```

Open:

- Web application: <http://localhost:3000>
- API documentation: <http://localhost:8000/docs>
- API liveness: <http://localhost:8000/api/v1/health/live>
- API readiness: <http://localhost:8000/api/v1/health/ready>

The checked-in defaults are for local development only. Use `.env.example` as the configuration reference and set a strong database password in any shared environment.

## Demo Workflow

1. Open <http://localhost:3000>.
2. Select **Try Demo**. No demo password is exposed.
3. Review the empty or existing service desk dashboard.
4. Create a ticket with requester and environment context.
5. Assign the ticket, change its workflow status, and review the activity trail.

All identities and infrastructure in demo mode are fictional. The generated corpus is available under `data/`; database ingestion and AI use arrive in later phases.

## Synthetic Enterprise Data

Generate and validate the default corpus without paid services or third-party Python packages:

```bash
python scripts/generate_demo_data.py \
  --tickets 1000 \
  --users 250 \
  --incidents 25 \
  --knowledge-articles 100 \
  --seed 42

python scripts/validate_demo_data.py
```

The checked-in seed-42 dataset contains 250 fictional users, 1,000 tickets, 25 correlated incidents, 100 knowledge articles, 10,800 telemetry observations, 2,767 synthetic logs, and 150 hidden evaluation cases. See [the synthetic data model](docs/data-model.md) for relationships, privacy boundaries, validation, and limitations.

## Structured AI Triage

Local demo mode requires no key. Create a ticket, open its detail page, and select **Analyze ticket** to receive:

- A validated category recommendation and confidence
- Structured requester, location, application, device, scope, and urgency entities
- Explicit priority decision factors
- A deterministic P1-P4 recommendation
- A manual-review warning when confidence or scope is uncertain

Hosted mode uses an OpenAI-compatible structured-output endpoint when explicitly configured. Provider output is schema-validated and supplies signals only; deterministic application policy assigns priority. See [the AI design](docs/ai-design.md).

## RAG Knowledge Retrieval

Docker Compose validates migrations, ingests the checked-in knowledge corpus, and starts the API only after ingestion succeeds. Ticket detail pages search the knowledge base using bounded ticket context and display only persisted article titles and exact chunk excerpts.

Phase 5 uses a deterministic 384-dimensional signed hashing embedding plus lexical reranking and transparent domain query expansion. This keeps the demo fully local and reproducible without claiming learned semantic quality. The retrieval boundary can be replaced by a learned embedding model in a later production deployment.

```bash
cd backend
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai \
RESOLVEAI_KNOWLEDGE_DATA_DIR=../data/knowledge \
.venv/bin/python -m app.rag.ingest
```

See [the RAG architecture](docs/rag-architecture.md) for chunking, ranking, citation integrity, and limitations.

## Investigation Workflow

After structured triage completes, an analyst can start a bounded investigation. ResolveAI plans at most ten read-only tool calls and records each result as an auditable step:

- Search approved knowledge
- Search semantically similar resolved tickets
- Read current ticket history
- Inspect synthetic service status
- Inspect bounded telemetry windows
- Search bounded synthetic logs
- Read related public incident facts

The primary VPN/PayrollPro scenario uses a clearly labeled curated synthetic reference time and collects both healthy VPN observations and degraded DNS observations. Phase 6 displays facts only and does not state a root cause, confidence, or recommendation. See [the investigation workflow](docs/investigation-workflow.md).

## Root Cause And Trust

After investigation, an analyst can generate a separate assessment. ResolveAI displays the information in trust order:

1. Observed evidence with persisted source IDs
2. Probable root cause labeled as an unconfirmed inference
3. Deterministic evidence confidence labeled as not measured accuracy
4. Recommended action labeled for human review, with no claim that it executed

Confidence below the configured 70% threshold recommends human escalation. “Show Me Why” exposes the persisted investigation timeline, supporting evidence, and signed confidence factors while explicitly stating that hidden chain-of-thought is not stored or shown. See [root-cause analysis design](docs/root-cause-analysis.md).

## Local Development

Backend requires Python 3.12:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai .venv/bin/alembic upgrade head
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai RESOLVEAI_SESSION_COOKIE_SECURE=false .venv/bin/uvicorn app.main:app --reload
```

Frontend requires Node.js 22 or later:

```bash
cd frontend
npm install
npm run dev
```

## Quality Checks

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/mypy app tests
.venv/bin/pytest
```

```bash
cd frontend
npm run format
npm run lint
npm test
npm run build
```

## Architecture

The architecture, data model, API contracts, AI workflow, phase gates, dependencies, and risks are documented in [docs/implementation-plan.md](docs/implementation-plan.md).

## License

No license has been selected yet. All rights are reserved until a license is added during repository hardening.
