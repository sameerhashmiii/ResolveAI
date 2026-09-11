# ResolveAI

AI-powered IT support ticket copilot designed around auditable evidence, deterministic policy, and human-approved resolution.

## Project Status

ResolveAI is being built incrementally against the reviewed [implementation plan](docs/implementation-plan.md). Phase 1 establishes the runnable platform foundation; ticket workflows and AI capabilities are intentionally not represented as complete yet.

Current foundation:

- React 19 and TypeScript frontend with accessible readiness states
- FastAPI backend with typed liveness and database readiness contracts
- PostgreSQL 16 with pgvector enabled by Alembic migration
- Structured request logging and request IDs
- Docker Compose startup with database, migration, API, and frontend health gates
- Backend and frontend health tests, linting, and type-check configuration

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

## Local Development

Backend requires Python 3.12:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai .venv/bin/alembic upgrade head
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai .venv/bin/uvicorn app.main:app --reload
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
