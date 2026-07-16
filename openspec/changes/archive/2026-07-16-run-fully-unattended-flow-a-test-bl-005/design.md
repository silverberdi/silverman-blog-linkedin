## Context

BL-004 closed 2026-07-15: Flow A n8n (`silvermanFlowAPublish01`) active with Schedule `0 9 * * *` UTC + single-flight; LinkedIn publication independently gated (US-011). Worker deployed clean from HEAD (`BUILD_REVISION=1784154207`).

Operator intent for BL-005:
- Two real posts already in `blog-posts/ready/`:
  - `05-keep-contracts-boring.md` (Manual)
  - `06-search-is-not-one-model.md` (Schedule)
- Live blog side effects approved (image, publish, git, live-site confirmation).
- LinkedIn API publication out of scope.
- Two separate executions: Manual first, then Schedule — serialized ready inbox so one Manual run does not consume both.

Current blocker: posts lack required Flow A front matter (`layout`, `date`, `categories`, `tags`, `description`, `image`). AppleDouble `._*` files must be removed.

## Goals / Non-Goals

**Goals:**

- Close US-012 / US-013 / US-014 with demonstrated Manual + Schedule unattended runs.
- Prefer existing HTTP Flow A path; evidence-first; minimal code unless ready-gate remediation requires doc-only/editor fixes.
- Keep LinkedIn enablement independent (no publish-linkedin endpoints invoked by Flow A).

**Non-Goals:**

- BL-006 / BL-007; Flow B; calendar connector rewrite; LinkedIn API posts; permanent flag flips; Execute Command.

## Decisions

### 1. Serialize ready for dual execution semantics

**Decision:** At Manual time, only Post A is in `blog-posts/ready/`. After Post A reaches lifecycle completion (`flow_a_complete` / processed), move Post B into ready and wait for Schedule 09:00 UTC (or next schedule fire). Do not leave both in ready for Manual.

**Rationale:** `process-ready` can return multiple candidates; one Manual execution would otherwise consume both and invalidate “two executions.”

**Alternative:** Schedule both via two schedule days — slower; rejected for operator timeline.

### 2. Evidence-first; remediate front matter before trigger

**Decision:** Apply front-matter remediation to both posts before any trigger (required fields for `ready_post_validation`). Prefer ComfyUI image remediation when enabled rather than inventing PNG assets manually. Remove `._*` files before runs.

**Rationale:** Without remediation Manual/Schedule fail at validation with clear error codes — not an unattended success.

**Alternative:** Weaken validation for BL-005 — rejected; would reinvent product behavior.

### 3. Trigger methods

**Decision:**
- Post A: n8n Manual Trigger / CLI execute of `silvermanFlowAPublish01` with empty second slot.
- Post B: natural Schedule Trigger at `0 9 * * *` UTC with Post B alone in ready; operator observes no-touch after placement.

If Schedule wait is operationally too long, operator may approve an exceptional second Manual labeled as schedule-path dry substitute only with PENDING against US-014 “no intervention” strict reading — prefer waiting for real Schedule.

### 4. Success criteria for each run

**Decision:** PASS for a run when campaign reaches at least `distribution_scheduled` with `linkedin_distribution` and source lifecycle completed (`flow_a_complete` / processed) and calendar records updated when applicable; blog live confirmation present when `live_site_confirmation` opted in / enabled. FAIL on hard validation/publish errors. PENDING if Schedule not yet fired after Post B placement.

### 5. HTTP-only; no new endpoints

All orchestration remains n8n → worker HTTP. No LinkedIn publication endpoints. No Execute Command.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Both posts processed in one Manual | Ready serialization; verify ready_count=1 before each run |
| Front matter incomplete | Remediate before trigger; dry validation probe optional |
| Schedule delay overnight | Document expected fire time; PENDING until Schedule evidence |
| Live blog pollution | Operator-approved content; optional cleanup follow-up |
| ComfyUI unavailable | FAIL with remediation; do not fake image |
| Accidentally invoke LinkedIn API | Assert Flow A URL set; no publication paths; leave flag alone |
| AppleDouble files as candidates | Delete `._*` before runs |

## Migration Plan

1. Approve proposal → `/opsx-apply`.
2. Remediate front matter; remove AppleDouble; stage Post A only.
3. Manual execute + evidence for Post A.
4. Stage Post B; wait Schedule; evidence for Post B.
5. Update CURRENT-STATE / product progress only after both PASS.
6. Verify → commit → sync → archive.

**Rollback:** No worker contract rollback. Editorial: move sources back / remove published smoke posts only with operator approval.

## Open Questions

- Exact calendar row expectations for brand-new posts (insert vs update) — resolve during apply from editorial-calendar behavior.
- Whether Post B Schedule wait may be deferred overnight — operator timing; record PENDING if waiting.
