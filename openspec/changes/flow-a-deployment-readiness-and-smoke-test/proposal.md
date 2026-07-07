## Why

Flow A core implementation is complete through child slice 7 (`n8n-flow-a-blog-publish-orchestration`, commit `962ba2f`), but operators discovered that **repository HEAD can be current while the running worker still exposes old endpoints**. Ad-hoc curl checks and manual n8n execution are error-prone and do not distinguish code readiness from deployment readiness. Before archiving the active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, the project needs a **repeatable deployment readiness and smoke-test capability** that gates Flow A verification on Phase 0 checks.

## Goals

- Define a repeatable script/command layer that verifies whether the **deployed/running environment** is ready for Flow A smoke testing.
- Distinguish **repository state** (git checkout) from **running worker state** (process/container + OpenAPI surface).
- Cover phased smoke testing: deployment readiness → worker contract → n8n configuration → manual Flow A execution → idempotent rerun.
- Produce human-readable terminal output and optional machine-readable JSON with a clear pass/fail summary.
- Fail clearly on stale worker, missing Flow A endpoints, wrong port/base path, missing workflow export, or workflow `active: true`.
- Treat n8n workflow-not-imported as **pending import**, not a code failure.
- Reference umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` for policy and sequencing.

## Non-Goals

- LinkedIn API publication (deferred slice 8 `linkedin-publication-integration`).
- Activating the Flow A n8n workflow (`"active": true`), cron, webhook, or scheduled triggers.
- Automatic deploy, container restart, or git operations.
- Archiving the umbrella or this child change.
- Committing or pushing repository changes as part of this proposal.
- Requiring manual ad-hoc diagnostics as the primary operator workflow.
- Printing secrets in output.
- Destructive operations (publishing real content, deleting files, mutating production metadata) during readiness checks.

## What Changes

- Add child OpenSpec change `flow-a-deployment-readiness-and-smoke-test` under active umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` — **operational verification after slice 7, before umbrella archive**.
- Introduce capability spec `flow-a-deployment-readiness-and-smoke-test` covering deployment readiness checks, smoke-test phases, output format, and failure semantics.
- Design and later implement a **Python CLI** at `scripts/flow_a_readiness.py` (primary) with optional thin shell wrapper if needed for server operators; complements existing `deploy/server/smoke-worker.sh` without replacing it.
- Add unit tests for readiness parsers/checks (OpenAPI path extraction, workflow `active` flag, commit presence, report structure).
- Document operator workflow in README and/or `docs/deployment/` — Phase 0 must pass before Phases 1–4.
- Update umbrella roadmap: operational verification child **proposed/active**; slice 8 remains **deferred**; umbrella **not ready to archive** until this child is completed.

No worker HTTP endpoint changes, n8n workflow activation, LinkedIn API calls, or umbrella archive in this change.

## Capabilities

### New Capabilities

- `flow-a-deployment-readiness-and-smoke-test`: Repeatable deployment readiness and phased smoke-test verification for Flow A — repo vs running worker checks, OpenAPI endpoint surface validation, n8n reachability and workflow export checks, structured pass/fail reporting, and gated smoke phases without secrets or destructive operations.

### Modified Capabilities

<!-- No existing main spec requirements change. deploy/server/smoke-worker.sh remains scoped to basic server health/process-ready; this child adds Flow A-specific readiness and phased smoke orchestration. -->

## Impact

- **Umbrella reference**: MUST cite `flow-a-automatic-blog-linkedin-publishing-roadmap`. Umbrella remains **active** and is **not ready to archive** until this operational verification child completes.
- **Expected baseline commits** (configurable): `79f5345`, `962ba2f`, `53708eb` on `origin/main`.
- **Worker endpoints inspected** (read-only): `GET /health`, `GET /openapi.json`, presence of `/process-ready`, `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution` in OpenAPI paths.
- **Files verified in checkout**: Flow A workflow JSON, editorial canon, key worker modules (see design.md).
- **n8n**: Reachability check only; workflow import status reported as pending when applicable.
- **Tests**: New unit tests under `tests/` for readiness logic; no live server required in CI for parser tests.
- **Out of scope for apply**: archive, commit, push.
