## Context

Flow A worker pipeline (publish → package → schedule → campaign lifecycle) is operationally validated on the Ubuntu server (`192.168.0.194:8010`). The repository already ships:

- Canonical export: `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`
- Import script: `deploy/server/import-flow-a-n8n-workflow.sh` (stable id `silvermanFlowAPublish01`, 26 nodes, `active: false`)
- Evidence script: `deploy/server/collect-flow-a-smoke-evidence.sh`
- Readiness CLI: `scripts/flow_a_readiness.py` (Phase 0–2 gates)

The Flow B draft-generation workflow (`silverman-blog-linkedin-draft-generation.json`) is a separate artifact and must not be conflated with Flow A. n8n orchestration is HTTP-only per ADR-0001. US-009 identification MUST NOT enable LinkedIn publication; a temporary `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` verify window is allowed, and operator may restore a prior `true` value afterward (see `docs/operations/us-009-canonical-flow-a-n8n-identity-validation-2026-07-15.md`). US-011 (LinkedIn guard at activation) remains deferred.

**US-009** requires operators to identify the canonical workflow, confirm import/configuration, and define execution frequency — without activation (US-010) or LinkedIn publication enablement (US-011).

## Goals / Non-Goals

**Goals:**

- Single documented canonical identity for Flow A n8n orchestration (file path, workflow name, stable id, node count, inactive state).
- Repeatable pass/fail verification on Ubuntu server using existing scripts, extended with explicit identity checks and remediation.
- Documented proposed execution frequency aligned with editorial calendar cadence (decision record; no schedule trigger in this change).
- Operator-visible outcomes distinguishing pass, pending (import not yet run), and fail (wrong workflow, active workflow, config mismatch).

**Non-Goals:**

- Activating the workflow or adding Cron/Schedule Trigger nodes (US-010).
- Enabling LinkedIn API publication (US-011).
- Running publish/package/schedule apply paths during identification verification.
- Modifying worker endpoints, Flow B workflow, or n8n gateway compose.

## Decisions

### 1. Canonical identity constants (single source of truth)

| Field | Value |
|-------|-------|
| Repository export | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Workflow name | `Silverman Blog LinkedIn Flow A Publish` |
| Stable n8n id | `silvermanFlowAPublish01` |
| Expected node count | `26` |
| Active state (this change) | `false` |
| Non-canonical (Flow B) | `n8n/workflows/silverman-blog-linkedin-draft-generation.json` |

**Rationale:** Matches existing import script, deployment docs, RUNTIME-STATE, and archived slice-7 implementation. Centralize constants in readiness script module and reference from import/evidence scripts via shared documentation — avoid duplicating magic strings in three places without a traceable doc table.

**Alternative considered:** New standalone constants file — rejected as over-engineering for identification-only scope; Python readiness module + deployment doc table is sufficient.

### 2. Verification entry points (layered, read-only)

| Layer | Tool | Purpose |
|-------|------|---------|
| Local / CI | `scripts/flow_a_readiness.py` Phase 0 + Phase 2 | Repo export identity; Phase 2 PASS when `--n8n-workflow-export` confirms imported id `silvermanFlowAPublish01` (active=false, 26 nodes); PENDING when n8n reachable but export confirmation not provided |
| Ubuntu server | `deploy/server/import-flow-a-n8n-workflow.sh` | Idempotent import + post-import export verification **by stable id** (name secondary) |
| Ubuntu server | `deploy/server/collect-flow-a-smoke-evidence.sh` | Read-only n8n export check (**id required**, nodes, inactive) alongside worker health |

**Rationale:** Reuse proven scripts from `flow-a-deployment-readiness-and-smoke-test` rather than new ad-hoc SSH commands. Extend with explicit canonical identity assertions and remediation strings.

**Alternative considered:** New dedicated `verify-canonical-flow-a-workflow.sh` — rejected; thin wrapper adds operator confusion. Extend existing scripts with a clearly labeled "canonical identity" section in output.

### 3. Configuration verification without secrets

Import script already sets `worker_base_url` (`http://192.168.0.194:8010`) and `worker_api_key` from server `.env`. Verification MUST report:

- `worker_base_url` value (non-secret)
- `worker_api_key: configured` or `missing` (never the key)
- Phase 1 readiness: HTTP 401 on authenticated probe → API key mismatch remediation

**Rationale:** Aligns with existing security constraints in deployment-readiness spec.

### 4. Proposed execution frequency (documentation only)

**Decision:** Propose **daily polling at 09:00 UTC** via a future Schedule Trigger (US-010), aligned with editorial calendar due-item processing:

- Flow A n8n workflow polls ready folder via `POST /process-ready` when triggered.
- Editorial calendar connector (`POST /editorial-calendar/execute-flow-a-due`) remains the authority for which posts are due; n8n scheduling is the orchestration timer, not the editorial policy engine.
- Single concurrent execution enforced in US-010 (not this change).

Document in `docs/deployment/` and README Flow A section as **proposed** — export JSON and server import remain without Cron/Schedule Trigger until US-010.

**Rationale:** Daily cadence matches typical blog publishing rhythm; 09:00 UTC gives predictable operator window. Explicit UTC avoids local-time ambiguity on server.

**Alternatives considered:**

- Hourly polling — rejected; increases duplicate-run risk before US-010 concurrency controls.
- Calendar-webhook-only — rejected for US-009; frequency definition requires a concrete proposal even if activation is deferred.

### 5. Failure modes and remediation matrix

| Condition | Status | Remediation |
|-----------|--------|-------------|
| Export missing in repo | FAIL | Pull latest `origin/main`; verify path |
| Wrong workflow id in n8n | FAIL | Re-run import script; deactivate/delete duplicate |
| `active: true` | FAIL | Deactivate in n8n UI; re-verify export |
| Node count ≠ 26 | FAIL | Re-import from current repo export |
| n8n unreachable | FAIL | Check `local-ai-stack` n8n container (not gateway) |
| Import not yet run | PENDING | Run `import-flow-a-n8n-workflow.sh` |
| API key 401 in Phase 1 | FAIL | Align n8n Set Configuration with worker `.env` |
| Worker OpenAPI stale | FAIL | `deploy-worker.sh` + `verify-worker-deploy.sh` |

### 6. No processing side effects during US-009 verification

Identification checks use:

- `GET /health`, `GET /openapi.json` (read-only)
- n8n `export:workflow` (read-only)
- Optional Phase 1 `POST /process-ready` only when explicitly running full readiness Phase 1 (non-mutating scan)

Do **not** run `run-flow-a-worker-smoke.sh` or manual n8n trigger as part of US-009 identification tasks unless operator explicitly opts into Phase 3 smoke (out of US-009 scope).

### 7. Fail-closed imported workflow identity (by id)

**Decision:** Import verification and evidence collection MUST resolve the canonical workflow by stable id `silvermanFlowAPublish01` only. Matching by display name alone is forbidden (fail-open risk for a renamed duplicate). After id resolution, name, `active: false`, and node count are secondary asserts.

**Phase 2 Option A:** When `--n8n-base-url` shows n8n reachable and `--n8n-workflow-export PATH` provides a read-only n8n export (single workflow or list), Phase 2 PASSes if the export contains id `silvermanFlowAPublish01` with expected name/nodes/`active: false`. If n8n is reachable but no export path is provided, Phase 2 remains PENDING (`pending_import` / confirmation needed) with remediation pointing at import + collect (or re-run readiness with `--n8n-workflow-export`). Wrong id / active / node count → FAIL.

**Alternative considered (Option B):** Keep Phase 2 always PENDING on HTTP reachability — rejected; operators and overall readiness would never PASS Phase 2 after a successful import.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operator activates wrong workflow (Flow B) | Document side-by-side comparison; verify id `silvermanFlowAPublish01` |
| Import script run against nginx gateway | Script already filters by n8n image; retain and test gateway exclusion |
| Frequency proposal rejected later | Marked as proposal; US-010 can revise before adding trigger |
| Phase 0 pending_import mistaken for pass | Clear three-state output: PASS / PENDING / FAIL |
| Stale repo export on server import path | Remediation: copy fresh export before import |

## Migration Plan

1. Apply code/doc changes on Mac; run targeted unit tests locally.
2. Deploy doc/script updates to Ubuntu server checkout (operator copies or git pull — no automatic deploy).
3. Operator runs `import-flow-a-n8n-workflow.sh` if not already PASS.
4. Operator runs `flow_a_readiness.py --phase 2` and `collect-flow-a-smoke-evidence.sh` for evidence.
5. Record US-009 validation in progress checklist when demonstrated — not on code merge alone.

**Rollback:** Revert doc/script changes; no worker or n8n state mutation required. Workflow remains inactive throughout.

## Open Questions

- None blocking US-009. US-010 will confirm final cron expression and concurrency (single-flight) before activation.
