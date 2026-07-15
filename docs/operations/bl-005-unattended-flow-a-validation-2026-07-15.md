# BL-005 — Unattended Flow A validation (US-012 / US-013 / US-014)

**Date (UTC):** 2026-07-15  
**Host:** `192.168.0.194`  
**Change:** `run-fully-unattended-flow-a-test-bl-005`  
**Overall status:** **FAIL** (Manual incomplete vs full-path ACs; Schedule not started) — blocked pending OpenSpec for ready-path gaps

**Scope:** Dual Manual + Schedule evidence with serialized ready. Live blog side effects approved. LinkedIn API publication out of scope. BL-006 / BL-007 remain open.

## Acceptance criteria map (current)

| Story | Criterion (summary) | Manual | Schedule |
|-------|---------------------|--------|----------|
| US-012 | Ready accept + image generate/validate | **PASS** | not started |
| US-012 | Blog publish to live site (git + live confirmation when enabled) | **FAIL** | — |
| US-013 | LinkedIn package + distribution schedule | **PASS** | — |
| US-013 | Source lifecycle / not stuck in ready | **FAIL** | — |
| US-014 | Campaign records | **PASS** (`distribution_scheduled`) | — |
| US-014 | Calendar records | **FAIL** / not wired on ready-path | — |
| US-014 | No mid-run technical intervention once started | **PASS** (CLI execute) | — |
| Shared | No LinkedIn publication API calls from Flow A | **PASS** | — |

## Identity / environment

| Field | Value |
|-------|-------|
| Workflow | `silvermanFlowAPublish01` / Silverman Blog LinkedIn Flow A Publish |
| HTTP path (as activated) | `/process-ready` → `/publish-blog-post` → `/generate-linkedin-package` → `/schedule-linkedin-distribution` |
| Flags | `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true`, `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true` |
| LinkedIn publication | Not invoked by Flow A (variants remain `publish_state=pending`) |

## Ready-gate (§1)

| Step | Result |
|------|--------|
| Remove AppleDouble `._*` | **PASS** |
| Front matter remediation Post A/B | **PASS** |
| Serialize ready (Post A only; Post B held) | **PASS** — hold at `blog-posts/ready-hold-bl005/06-search-is-not-one-model.md` |
| ComfyUI / image path | **PASS** — PNG generated beside Post A during publish |

## Manual run — Post A (`05-keep-contracts-boring.md`)

### Execution

- Trigger: n8n CLI `n8n execute --id=silvermanFlowAPublish01` (stop/start pattern from US-010)
- `ready_count=1` (Post A only)
- Outcome: `EXECUTE_RC=0`, `lastNodeExecuted=Release Single-Flight Lock`, `outcome` includes `lock_acquired` / `flow_a_completed`, status `success`
- Mid-run intervention: none

### Outcomes observed

| Check | Result | Evidence |
|-------|--------|----------|
| Campaign created | **PASS** | `metadata/campaigns/flow-a-2026-07-15-keep-contracts-boring.json` |
| Campaign state | `distribution_scheduled` | not `flow_a_complete` |
| Blog handoff | **PASS** | checkout file `silverberdi.github.io/_posts/2026-07-15-keep-contracts-boring.md` |
| Git publish | **FAIL** | file **untracked** (`??`) in public checkout; no commit; `blog_git_publication` absent |
| Live-site confirmation | **FAIL** | `blog_live_site_publication` absent; public URL claimed `https://silverman.pro/2026/07/15/keep-contracts-boring/` (HTTP probe previously 403 — not treated as confirmed live) |
| LinkedIn package | **PASS** | `linkedin_package.package_status=generated`, 4 variants |
| Distribution schedule | **PASS** | `strategy=flow_a_staggered`, `anchor_utc=2026-07-16T14:00:00Z`, variants `pending` with staggered `scheduled_at_utc` |
| Source lifecycle | **FAIL** | source still `blog-posts/ready/` (`source_file_status.location=ready`); companion PNG remains in ready (root-owned) |
| Calendar row | **FAIL** | no editorial calendar artifact updated for this campaign on ready-path |
| LinkedIn API publish | **PASS** (not called) | variants stay `pending` |

### Root cause (blocking OpenSpec)

Ready-folder Flow A n8n (by design/current export) does:

1. **Publish without opt-in** — `Publish Blog Post` body is only `source_relative_path` (+ optional `site_url`). It does **not** send `git_publication: true` or `live_site_confirmation: true`, so guarded Git/live steps never run even when env flags are `true`.
2. **No source lifecycle HTTP step** — `complete_flow_a_source_lifecycle` exists as a Python entry point and is wired inside `POST /editorial-calendar/execute-flow-a-due`, but there is **no** dedicated worker HTTP route for ready-path n8n to call after schedule. Specs also expect queue acceptance (`ready` → `queued`) before lifecycle (`queued` → `processed`); ready-path n8n never queue-accepts.
3. **No calendar terminal update on ready-path** — calendar terminal persistence is owned by the editorial-calendar Flow A connector, not by publish→package→schedule alone.

BL-005 proposal non-goals explicitly excluded rewriting Flow A n8n to `execute-flow-a-due` and expected **no new worker routes**. Therefore closing full-path ACs requires a **new or expanded OpenSpec change** before further n8n remediation / revalidation.

## Schedule run — Post B

**Status:** not started (blocked until Manual full-path PASS or AC scope revised).

Post B remains held at `blog-posts/ready-hold-bl005/06-search-is-not-one-model.md`.

## Remediation options (operator decide via OpenSpec)

1. **Extend ready-path orchestration (preferred if BL-005 ACs stay as written):** OpenSpec to (a) pass `git_publication` / `live_site_confirmation` from n8n Set Configuration into `POST /publish-blog-post`, (b) expose authenticated HTTP for `complete_flow_a_source_lifecycle` (and queue acceptance if required), (c) define calendar update/reconcile for ready-path or document calendar-only via connector, (d) re-import/activate, re-run Manual with clean Post A serialization. **Status 2026-07-15:** change `flow-a-ready-path-completion-http` implements (a)–(c) in repo (`POST /complete-flow-a-ready-path`, n8n export 35 nodes). **Still required for BL-005 resume:** deploy worker, re-import/activate Flow A n8n, set server Set Configuration `git_publication`/`live_site_confirmation` true, then revalidate Manual/Schedule.
2. **Narrow BL-005 evidence contract:** amend unattended E2E spec to accept ready-path success as publish→package→schedule only, and move live/lifecycle/calendar to calendar-connector or a follow-on backlog item — only with explicit product approval (contradicts current US-012–014 wording in this change).
3. **Do not** complete Manual with ad-hoc server Python/CLI side effects and call that unattended PASS.

## Side effects / hygiene notes

- Post A markdown + PNG still in `blog-posts/ready/` — must not place Post B until Post A is cleared or held to avoid double candidates.
- Public checkout post exists but is **not** on remote `main` yet — do not claim site published/live.
- LinkedIn publication flag / BL-007 WIP left untouched.

## Next step

Pause `/opsx-apply` on this change until an approved OpenSpec addresses the ready-path gaps (or product explicitly revises BL-005 ACs). Then resume Manual revalidation → Schedule → product close.
