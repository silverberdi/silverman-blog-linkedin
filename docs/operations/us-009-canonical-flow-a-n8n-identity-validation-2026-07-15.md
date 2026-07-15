# US-009 — Canonical Flow A n8n identity validation

**Date (UTC):** 2026-07-15  
**Host:** `192.168.0.194`  
**Change:** `identify-canonical-flow-a-n8n-workflow`  
**Scope:** Identification, import/config confirmation, proposed frequency documentation — not activation (US-010) and not LinkedIn guard activation work (US-011).

## Acceptance criteria map

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Identify the canonical Flow A workflow | **PASS** | Export `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json`; import id `silvermanFlowAPublish01`; name **Silverman Blog LinkedIn Flow A Publish**; 26 nodes; not Flow B / not publish-pending |
| Confirm correct import and configuration | **PASS** | `import-flow-a-n8n-workflow.sh` → `OVERALL: PASS`; identity summary; `worker_api_key: configured`; `active: false` |
| Define execution frequency | **PASS (docs only)** | Proposed **daily 09:00 UTC** labeled not active until US-010; export has no Cron/Webhook/Schedule Trigger |
| Outcome visible / understandable | **PASS** | Import script identity block; `collect-flow-a-smoke-evidence.sh` canonical identity section; README + deployment docs |
| Failures / blocked states clearly communicated | **PASS** | Readiness Phase 0 FAIL on missing expected commits with message; identity helpers PENDING/FAIL remediation text in `scripts/flow_a_readiness.py` |
| No duplicate / unintended side effects | **PASS (ops window)** | No workflow activation; no Schedule Trigger added; no publish/package/schedule apply; collect evidence remained read-only |

## Commands and outcomes

### 5.1 Export source freshness

- Host import source and repo export md5: `3d8b2622aebe34cc8906e3368e231b70` (match; no copy required).

### 5.2 Import script

```text
/home/silverman/silverman-blog-linkedin-worker/import-flow-a-n8n-workflow.sh
```

- `OVERALL: PASS (Flow A workflow imported; remains inactive)`
- id `silvermanFlowAPublish01`, 26/26 nodes, `active: false`, `worker_api_key: configured`
- Canonical identity summary printed
- NOTE: proposed schedule daily 09:00 UTC documentation-only until US-010

### 5.3 Readiness

Default `--expected-commit` set failed on server checkout because objects `96519c3` / `9dba064` are absent from `/home/silverman/silverman-blog-linkedin-src` (incomplete git object graph vs Mac remote). Remediation used for this validation:

```text
python3 scripts/flow_a_readiness.py --phase 2 \
  --worker-base-url http://192.168.0.194:8010 \
  --expected-commit 88cd5bc
```

- `OVERALL: PASS`
- All canonical identity checks PASS (name, nodes, no schedule triggers, identity summary)
- Phase 2 n8n HTTP smoke SKIP (no `--n8n-base-url`); n8n identity covered by import + evidence scripts instead

### 5.4 Collect evidence

```text
/home/silverman/silverman-blog-linkedin-worker/collect-flow-a-smoke-evidence.sh
```

- Canonical identity section present
- n8n: found `silvermanFlowAPublish01`, inactive, 26 nodes
- `OVERALL: PASS`
- Read-only (no activation, no LinkedIn API, no Flow A apply endpoints)

### 5.5 LinkedIn enablement

| Step | Result |
|------|--------|
| Temporarily set `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` + recreate worker | **PASS** — `.env` and container both `false` |
| US-009 no-unintended-publication check during false window | Satisfied (workflow inactive; no LinkedIn API in this change) |
| Restore `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` + recreate worker (operator request 2026-07-15) | **PASS** — `.env` and container both `true` |

Compose file used: `silverman-worker.compose.yaml` (not `docker-compose.worker.yml`).

**Final operational state:** LinkedIn publication enablement remains **`true`** by operator request after the US-009 verification window.

## Side effects explicitly not performed

- No n8n workflow activation
- No Cron / Webhook / Schedule Trigger added
- No `POST /publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`
- No LinkedIn queue/publish endpoints invoked

## Follow-ups

| Item | Owner |
|------|--------|
| Deepen or re-sync `silverman-blog-linkedin-src` git objects so default expected commits resolve | Deploy / src sync |
| US-010 — activation + Schedule Trigger | Separate OpenSpec change |
| US-011 — LinkedIn guard at activation | Separate OpenSpec change |
