# ResolveAI

AI-powered IT support ticket copilot designed around auditable evidence, deterministic policy, and human-approved resolution.

## Project Status

ResolveAI is being built incrementally against the reviewed [implementation plan](docs/implementation-plan.md). Phase 3 adds a validated synthetic enterprise environment; AI investigation capabilities are intentionally not represented as complete yet.

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
- Backend and frontend tests, linting, formatting, and strict type checks

The ticket detail page explicitly marks AI investigation as unavailable until the evidence-backed workflow is implemented and tested in Phase 4. ResolveAI does not display fabricated analyses or metrics.

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
