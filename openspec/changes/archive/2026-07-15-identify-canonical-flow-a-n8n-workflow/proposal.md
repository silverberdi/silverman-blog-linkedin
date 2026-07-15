## Why

Flow A core worker capabilities are operationally validated, and the Flow A n8n workflow export is imported but **inactive** on the Ubuntu server. Before activation (US-010) or unattended scheduling (BL-005), operators need a single, authoritative answer to which n8n workflow is canonical for Flow A, whether import and configuration on `192.168.0.194` are correct, and what execution frequency is proposed — with clear pass/fail evidence and remediation when something is wrong. Without that identification step, operators risk activating the wrong workflow, misconfiguring worker URL/API key, or enabling scheduling before readiness gates pass.

## Goals

- Satisfy **US-009** acceptance criteria under backlog **BL-004** (identify canonical workflow, confirm import/configuration, define execution frequency proposal, operator-visible outcomes, clear failure communication, no duplicate or unintended side effects).
- Establish one canonical Flow A workflow identity: repository export `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`, stable n8n id `silvermanFlowAPublish01`, name **Silverman Blog LinkedIn Flow A Publish**.
- Provide repeatable operator verification via existing `deploy/server/import-flow-a-n8n-workflow.sh` and `deploy/server/collect-flow-a-smoke-evidence.sh`, plus Phase 0/2 readiness checks — without activating the workflow or calling LinkedIn API.
- Document a proposed execution frequency for scheduled orchestration (decision record only; workflow export and server import remain **inactive** until US-010).

## Non-Goals

- **US-010**: Activating the workflow, adding cron/schedule triggers, or enabling unattended n8n execution.
- **US-011**: LinkedIn publication enablement as an activation-time guard story. US-009 MUST NOT enable LinkedIn publication; a temporary `false` verify window is allowed. Final runtime flag may remain or be restored to `true` by operator after validation (documented in ops notes / RUNTIME-STATE) without closing US-011.
- **BL-005**: Fully unattended Flow A test.
- Modifying Flow B draft-generation workflow (`silverman-blog-linkedin-draft-generation.json`).
- Worker endpoint contract changes, publish/package/schedule apply paths, or destructive filesystem operations.
- n8n Execute Command or any non-HTTP orchestration (ADR-0001).

## What Changes

- Add operator-facing canonical workflow identification documentation tying repository export, stable n8n id, node count (26), and distinction from Flow B draft-generation workflow.
- Extend readiness and evidence scripts (or add a focused verification entry point) with explicit canonical-workflow identity checks: file path, workflow id `silvermanFlowAPublish01`, `active: false`, 26 nodes, worker `worker_base_url` / `worker_api_key` configured without printing secrets.
- Document proposed Flow A n8n execution frequency aligned with editorial calendar cadence (proposal only — no schedule trigger added to export or server).
- Add pass/fail/pending remediation messages when import is missing, wrong workflow is present, configuration mismatches API key, or workflow is unexpectedly active.
- Map implementation tasks and validation steps explicitly to US-009 acceptance criteria; defer US-010/US-011 to follow-up changes.

## Capabilities

### New Capabilities

- `flow-a-canonical-n8n-workflow-identification`: Operator requirements for identifying the canonical Flow A n8n workflow, confirming import/configuration on Ubuntu server, documenting proposed execution frequency, and surfacing pass/fail remediation — without activation or processing side effects.

### Modified Capabilities

- `flow-a-deployment-readiness-and-smoke-test`: Extend Phase 0/2 and evidence collection with canonical workflow identity verification (path, id, name, node count, inactive state, configuration presence) and operator remediation for import/config failures.
- `n8n-flow-a-blog-publish-orchestration`: Add requirement to document proposed execution frequency and canonical identity cross-references; reaffirm export remains inactive with no production schedule trigger in this change.

## Impact

- **Documentation**: `docs/deployment/`, `docs/CURRENT-STATE.md` (canonical workflow identity section), README Flow A cross-links.
- **Scripts**: `deploy/server/import-flow-a-n8n-workflow.sh`, `deploy/server/collect-flow-a-smoke-evidence.sh`, `scripts/flow_a_readiness.py` — targeted extensions for canonical identity checks and remediation text.
- **Tests**: Unit tests for new readiness/identity check logic (no live n8n or Ubuntu server required in CI).
- **n8n**: Verification only on Ubuntu server; workflow remains **inactive**; no cron/webhook nodes added.
- **Worker / LinkedIn**: No worker API contract changes in this change. US-009 verification does not enable LinkedIn publication; live enablement flag is recorded in RUNTIME-STATE and may differ after an operator-approved restore.

## Backlog and User Story Mapping

| Source | Scope |
|--------|-------|
| **BL-004** | Parent backlog — this change addresses only the identification/configuration/frequency-proposal slice |
| **US-009** | **In scope** — all six acceptance criteria |
| **US-010** | **Deferred** — workflow activation and concurrency controls |
| **US-011** | **Deferred** — LinkedIn publication guard confirmation at activation time |

### US-009 Acceptance Criteria Coverage

| Criterion | How this change addresses it |
|-----------|------------------------------|
| Identify the canonical Flow A workflow | Document and verify `silverman-blog-linkedin-flow-a-publish.json` / `silvermanFlowAPublish01` vs Flow B draft workflow |
| Confirm correct import and configuration | `import-flow-a-n8n-workflow.sh` + evidence/readiness checks for id, nodes, inactive, worker URL/key |
| Define execution frequency | Document proposed schedule (e.g. daily poll aligned with editorial calendar due items) — proposal only |
| Outcome visible and understandable | Pass/fail/pending summaries with remediation in scripts and deployment docs |
| Failures or blocked states clearly communicated | Distinct failure modes: missing import, wrong id, active workflow, API key mismatch, stale worker |
| No duplicate or unintentional changes | Read-only verification; no publish/package/schedule apply; workflow stays inactive |
