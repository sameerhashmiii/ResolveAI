# Screenshot Manifest

These images were captured from the verified local Compose application using only synthetic data. Regenerate them with `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npm run screenshots` from `frontend/` after starting the stack.

| Required filename | Surface | Suggested alt text |
|---|---|---|
| `landing.png` | Public evidence-first portfolio entry | ResolveAI landing page introducing an evidence-first, human-controlled support workflow |
| `dashboard.png` | Authenticated service desk overview | ResolveAI synthetic service desk dashboard with ticket totals and recent requests |
| `ticket-intake.png` | New request form populated with the Dallas/PayrollPro scenario | New synthetic IT request form for a Dallas PayrollPro name-resolution issue |
| `ticket-triage.png` | Completed deterministic triage | Structured synthetic ticket classification, entities, and policy priority |
| `investigation.png` | Completed bounded investigation timeline | Read-only investigation timeline showing synthetic evidence sources and limitations |
| `assessment.png` | Evidence, probable cause, confidence, and Show Me Why | Probable-cause assessment with cited evidence and deterministic confidence factors |
| `human-approval.png` | Recommendation and response approval panel | Human decision panel stating that response approval does not send a message |
| `mobile-navigation.png` | Open mobile navigation | ResolveAI mobile navigation over the synthetic service desk view |

Before committing a capture:

- Reset to the checked-in synthetic dataset and use fictional names/identifiers only.
- Inspect the full frame for terminal paths, browser profiles, email, hostnames, tokens, notifications, extensions, and machine metadata; crop or redact them.
- Do not show hosted-provider keys, raw prompts, hidden evaluation cases, database details, logs, or developer tools.
- Use a stable viewport, legible scale, and PNG output. Avoid decorative browser chrome where it adds no context.
- Add meaningful Markdown/HTML alt text describing the useful state rather than saying "screenshot."
- Update this manifest if a filename changes and verify every README/docs link.
