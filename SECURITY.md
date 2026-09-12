# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| `main` / current 0.11 release line | Yes |
| 0.10 and older | No |

Historical tags and forks are not supported.

## Reporting A Vulnerability

Do not open a public issue or discussion for a suspected vulnerability. Report it privately through [GitHub Security Advisories](https://github.com/sameerhashmiii/ResolveAI/security/advisories/new), including reproduction steps, affected paths, impact, and any suggested mitigation. You may expect acknowledgement when maintainers are available, but this portfolio project provides no guaranteed response or remediation SLA. Please allow time for investigation before disclosure.

## Scope And Limits

ResolveAI is a non-production, single-tenant local demonstration. It is not designed or certified for regulated data, compliance workloads, public internet exposure, multiple tenants, or high-availability operation. Do not enter real or confidential data.

Important limits:

- Authentication, CSRF, RBAC, headers, input validation, and process-local rate limits are defense-in-depth controls, not a complete deployment security program.
- Audit records are append-only by application convention. A database administrator or compromised process can alter them; they are not tamper-evident or independently retained.
- Dependency, static-analysis, and container scans can identify known classes of problems; passing scans does not prove vulnerabilities are absent.
- There is no tenant isolation, compliance attestation, secrets manager integration, at-rest encryption certification, backup policy, disaster recovery, or external security audit.
- TLS, network segmentation, host hardening, PostgreSQL access control, encrypted backups, monitoring, and secret rotation are deployment-operator responsibilities.
- Hosted AI mode transmits bounded ticket context and normalized evidence to the configured provider under that provider's security and retention terms.
- In-process background tasks and rate limits are non-durable and intended for one API process.
- ResolveAI has no remediation executor or response-delivery adapter. Human approval does not prove an action occurred or a response was sent.

See [the architecture trust boundaries](docs/architecture.md) and [hardening notes](docs/security-hardening.md).
