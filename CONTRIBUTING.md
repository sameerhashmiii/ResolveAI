# Contributing

ResolveAI welcomes focused fixes and documentation improvements. By participating, follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report vulnerabilities through the private route in [SECURITY.md](SECURITY.md), never a public issue.

## Setup

Use Python 3.12, `uv`, Node.js 22, npm, Docker, and Docker Compose.

```bash
cd backend
uv sync --frozen --extra dev
cd ../frontend
npm ci
```

For the full local stack, run `docker compose up --build`. Native backend setup and environment values are documented in [docs/setup.md](docs/setup.md).

## Checks

Run checks relevant to the change before opening a pull request:

```bash
cd backend
uv run --frozen ruff check app tests alembic ../evaluation ../scripts/export_openapi.py
uv run --frozen mypy
uv run --frozen pytest
cd ../frontend
npm run format
npm run lint
npm test
npm run typecheck
npm run build
```

Run `npm run test:e2e` against the Compose stack for user-flow changes. Do not update snapshots or screenshots merely to hide a regression.

## Database And API Changes

- Add an Alembic migration for every schema change; test upgrade, downgrade to base, and upgrade again against PostgreSQL.
- Keep mutations transactional with corresponding ticket/audit events where the existing convention requires them.
- Update `docs/api.md` for API behavior changes.
- Regenerate OpenAPI with `cd backend && uv run --frozen python ../scripts/export_openapi.py`; commit `docs/openapi.json` and verify a second run has no diff.

Create and validate a migration from `backend/` with a configured development database:

```bash
uv run alembic revision --autogenerate -m "concise change"
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```

## Data, UI, And Documentation

- Use only synthetic, fictional data. Never commit customer data, personal data, credentials, provider payloads, prompts containing real data, or production logs.
- Keep generated data deterministic and run `python scripts/validate_demo_data.py`. Explain intentional corpus/checksum changes.
- Test keyboard operation, focus, names/labels, status announcements, contrast, responsive layout, and reduced-width overflow for UI changes.
- Screenshots must use a fresh synthetic dataset, redact machine/user metadata, include useful alt text, and follow `docs/assets/screenshots/README.md`.
- Update current docs rather than treating `docs/implementation-plan.md` as authority.

## AI Claim Checklist

Before describing AI behavior, verify that the change:

- Distinguishes deterministic local behavior from hosted provider behavior.
- Calls an assessment probable rather than confirmed and confidence evidence coverage rather than calibrated accuracy.
- Preserves citations and states retrieval/evaluation limitations.
- Documents exactly what bounded context leaves the deployment in hosted mode.
- Does not claim autonomous remediation, response delivery, production accuracy, or safety guarantees.
- Keeps human approval and escalation boundaries explicit.

Use concise [Conventional Commit](https://www.conventionalcommits.org/) messages such as `docs: clarify hosted provider boundary` or `fix: reject stale response approval`. Keep commits scoped and do not mix unrelated formatting changes.
