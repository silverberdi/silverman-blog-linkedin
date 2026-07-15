# US-010 — Flow A n8n activation validation

**Date (UTC):** 2026-07-15  
**Host:** `192.168.0.194`  
**Change:** `activate-flow-a-n8n-workflow-us-010`  
**Scope:** Activate canonical Flow A n8n workflow with Schedule Trigger + single-flight; restart/concurrency evidence. Prefer empty `blog-posts/ready/`. No LinkedIn API calls. No live blog side effects. US-011 / BL-005 remain open.

## Acceptance criteria map

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Activate the workflow | **PASS** | `n8n publish:workflow --id=silvermanFlowAPublish01` then restart; export/API `active: true`; identity `silvermanFlowAPublish01`, 31 nodes, Schedule `0 9 * * *` UTC |
| Prevent duplicate or concurrent processing | **PASS** | Held shared-mount lockfile → Manual/CLI path ends at `Stop Skipped Already Running` with `outcome: skipped_already_running`; no publish/package/schedule apply |
| Validate restart and recovery behavior | **PASS** | Idle n8n restart keeps `active: true`; expired lockfile (past TTL 2h) allows next run to acquire lock and complete empty-ready no-op |
| Outcome visible / understandable | **PASS** | Import / `--expect-server-active` evidence scripts; this report |
| Failures or blocked states clearly communicated | **PASS** | Mode-aware active checks; skip branch distinct from hard failure |
| No unintended duplication of completed work | **PASS** | Empty ready throughout evidence; idempotent rerun → `Stop No Candidates`; no publish/package/schedule apply |

## Identity after activation

| Field | Value |
|-------|-------|
| Export (git) | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` (`active: false`) |
| Server id | `silvermanFlowAPublish01` |
| Name | Silverman Blog LinkedIn Flow A Publish |
| Nodes | 31 |
| Server active | `true` |
| Schedule | `0 9 * * *` UTC |
| Single-flight | static-data + shared-mount lockfile fallback (TTL 2h) |
| HTTP path | `/process-ready` → publish → package → schedule (not calendar `execute-flow-a-due`) |

## Commands and outcomes

### 4.1 Re-import (inactive)

- Synced updated export to `/home/silverman/n8n-imports/silverman-blog-linkedin-flow-a-publish.source.json`
- Synced `import-flow-a-n8n-workflow.sh` / evidence scripts to worker layout
- `/home/silverman/silverman-blog-linkedin-worker/import-flow-a-n8n-workflow.sh` → `OVERALL: PASS`
- Post-import: `active: false`, 31/31 nodes, Schedule Trigger + Single-Flight Guard present

### 4.2 Activate

- `docker exec local-ai-stack-n8n-1 n8n publish:workflow --id=silvermanFlowAPublish01`
- Restart `local-ai-stack-n8n-1` so publish takes effect
- Export confirms `active: true`
- `collect-flow-a-smoke-evidence.sh --expect-server-active` → `OVERALL: PASS` (post-activation mode)

### 5.1 Empty ready Manual/CLI no-op

- `blog-posts/ready/` empty (`ready_count=0`)
- CLI execute (compose run after brief n8n stop): `lastNodeExecuted=Stop No Candidates`, `valid_count=0`, lock released
- No `Publish Blog Post` / package / schedule apply nodes executed

### 5.2 Concurrent skip while lock held

- Wrote held lockfile `/home/silverman/compartido_mac/.silverman-flow-a-single-flight.lock` (mapped to `/home/node/.n8n-files/` in n8n)
- Execute → `lastNodeExecuted=Stop Skipped Already Running`, `outcome=skipped_already_running`, `single_flight_acquired=false`
- No publish/package/schedule apply; lockfile remained present after skip

### 5.3 Idle restart

- Multiple n8n container restart/start windows during evidence
- Workflow remained `active: true`; subsequent empty-ready execute succeeded as no-op
- No permanent stuck lock after released/cleared paths

### 5.4 Lock TTL recovery

- Wrote lockfile with `acquired_at_ms` older than 2h TTL
- Execute acquired lock (`outcome=lock_acquired`) and completed `Stop No Candidates`

### 5.5 Idempotent empty-ready rerun

- Cleared lockfile; re-executed → again `Stop No Candidates`, no apply chain

## Side effects explicitly not performed

- No LinkedIn publication API calls
- No `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` flip (US-011 remains open)
- No posts placed in `blog-posts/ready/`
- No git commit/push for public site
- Repository export remains `"active": false`

## Qualified status language

- n8n **activated on schedule** ≠ BL-005 fully unattended Flow A
- Empty-ready evidence ≠ live blog handoff or site live
- US-011 LinkedIn publication-guard story remains incomplete

## Follow-ups

| Item | Owner |
|------|--------|
| US-011 — LinkedIn publication disabled-until-approved acceptance | Separate OpenSpec change |
| BL-005 — fully unattended Flow A with real ready content | Separate backlog item |
| Prefer rotating worker API key if CLI execute logs were retained unredacted anywhere | Operator (logs on server were redacted under `/tmp/us010-*.txt`) |
