# Phase 10 Hardening

## Request Controls

ResolveAI applies fixed-window limits to public login/demo authentication and to authenticated analysis, investigation, assessment, retry, and response-generation operations. Authentication limits use the direct socket client address and never trust `X-Forwarded-For`. Workflow limits use the authenticated internal user ID and stable route template.

Limited requests return HTTP `429`, a generic message, and an integer `Retry-After` header. Keys, counters, user data, and request content are never returned or logged. Invalid CSRF requests do not consume authenticated workflow quota.

The limiter is bounded and process-local, matching the current single-worker container. Production deployments with multiple workers or replicas must replace it with a shared atomic limiter such as Redis or a database-backed implementation.

## Browser Policy

API responses include MIME-sniffing, framing, referrer, permissions, and content-security controls, including error responses. Authentication, analytics, and administrator responses use `Cache-Control: no-store`. HSTS is emitted only when the configured environment is `production` and secure cookies are enabled.

Trusted hosts are configured with `RESOLVEAI_TRUSTED_HOSTS` as a JSON list. Cross-origin access is not enabled by default. Local Compose trusts `localhost`, `127.0.0.1`, and the internal `backend` hostname.

The nginx frontend applies a same-origin CSP, framing and MIME protections, restrictive permissions, and cross-origin opener isolation. HTML is not cached; content-hashed assets are immutable. `/healthz` provides a dependency-free container health check.

## Failure Safety

Unhandled API failures return a generic HTTP `500` response with a request ID and security headers. Database addresses, credentials, SQL, stack traces, provider output, prompts, and ticket content are not returned. Structured request logs use bounded fields and stable route templates.

React and router error boundaries show generic recovery actions without rendering raw exception text. The mobile navigation drawer is inert while closed and supports Escape, backdrop dismissal, route-close, and focus restoration.

## Containers

- Backend dependencies are installed from `uv.lock` with frozen resolution.
- Frontend dependencies use `npm ci` and `package-lock.json`.
- Backend and frontend runtime processes are non-root.
- Application containers drop Linux capabilities, set `no-new-privileges`, use read-only root filesystems, and receive only bounded temporary storage.
- Image and Compose health checks validate backend readiness and frontend `/healthz`.

## Continuous Integration

`.github/workflows/ci.yml` runs independent backend, frontend, deterministic-data, PostgreSQL integration/evaluation, image-build, Compose-smoke, and Playwright jobs. `.github/workflows/codeql.yml` analyzes Python and TypeScript. Dependabot monitors Python, npm, Actions, and Docker dependencies.

The Compose smoke test verifies health through both direct and proxied API paths, security headers on successful and error responses, HTML/asset cache behavior, hidden server versions, and non-root runtime users. Playwright exercises the real analyst workflow from demo login through explicitly approved resolution plus a mobile navigation/overflow check.
