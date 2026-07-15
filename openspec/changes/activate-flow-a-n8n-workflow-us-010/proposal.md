## Why

US-009 identified the canonical Flow A n8n workflow (`silvermanFlowAPublish01`) and documented a proposed daily 09:00 UTC schedule, but the workflow remains inactive and schedule-less on `192.168.0.194`. BL-004 / **US-010** needs controlled activation with single-flight protection and restart/recovery evidence so Flow A can run on schedule through n8n without duplicate concurrent processing — without claiming fully unattended Flow A (BL-005) or closing LinkedIn publication-guard acceptance (US-011).

## What Changes

- Activate the canonical Flow A n8n workflow on the Ubuntu server (`id=silvermanFlowAPublish01`).
- Add a Schedule Trigger for daily **09:00 UTC** to the repository export and re-import path; retain Manual Trigger for operator runs.
- Enforce single-flight (no overlapping executions of the same workflow) using n8n orchestration settings plus existing worker idempotency — no new worker endpoints unless design proves a hard gap.
- Define and execute an operator evidence plan for restart/recovery (n8n/container restart does not double-process or leave stuck locks); prefer dry-run/empty-ready paths; gate any live blog side effects behind explicit operator approval.
- Update readiness/import/evidence scripts and docs that currently require `active: false` and forbid Schedule Trigger (US-009 assumptions) with intentional US-010 exceptions: repo export stays inactive; server may be active.
- Provide operator-visible pass/fail/pending outcomes and remediation for activation, concurrency, and recovery checks.
- Update CURRENT-STATE / RUNTIME-STATE / product progress only for demonstrated US-010 outcomes (not US-011 / BL-005).

## Goals

- Materialize the US-009 proposed schedule and activate the canonical workflow safely.
- Prevent duplicate/concurrent Flow A orchestration runs.
- Prove restart/recovery behavior with recorded evidence.
- Keep language qualified: n8n active ≠ unattended BL-005; blog handoff ≠ live; LinkedIn API not in scope.

## Non-Goals

- **US-011** — Keep LinkedIn publication disabled until separately approved (do not close US-011; do not flip `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as part of this change unless a later design gap and explicit operator approval require a temporary verify window).
- **BL-005** — Fully unattended end-to-end Flow A test.
- **BL-007 / auto_queue WIP** — Ignore unstaged LinkedIn publication automation WIP and publish-pending workflow.
- Flow B draft-generation workflow changes.
- Worker contract changes unless strictly required for single-flight (orchestration-side first).
- n8n Execute Command or any non-HTTP worker integration (ADR-0001).
- Closing BL-004 entirely (US-011 remains open).

## Acceptance criteria addressed (US-010)

| AC | How this change addresses it |
|----|------------------------------|
| Activate the workflow | Server activation of `silvermanFlowAPublish01` after Schedule Trigger import |
| Prevent duplicate or concurrent processing | n8n single-flight + existing worker idempotency |
| Validate restart and recovery behavior | Documented evidence procedure on server |
| Outcome visible to operator | Pass/fail/pending scripts + remediation |
| Failures/blocked states clear | Failure-mode matrix in design/specs |
| No unintended duplication of completed work | Idempotent worker paths + no overlapping runs |

## Acceptance criteria intentionally excluded

- US-011 LinkedIn publication disabled-until-approved (noted in design/RUNTIME only; not validated here).
- BL-005 unattended full-path success criteria.

## Capabilities

### New Capabilities

- `flow-a-n8n-workflow-activation`: Controlled activation of canonical Flow A n8n orchestration — Schedule Trigger materialization, server `active: true`, single-flight concurrency, restart/recovery evidence, and operator pass/fail/pending outcomes (US-010 / BL-004).

### Modified Capabilities

- `flow-a-canonical-n8n-workflow-identification`: Evolve proposed-only schedule and “must stay inactive / no schedule triggers” identity rules for post–US-010 repo vs server divergence; update expected node count after Schedule Trigger.
- `n8n-flow-a-blog-publish-orchestration`: Allow Schedule Trigger alongside Manual Trigger; update inactive-export and scheduling requirements; document dual-entry flow and concurrency expectation.
- `flow-a-deployment-readiness-and-smoke-test`: Replace US-009 script assumptions (`active: false` on server, forbid Schedule Trigger) with mode-aware checks for repo export vs live activated workflow.

## Impact

- **n8n:** Export `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` (Schedule Trigger + connections); re-import and activate on `192.168.0.194`.
- **Scripts:** `deploy/server/import-flow-a-n8n-workflow.sh`, `deploy/server/collect-flow-a-smoke-evidence.sh`, `scripts/flow_a_readiness.py`, related tests/docs.
- **Docs:** README Flow A section, deployment docs, CURRENT-STATE, RUNTIME-STATE, product progress for US-010 when validated.
- **Worker:** No endpoint contract changes expected; reuse publish/package/schedule idempotency.
- **Out of impact:** LinkedIn publication flag (US-011), Flow B workflow, BL-007 WIP.
- **Backlog:** BL-004 US-010; leaves US-011 and BL-005 open.
