# Synthetic Enterprise Data Model

## Purpose

ResolveAI includes a reproducible fictional enterprise dataset for demonstration, retrieval, incident correlation, and offline evaluation. It contains no real people, organizations, credentials, routable infrastructure, or production telemetry.

The dataset is generated from relationships first. Incidents select affected services, locations, applications, and users; tickets then describe varied symptoms within those incident windows; telemetry and logs independently record correlated service behavior. This prevents the corpus from becoming a collection of unrelated random records.

## Generate and Validate

```bash
python scripts/generate_demo_data.py \
  --tickets 1000 \
  --users 250 \
  --incidents 25 \
  --knowledge-articles 100 \
  --applications 15 \
  --seed 42

python scripts/validate_demo_data.py
```

The generator uses only the Python standard library and writes byte-identical output for identical arguments. It refuses unsafe output roots and only removes known generated paths. `data/manifest.json` records counts, simulation dates, distribution, schema/dataset versions, and SHA-256 checksums.

## Artifacts

| Path | Format | Purpose |
|---|---|---|
| `data/manifest.json` | JSON | Provenance, counts, distribution, and checksums |
| `data/locations/locations.json` | JSON | Ten fictional offices and synthetic network context |
| `data/applications/applications.json` | JSON | Fifteen fictional applications and service dependencies |
| `data/users/users.jsonl` | JSONL | Fictional users, managers, locations, and devices |
| `data/incidents/incidents.json` | JSON | Public incident facts and related-ticket links |
| `data/tickets/tickets.jsonl` | JSONL | One thousand varied historical support tickets |
| `data/knowledge/index.json` | JSON | Searchable article metadata and source paths |
| `data/knowledge/articles/*.md` | Markdown | One hundred inspectable troubleshooting articles |
| `data/telemetry/telemetry.jsonl` | JSONL | Normal baselines and incident-correlated service spikes |
| `data/logs/logs.jsonl` | JSONL | Synthetic-safe service log evidence |
| `data/evaluation/ground_truth.json` | JSON | Non-user-facing incident and ticket evaluation truth |

JSONL is used for higher-volume records so later ingestion can stream data rather than loading an entire file into memory.

## Relationship Rules

1. Every user references a known location and, where applicable, a known fictional manager.
2. Application dependencies reference the fixed synthetic service catalog.
3. Every incident has a valid time window, affected scope, related tickets, telemetry, logs, and hidden ground truth.
4. Incident-linked tickets use affected users and locations and occur inside the incident window.
5. Related-ticket links are symmetric and connect tickets from the same incident.
6. Resolved or closed tickets have consistent resolution fields; in-progress tickets do not claim a resolution.
7. Knowledge citations reference indexed Markdown files.
8. Telemetry outside incidents has an error rate below 1%; incident observations exceed 5% and match service, location, and time scope.
9. Ticket `ai_analysis` and `ai_confidence` remain null because Phase 3 does not fabricate AI output.

## Primary Scenario

`INC-0001` represents a Dallas DNS degradation affecting PayrollPro. Tickets use different symptom language, including VPN-connected users unable to reach internal applications. DNS telemetry degrades during the same window and synthetic DNS logs include a failed lookup for `payrollpro.internal.synthetic.invalid`.

The P2 root-cause key and expected evidence remain in `data/evaluation/ground_truth.json`. They are excluded from normal ticket, incident, knowledge, telemetry, and log responses. Future application APIs must never expose this file to analyst-facing retrieval.

## Validation

The validator independently checks:

- Manifest file coverage and checksums
- Exact entity counts and category distribution
- Unique IDs and foreign keys
- User, manager, location, application, and dependency integrity
- Ticket status, priority, timestamps, resolutions, and AI null fields
- Incident scope and ticket correlation
- Symmetric meaningful related-ticket links
- Knowledge metadata, files, required sections, and variation
- Telemetry thresholds and incident windows
- Synthetic hostnames and service-specific log signatures
- Complete separated ground truth with no root-cause leakage

It exits non-zero on failure and reports each check as `PASS` or `FAIL`.

## Limitations

- The data models plausible service-desk relationships, not a statistically representative real enterprise.
- Names and language are template-generated and intentionally fictional.
- Service measurements are deterministic signals for product demonstration, not a physical infrastructure simulation.
- Ground truth enables evaluation but does not prove that an AI method generalizes to production data.
