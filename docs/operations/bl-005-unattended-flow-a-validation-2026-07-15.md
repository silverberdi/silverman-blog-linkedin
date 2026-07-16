# BL-005 — Unattended Flow A validation (US-012 / US-013 / US-014)

**Date (UTC):** 2026-07-15 (Manual) / 2026-07-16 (Schedule + resume)
**Host:** `192.168.0.194`  
**Change:** `run-fully-unattended-flow-a-test-bl-005`  
**Overall status:** **PASS** (Manual Post A + Schedule Post B full-path; LinkedIn API publication out of scope)

**Scope:** Dual Manual + Schedule evidence with serialized ready. Live blog side effects approved. LinkedIn API publication out of scope. BL-006 / BL-007 remain open.

## Acceptance criteria map (final)

| Story | Criterion (summary) | Manual (Post A) | Schedule (Post B) |
|-------|---------------------|-----------------|-------------------|
| US-012 | Ready accept + image generate/validate | **PASS** | **PASS** (ComfyUI PNG at Schedule) |
| US-012 | Blog publish to live site (git + live confirmation when enabled) | **PASS** | **PASS** (git at Schedule; live confirm on post-lag resume) |
| US-013 | LinkedIn package + distribution schedule | **PASS** | **PASS** |
| US-013 | Source lifecycle / not stuck in ready | **PASS** | **PASS** (`flow_a_complete` / processed) |
| US-014 | Campaign records | **PASS** | **PASS** |
| US-014 | Calendar records | **PASS** | **PASS** |
| US-014 | No mid-run technical intervention once started | **PASS** | **PASS** on Schedule fire; resume after Pages lag between executions (same US-002 pattern as Post A) |
| Shared | No LinkedIn publication API calls from Flow A | **PASS** | **PASS** (4 variants `pending`, no URN) |

## Identity / environment

| Field | Value |
|-------|-------|
| Workflow | `silvermanFlowAPublish01` / Silverman Blog LinkedIn Flow A Publish |
| HTTP path (35 nodes) | `/process-ready` → `/publish-blog-post` (git/live opt-in) → `/generate-linkedin-package` → `/schedule-linkedin-distribution` → `/complete-flow-a-ready-path` |
| Set Configuration (server) | `git_publication=true`, `live_site_confirmation=true`, `update_calendar=true` |
| Flags | `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true`, `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true` |
| Worker | `BUILD_REVISION=1784157627` (~`da21e99`); OpenAPI includes `POST /complete-flow-a-ready-path` |

## Ready-gate (§1)

| Step | Result |
|------|--------|
| Remove AppleDouble `._*` | **PASS** |
| Front matter remediation Post A/B | **PASS** |
| Serialize ready | **PASS** |
| ComfyUI / image path | **PASS** |

## Manual run — Post A (`05-keep-contracts-boring.md`)

**Status:** **PASS** (revalidation on remediated path after archaic ready-path FAIL)

- Campaign: `flow-a-2026-07-15-keep-contracts-boring` → `flow_a_complete`
- Git: `6daac7a` pushed; live confirmed `https://silverman.pro/2026/07/15/keep-contracts-boring/`
- Package + staggered schedule; source processed; calendar item completed
- Variants `publish_state=pending` (no LinkedIn API)
- Notes: Pages-lag + obsolete package residue required between-attempt hygiene; Attempt 3 CLI `outcome=flow_a_completed` (`/tmp/bl005-manual-retry-pkg-20260715T235446Z.txt`)

## Schedule run — Post B (`06-search-is-not-one-model.md`)

### Schedule fire (unattended)

- Trigger: Schedule `0 9 * * *` UTC at **2026-07-16T09:01Z** (natural; no mid-run intervention)
- ComfyUI generated companion PNG; git **pushed** `9a0158b`
- Live confirmation during fire: **404** (`blog_live_site_confirmation_unreachable`) → stopped before package/lifecycle
- Source remained in `ready/`; campaign `blog_published`

### Post-lag resume (Manual CLI, same pattern as Post A / US-002)

- Live URL already HTTP **200** before resume
- CLI execute `2026-07-16T14:26:14Z` log `/tmp/bl005-schedule-resume-20260716T142614Z.txt`
- `lastNodeExecuted=Release Single-Flight Lock`, `outcome=flow_a_completed`

### Outcomes (authoritative after resume)

| Check | Result | Evidence |
|-------|--------|----------|
| Campaign state | **PASS** | `flow_a_complete` — `flow-a-2026-07-15-search-is-not-one-model` |
| Git publish | **PASS** | `blog_git_publication.status=pushed`, commit `9a0158b` |
| Live-site confirmation | **PASS** | `confirmed` HTTP 200 — `https://silverman.pro/2026/07/15/search-is-not-one-model/` |
| LinkedIn package | **PASS** | `package_status=generated` |
| Distribution schedule | **PASS** | `strategy=flow_a_staggered`; 4 variants `pending` |
| Source lifecycle | **PASS** | `blog-posts/processed/06-search-is-not-one-model.md` (+ PNG) |
| Calendar | **PASS** | item completed; `calendar_update_status=completed`; `flow_a_completion.campaign_state=flow_a_complete` |
| LinkedIn API | **PASS** (not called) | no URN; all `pending` |
| Flow A still active | **PASS** | `active=true`, 35 nodes after resume |

## Out of scope (remain open)

- BL-006 LinkedIn variant review process
- BL-007 scheduled LinkedIn API publication
- Permanent LinkedIn enablement policy changes
- Claiming LinkedIn API posts as part of Flow A

## Next (OpenSpec)

1. `/opsx-verify` then implementation commit (on operator approval)
2. `/opsx-sync` → `/opsx-archive` as separate commits
3. No extra push/deploy required for this evidence window (worker already on remediated revision)
