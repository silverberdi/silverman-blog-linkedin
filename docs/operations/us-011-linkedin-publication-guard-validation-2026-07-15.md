# US-011 — LinkedIn publication guard validation

**Date (UTC):** 2026-07-15  
**Host:** `192.168.0.194`  
**Change:** `flow-a-linkedin-publication-guard-us-011`  
**Scope:** Prove Flow A activation/schedule is independent of LinkedIn API publication enablement; fail-closed when `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not `true`; restore prior operator-approved baseline. Prefer empty `blog-posts/ready/`. No new LinkedIn posts. No BL-005. No BL-007 WIP.

## Overall status

**`PASS`**

## Semantic (confirmed)

| Claim | Observed |
|-------|----------|
| Flow A active + Schedule 09:00 UTC | Server workflow `silvermanFlowAPublish01` remains `active: true`, 31 nodes |
| `distribution_scheduled` ≠ LinkedIn API published | Campaign scheduling unchanged by this evidence |
| LinkedIn API published | Guarded; fail-closed proven with flag `false` |
| US-011 ≠ permanent LinkedIn-off | Baseline restored to `true` |

## Out of scope (not claimed)

- BL-005 fully unattended Flow A
- BL-007 / `auto_queue_pending` / publish-pending WIP
- Flow B
- Calendar rewrite to `POST /editorial-calendar/execute-flow-a-due`
- New LinkedIn routes / OpenAPI expansion
- Permanent LinkedIn-off after this report
- n8n Execute Command

## Validation window

### 3.1 Record baseline (read-only)

| Check | Result | Notes |
|-------|--------|-------|
| `.env` `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | **PASS** | `true` |
| Worker container env same flag | **PASS** | `true` |
| Recorded baseline value | **PASS** | `true` (restored in 3.5) |
| `blog-posts/ready/` empty | **PASS** | `ready_count=0` |

### 3.2 Disable window (operator-approved)

| Check | Result | Notes |
|-------|--------|-------|
| Operator approval recorded | **PASS** | chat approval 2026-07-15 |
| Flag set to `false` in `.env` | **PASS** | |
| Worker recreated | **PASS** | `docker compose … --force-recreate --no-build` |
| Container env confirms `false` | **PASS** | `expect=false env=false container=false` |

### 3.3 Fail-closed probe

No pre-existing `queued` fixture. Temporary safe fixture created from a `pending` variant, then restored to `pending` after probe.

| Check | Result | Notes |
|-------|--------|-------|
| Safe fixture | **PASS** | campaign `flow-a-2026-07-10-deferring-is-not-avoiding-it-can-be-architecture`, variant `short-provocative` |
| Queue (`dry_run=false`, `publish_after_utc=2099-01-01T00:00:00Z`) | **PASS** | HTTP 200; `publish_state=queued`; no LinkedIn API |
| Real publish-due (`dry_run=false`, `publish_now=true`) | **PASS** | HTTP 200; errors include `linkedin_publish_not_enabled` |
| Variant not marked `failed` in metadata | **PASS** | campaign `publish_state` remained `queued` (not `failed` / not `published`) |
| No LinkedIn API publish / URN | **PASS** | `linkedin_post_urn=null` |
| Fixture restored to `pending` | **PASS** | via worker container write of pre-queue snapshot |

### 3.4 Flow A has no LinkedIn API path

| Check | Result | Notes |
|-------|--------|-------|
| Repo/import export has no LinkedIn API nodes/hosts/publication paths | **PASS** | `/home/silverman/n8n-imports/silverman-blog-linkedin-flow-a-publish.source.json`, 31 nodes, export `active=false` |
| Server workflow no LinkedIn publication paths | **PASS** | `silvermanFlowAPublish01` `active=true`, 31 nodes |
| Empty ready preferred | **PASS** | `ready_count=0` throughout |

### 3.5 Restore baseline

| Check | Result | Notes |
|-------|--------|-------|
| Restored value equals recorded baseline | **PASS** | `true` |
| Worker recreated | **PASS** | trap + explicit recreate |
| `.env` + container match | **PASS** | `expect=true env=true container=true` |
| Operator lasting override | N/A | none — restored baseline |

## User story mapping

| Criterion | Result |
|-----------|--------|
| Keep LinkedIn publication disabled until separately approved | **PASS** — flag independently gated; Flow A does not invoke LinkedIn API; fail-closed proven |
| Outcome visible and understandable | **PASS** — this report + flag/probe logs (no secrets) |
| Failures or blocked states clearly communicated | **PASS** — stable `linkedin_publish_not_enabled` |
| Existing completed work not duplicated / unintentionally changed | **PASS** — US-009/US-010 activation left intact; Flow A remains active; BL-007 WIP not mixed |

## BL-004 / BL-005

- **BL-004** closable: US-009, US-010, and US-011 demonstrated.
- **BL-005** remains open.

## Notes

- No API keys, tokens, client secrets, or authorization codes recorded here.
- Compose file: `silverman-worker.compose.yaml`.
- Temporary host-side campaign JSON restore failed with `PermissionError` (container-owned file); restore completed successfully via `docker exec` write to `/data/silverman-blog-linkedin/...`.
- Final operational LinkedIn flag: **`true`** (restored baseline).
