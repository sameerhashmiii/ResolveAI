# Acceptance Walkthrough

## Preconditions

1. Run `docker compose up --build --wait` from a clean or reset workspace.
2. Confirm <http://localhost:8000/api/v1/health/ready> reports `ready`.
3. Open <http://localhost:3000> in a desktop browser.

## Human-Controlled Resolution Path

1. Select **Start 90-second guided demo**, then **Continue guided demo**.
2. Verify the guided intake is prefilled and create a ticket with these synthetic values:
   - Title: `VPN access to PayrollPro unavailable`
   - Description: `The VPN connects from Dallas, but PayrollPro remains unavailable and its internal service name does not resolve. Other internet services work.`
   - Requester: `Jordan Lee`; department: `Payroll`; location: `Dallas`; device: `SYN-DEV-00041`; application: `PayrollPro`
3. Verify the ticket detail and activity trail appear.
4. Select **Analyze ticket**. Wait for completion and verify deterministic mode, extracted entities, category confidence, priority factors, and manual-review state are labeled.
5. Select **Start investigation**. Verify the timeline identifies its curated synthetic reference time and shows source-bearing knowledge, similar-ticket, status, telemetry/log, incident, and history observations as applicable.
6. Select **Generate assessment**. Verify observed evidence precedes the probable cause and recommendation. Confirm confidence is labeled deterministic evidence confidence, not measured accuracy.
7. Open **Show Me Why** and verify source IDs, limitations, signed factors, and the no-chain-of-thought disclosure.
8. In **Human Decision & Resolution**, select **Approve**, enter `Evidence and bounded guidance reviewed by the demo analyst`, and confirm.
9. Generate a requester response. Review or edit the draft so it uses uncertainty language, follows accepted guidance, and claims no completed action.
10. Save and approve the response. Verify the confirmation states it has not been sent.
11. Enter `Human-reviewed guidance and approved response recorded; no automated remediation was performed.` and resolve the ticket.
12. Verify resolved status, summary, and activity records. No UI or API should claim response delivery or remediation.

## Alternate And Guardrail Checks

1. Rejecting a recommendation should stop the assisted response path.
2. High-impact account/access instructions should require Manager or Administrator authority.
3. Generic ticket edits must not set resolved or escalated; use dedicated transitions.
4. A low-confidence assessment should recommend human escalation.
5. At mobile width, the menu should open/close with keyboard Escape, restore focus, and create no horizontal page overflow.
6. Administrator observability should show aggregate synthetic evaluation and sanitized component status, not per-case truth, prompts, raw logs, secrets, or database addresses.

The automated counterpart is `frontend/e2e/critical-flow.spec.ts`; mobile behavior is covered by `frontend/e2e/mobile.spec.ts`.
