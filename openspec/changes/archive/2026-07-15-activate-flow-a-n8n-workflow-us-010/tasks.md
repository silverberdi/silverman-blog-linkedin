## 1. Export: schedule + single-flight (US-010 AC: activate prep, concurrency)

- [x] 1.1 Edit `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`: add Schedule Trigger daily `0 9 * * *` UTC; keep Manual Trigger; wire both into Set Configuration
- [x] 1.2 Add single-flight guard on shared path after Set Configuration / before Health Check (static-data lock + TTL default 2h + `skipped_already_running` branch); release lock on terminal stop paths
- [x] 1.3 Keep repository `"active": false`; measure final node count; update identity constant everywhere (baseline target 28)
- [x] 1.4 Confirm HTTP-only boundary (no Execute Command / LinkedIn / GitHub / filesystem nodes) and no secrets in export

## 2. Scripts and tests (US-010 AC: operator visibility, no unintended duplication checks)

- [x] 2.1 Update `deploy/server/import-flow-a-n8n-workflow.sh`: expected node count; require Schedule Trigger; still verify post-import `active: false`; note separate activation step
- [x] 2.2 Update `deploy/server/collect-flow-a-smoke-evidence.sh` (and/or add activation verifier): mode-aware `active` expectation (`--expect-server-active` or equivalent); require schedule; pass/fail/pending + remediation; never print secrets
- [x] 2.3 Update `scripts/flow_a_readiness.py`: require Schedule Trigger on repo export; keep export `active: false`; remove/replace US-009 “forbid schedule” check; update node count constant and remediation copy
- [x] 2.4 Update lightweight workflow tests (`tests/test_n8n_workflow.py` and readiness tests) for schedule-required + export-inactive + guard presence + node count
- [x] 2.5 Run targeted pytest for touched tests; fix failures; `git diff --check`

## 3. Documentation (US-010 AC: outcome visible; clear remediation)

- [x] 3.1 Update README Flow A section: schedule materialized, export inactive vs server active, single-flight, Manual Trigger retained, ready-folder path vs calendar connector
- [x] 3.2 Update deployment/ops docs with import → verify → activate procedure, failure modes, and empty-ready preferred evidence path
- [x] 3.3 Document US-011 / BL-005 still open; do not instruct LinkedIn flag flips for US-010

## 4. Server activation (US-010 AC: activate the workflow) — approval-gated

- [x] 4.1 Sync/deploy updated export to `192.168.0.194`; re-run `import-flow-a-n8n-workflow.sh`; confirm id `silvermanFlowAPublish01`, schedule, node count, inactive immediately after import
- [x] 4.2 After explicit operator approval: activate `silvermanFlowAPublish01` on server; verify `active: true` via activation evidence mode

## 5. Concurrency + restart evidence (US-010 AC: prevent duplicate/concurrent; restart/recovery; no unintended duplication)

- [x] 5.1 With empty ready (default): Manual run → clean no-candidates stop; confirm no publish/package/schedule apply
- [x] 5.2 Concurrent run while lock held → `skipped_already_running`; no second apply chain
- [x] 5.3 Idle n8n container restart → workflow remains active; next Manual no-op succeeds; no stuck permanent lock
- [x] 5.4 Force-kill / lock-without-release past TTL → next run acquires lock; record PASS
- [x] 5.5 Idempotent path: rerun against already-published or empty ready → no duplicate artifacts
- [x] 5.6 Write `docs/operations/us-010-flow-a-n8n-activation-validation-YYYY-MM-DD.md` with pass/fail per step (no LinkedIn API calls; no live blog side effects without separate approval)

## 6. Context and product progress (demonstrated outcomes only)

- [x] 6.1 Update `docs/CURRENT-STATE.md`: n8n Flow A activated on schedule; single-flight; still not BL-005 unattended; US-011 open
- [x] 6.2 Update `docs/RUNTIME-STATE.md`: workflow active + schedule facts; do not close US-011; do not flip LinkedIn flag unless separately approved (default: no flip)
- [x] 6.3 Update `docs/product/user-stories.md` US-010 header (add missing `### US-010` if needed) and mark ACs only when demonstrated; leave US-011 open
- [x] 6.4 Update `docs/product/progress-checklist.md` for US-010 when validated; keep BL-004 open until US-011

## 7. Business validation

- [x] 7.1 Map evidence to every US-010 AC: activate; concurrency; restart/recovery; operator-visible outcomes; clear failures; no unintended duplication
- [x] 7.2 Confirm out of scope remains incomplete: US-011, BL-005, BL-007 WIP, Flow B, worker contract expansion
- [x] 7.3 Run `openspec validate activate-flow-a-n8n-workflow-us-010 --strict` after apply edits; prepare `/opsx-verify` before any commit request
