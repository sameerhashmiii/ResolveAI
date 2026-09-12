# Setup And Operations

## Docker Quick Start

Install Docker Desktop with Docker Compose, then run from the repository root:

```bash
docker compose up --build
```

Open <http://localhost:3000> and select **Start 90-second guided demo**. Compose starts PostgreSQL, applies all Alembic migrations, idempotently ingests the synthetic knowledge and operational corpora, runs the real 150-case aggregate evaluation, then starts the API and frontend after every gate succeeds.

The defaults are for a local, single-user demonstration. Do not expose them to an untrusted network or enter real/confidential data.

## Configuration

`.env.example` documents local Compose settings. Common overrides:

- `FRONTEND_PORT` and `BACKEND_PORT`: host ports, default 3000 and 8000.
- `POSTGRES_PASSWORD`: change for any shared developer host.
- `RESOLVEAI_SESSION_COOKIE_SECURE`: `false` only for local HTTP; use secure cookies behind HTTPS.
- `RESOLVEAI_TRUSTED_HOSTS`: JSON hostname list; wildcards are intentionally rejected.
- `RESOLVEAI_AI_MODE`: `local_demo` or `openai_compatible`.
- `RESOLVEAI_LLM_BASE_URL`, `RESOLVEAI_LLM_MODEL`, `RESOLVEAI_LLM_API_KEY`: required for hosted mode.

Hosted mode sends bounded ticket context and normalized workflow evidence to the configured provider. Review that provider's privacy and retention terms first.

## Native Development

Use Python 3.12, `uv`, Node.js 22+, npm, and a PostgreSQL 16 instance with pgvector.

```bash
cd backend
uv sync --frozen --extra dev
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai uv run alembic upgrade head
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai RESOLVEAI_ENVIRONMENT=development RESOLVEAI_SESSION_COOKIE_SECURE=false uv run uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

For an empty native database, ingest both corpora from `backend/`:

```bash
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai uv run python -m app.rag.ingest
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai uv run python -m app.demo.ingest
```

## Reset

This removes the local Compose database volume:

```bash
docker compose down --volumes --remove-orphans
docker compose up --build
```

## Troubleshooting

| Symptom | Check |
|---|---|
| Port already allocated | Set `FRONTEND_PORT` or `BACKEND_PORT` in `.env` |
| API remains unhealthy | Run `docker compose ps` and `docker compose logs backend database migrate` |
| Ingestion or evaluation failed | Inspect `docker compose logs ingest operational-ingest evaluation-run`; validate `data/manifest.json` checksums |
| Login repeatedly returns 429 | Wait for the fixed window; the limiter resets when the one API process restarts |
| Cookie works in Docker but not native mode | Set `RESOLVEAI_SESSION_COOKIE_SECURE=false` only for local HTTP |
| Hosted analysis is unavailable | Set all three hosted provider values and confirm endpoint/model compatibility |
| Workflow remains queued/running after restart | In-process jobs are non-durable; use the UI retry when offered or reset demo state |
| Readiness returns 503 | Confirm PostgreSQL is healthy and the database URL resolves from the API environment |

## OpenAPI And Evaluation

```bash
cd backend
uv run --frozen python ../scripts/export_openapi.py
RESOLVEAI_DATABASE_URL=postgresql+asyncpg://resolveai:resolveai_local@localhost:5432/resolveai uv run python ../evaluation/run_eval.py
```

OpenAPI generation does not connect to the placeholder database. Evaluation requires migrated PostgreSQL and ingested knowledge.
