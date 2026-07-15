# US-011 — LinkedIn publication guard validation

**Date (UTC):** YYYY-MM-DD  
**Host:** `192.168.0.194`  
**Change:** `flow-a-linkedin-publication-guard-us-011`  
**Scope:** Prove Flow A activation/schedule is independent of LinkedIn API publication enablement; fail-closed when `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not `true`; restore prior operator-approved baseline. Prefer empty `blog-posts/ready/`. No new LinkedIn posts. No BL-005 unattended E2E. No BL-007 WIP.

## Semantic (read first)

| Claim | True meaning |
|-------|----------------|
| Flow A active + Schedule 09:00 UTC | n8n orchestration of publish → package → schedule |
| `distribution_scheduled` | Campaign scheduling metadata only |
| LinkedIn API published | Separate path gated by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` |
| US-011 complete | Guard proven + baseline restored — **not** “LinkedIn must stay false forever” |

## Out of scope (do not claim)

- BL-005 fully unattended Flow A
- BL-007 / `auto_queue_pending` / publish-pending WIP
- Flow B
- Calendar rewrite to `POST /editorial-calendar/execute-flow-a-due`
- New LinkedIn routes / OpenAPI expansion
- Permanent LinkedIn-off policy after this report
- n8n Execute Command
- Push/deploy without separate approval

## Overall status vocabulary

| Status | When |
|--------|------|
| `PASS` | Baseline recorded; disable window; fail-closed probe; Flow A no LinkedIn API; baseline restored |
| `PENDING` | Docs/asserts exist but server evidence not yet run, or safe fixture unavailable and operator accepted partial bar |
| `FAIL` | Any step below fails without recorded operator override |

### Distinct failure / pending modes

| Mode | Status | Remediation |
|------|--------|-------------|
| Baseline not recorded before window | `FAIL` / blocked start | Stop; record `.env` + container flag; restart procedure |
| Container env ≠ intended flag during window | `FAIL` | Fix `.env`, recreate worker, confirm `docker inspect` / env print (flag value only) |
| Expected `linkedin_publish_not_enabled` not observed | `FAIL` | Confirm real-mode publish-due hit enablement gate; check `dry_run=false` and flag `false` |
| Variant marked `failed` solely for disablement | `FAIL` | Inspect campaign variant `publish_state` (must remain `queued`) |
| Flow A export contains LinkedIn API nodes/hosts | `FAIL` | Compare to canonical export; do not use publish-pending workflow as Flow A |
| Restore ≠ recorded baseline | `FAIL` | Restore recorded baseline; recreate worker; re-confirm |
| Evidence not yet collected | `PENDING` | Run this procedure on `192.168.0.194` with explicit mutation approval |
| Secrets printed | `FAIL` | Rotate if exposed; redact; never paste tokens into this report |

## Validation window checklist

### 3.1 Record baseline (read-only)

| Check | Result | Notes (no secrets) |
|-------|--------|---------------------|
| `.env` `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | | e.g. `true` |
| Worker container env same flag | | |
| Recorded baseline value | | **this value is restored in 3.5** |

### 3.2 Disable window (approval-gated)

Explicit operator approval required before mutating `.env` or recreating the worker.

| Check | Result | Notes |
|-------|--------|-------|
| Operator approval recorded | | |
| Flag set to `false` in `.env` | | |
| Worker recreated | | |
| Container env confirms `false` | | |

### 3.3 Fail-closed probe

Preferred: real-mode (`dry_run=false`) publish-due against a **safe queued** fixture while flag is `false`.

| Check | Result | Notes |
|-------|--------|-------|
| Safe fixture identified (`campaign_id` / `variant`) | | or PENDING if none |
| Response includes `linkedin_publish_not_enabled` | | |
| No LinkedIn API publish occurred | | |
| Variant `publish_state` remains `queued` (not `failed`) | | |

If no safe fixture exists: stop and ask operator before closing US-011; do not mark story complete on docs/unit tests alone unless operator explicitly accepts `PENDING` / partial bar.

### 3.4 Flow A has no LinkedIn API path

| Check | Result | Notes |
|-------|--------|-------|
| Canonical Flow A workflow has no LinkedIn API nodes/hosts | | `silvermanFlowAPublish01` |
| Empty `blog-posts/ready/` preferred | | |
| Manual/schedule no-op does not call publication endpoints | | |

### 3.5 Restore baseline (mandatory)

| Check | Result | Notes |
|-------|--------|-------|
| Restored value equals **recorded baseline** (not hardcoded `false`) | | |
| Worker recreated | | |
| `.env` + container match recorded baseline | | |
| Operator lasting override (if any) recorded explicitly | | only if different from baseline |

### 3.6 Overall

| Field | Value |
|-------|-------|
| Overall status | `PASS` / `PENDING` / `FAIL` |
| Report path | `docs/operations/us-011-linkedin-publication-guard-validation-YYYY-MM-DD.md` |

## User story mapping (fill only after demonstrated evidence)

| Criterion | Result |
|-----------|--------|
| Keep LinkedIn publication disabled until separately approved | |
| Outcome visible and understandable | |
| Failures or blocked states clearly communicated | |
| Existing completed work not duplicated / unintentionally changed | |

## BL-004 / BL-005

- Close **BL-004** only when US-009, US-010, and US-011 are all demonstrated.
- Leave **BL-005** open after US-011 `PASS`.

## Notes

- Never print API keys, tokens, client secrets, or authorization codes.
- Do not mix BL-007 `auto_queue_pending` / publish-pending paths into this evidence.
