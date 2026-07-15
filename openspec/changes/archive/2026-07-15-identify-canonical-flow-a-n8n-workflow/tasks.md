## 1. Canonical identity constants and documentation

_US-009: Identify the canonical Flow A workflow_

- [x] 1.1 Add canonical Flow A n8n identity constants to `scripts/flow_a_readiness.py` (export path, id `silvermanFlowAPublish01`, name, node count 26)
- [x] 1.2 Document canonical identity table and Flow B distinction in README Flow A section (`n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` vs draft-generation workflow)
- [x] 1.3 Add canonical workflow identification section to `docs/deployment/ubuntu-server-worker-deployment.md` with id, name, node count, and import path defaults
- [x] 1.4 Update `docs/CURRENT-STATE.md` with canonical Flow A n8n workflow identity reference (imported, inactive; identification change applied)

## 2. Proposed execution frequency (documentation only)

_US-009: Define execution frequency (proposal; no activation)_

- [x] 2.1 Document proposed daily 09:00 UTC Schedule Trigger in README and deployment docs, labeled **proposed / not active** until US-010
- [x] 2.2 Confirm repository export `silverman-blog-linkedin-flow-a-publish.json` retains `"active": false` and contains no Cron/Webhook/Schedule Trigger nodes (no JSON changes unless drift found)

## 3. Readiness and import script extensions

_US-009: Confirm correct import and configuration; failures clearly communicated_

- [x] 3.1 Extend `scripts/flow_a_readiness.py` Phase 0/2 to report canonical id `silvermanFlowAPublish01` in export and import checks with PASS/PENDING/FAIL remediation text
- [x] 3.2 Extend `deploy/server/import-flow-a-n8n-workflow.sh` to print labeled canonical identity summary block (id, name, nodes, active, worker_base_url, worker_api_key configured)
- [x] 3.3 Extend `deploy/server/collect-flow-a-smoke-evidence.sh` with canonical identity section; FAIL when id/name/node count/active state mismatch

## 4. Tests

- [x] 4.1 Add unit tests for canonical identity constants and readiness reporting (pending_import vs fail for wrong id, active workflow)
- [x] 4.2 Add or extend tests for import script identity output patterns (shell test or documented fixture if full docker unavailable in CI)
- [x] 4.3 Run targeted pytest for touched modules; confirm existing `tests/test_n8n_workflow.py` Flow A inactive/forbidden-node assertions still pass

## 5. Operator validation on Ubuntu server (US-009 business demonstration)

_US-009: Outcome visible; no duplicate processing or unintended publication_

- [x] 5.1 On `192.168.0.194`, copy current repo export to `/home/silverman/n8n-imports/silverman-blog-linkedin-flow-a-publish.source.json` if stale
- [x] 5.2 Run `deploy/server/import-flow-a-n8n-workflow.sh`; capture `OVERALL: PASS` with id `silvermanFlowAPublish01`, 26 nodes, `active: false`, `worker_api_key: configured`
- [x] 5.3 Run `python scripts/flow_a_readiness.py --phase 2` (or Phase 0+2) against server worker URL; capture PASS or documented PENDING with remediation
- [x] 5.4 Run `deploy/server/collect-flow-a-smoke-evidence.sh`; confirm canonical identity section and n8n inactive check (no publish/package/schedule apply, no workflow activation)
- [x] 5.5 Verify LinkedIn publication enablement during US-009 verification window (`false` for the verify window; final runtime may be restored to `true` per operator — see ops note / §7.4; no LinkedIn API calls in this change)

## 6. Business validation and progress tracking

- [x] 6.1 Map demonstrated evidence to US-009 acceptance criteria in validation notes (identify, import/config, frequency proposal, visibility, failure clarity, no side effects)
- [x] 6.2 Update `docs/product/progress-checklist.md` for US-009 only when all acceptance criteria are demonstrated on server (not on code merge alone)
- [x] 6.3 Leave US-010 and US-011 checklist items unchanged (deferred to follow-up changes)
- [x] 6.4 Run `git diff --check` and secrets audit before commit approval

## Deferred (explicitly out of scope)

| Story | Deferred work |
|-------|----------------|
| **US-010** | Activate workflow, add Schedule Trigger, concurrency/single-flight, restart/recovery validation |
| **US-011** | LinkedIn publication guard confirmation at activation time |
| **BL-005** | Fully unattended Flow A test |

## 7. Pre-sync review fixes (spec↔implementation)

_Follow-ups from pre-sync review of `864545d` — complete before `/opsx-sync`_

- [x] 7.1 Fail-closed n8n export match: require `id == silvermanFlowAPublish01` in import + collect scripts; name is secondary assert; wrong id + name-only match → FAIL with re-import remediation; tests cover name-OK/id-bad
- [x] 7.2 Gate `canonical_workflow_identity` on name, node count, no-schedule, and no Execute Command checks; wire `FORBIDDEN_N8N_ORCHESTRATION_TYPE_FRAGMENTS` in `assess_canonical_export_identity`
- [x] 7.3 Phase 2 Option A: PASS when `--n8n-workflow-export` confirms imported id/name/active/nodes; PENDING when n8n reachable but export not provided; FAIL on mismatch/unreachable; align delta + design
- [x] 7.4 Update proposal/design LinkedIn non-goal language (US-009 verify window may temporarily set false; final ops state may be restored true per operator; US-011 still deferred); fix identification evidence scenario wording to require id
- [x] 7.5 Run targeted pytest + `git diff --check` (no commit unless requested)

## 8. Pre-sync delta wording / sync hygiene

_Fail-open “id or name” leftover in delta + MODIFIED for main legacy scenarios_

- [x] 8.1 Fix identification delta: import confirms by stable id only; clarify failure modes (wrong id / wrong name after id / name-only without canonical id → FAIL)
- [x] 8.2 Add MODIFIED requirements in readiness delta for legacy main scenarios that say “by id or name” (import verification + evidence n8n check)
- [x] 8.3 Reorder design.md Decision sections 6 then 7; note §5.5 historical wording vs operator restore
- [x] 8.4 `openspec validate --strict` + `git diff --check`
