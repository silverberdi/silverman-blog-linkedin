## 1. Pending-approval read and sidecar update core

- [x] 1.1 Add `flow_b_blog_draft_approval` orchestration to scan `blog-posts/pending-approval/` for Markdown + PNG + `.flow-b.json` packages; build list/detail DTOs with title/topic, discovery summary (`topic_id`, `thesis`, `referent_positioning`, `rationale`), status, relative paths, optional `target_week` / `empty_days[]`, and Markdown body on detail; confine all paths; reject traversal
- [x] 1.2 Extend pending-approval writer helpers to support atomic overwrite of existing `.flow-b.json` sidecars (US-079 exclusive-create remains for new packages); never write under `blog-posts/ready/`
- [x] 1.3 Implement approve decision update: set sidecar `status: approved`, `approved_at_utc` (optional `approved_by`); leave `.md`/`.png`/sidecar under `pending-approval/`; return `promoted: false` / `promotion_pending: true`; no Flow A / LinkedIn / Git side effects
- [x] 1.4 Implement reject update: set sidecar `status: rejected`, `rejected_at_utc`, optional single free-text `rejection_reason`; MUST NOT promote to `ready/`; default list excludes rejected while status filter/detail can show them clearly
- [x] 1.5 Support optional `dry_run` on approve/reject (validate + would-be status without durable sidecar mutation)

## 2. Authenticated HTTP API

- [x] 2.1 Add authenticated `GET /flow-b/pending-approval-drafts` (list) and `GET /flow-b/pending-approval-drafts/{draft_id}` (detail); reject unauthenticated callers; secret-safe structured errors; empty folder returns empty list
- [x] 2.2 Add authenticated `GET /flow-b/pending-approval-drafts/{draft_id}/image` confined to the sibling PNG under `pending-approval/`; reject unauthenticated and traversal attempts
- [x] 2.3 Add authenticated `POST /flow-b/pending-approval-drafts/{draft_id}/approve` and `…/reject` per design; no promote/move to `ready/`; no US-081 spill routes; no US-082 trigger; no n8n Execute Command (ADR-0001)
- [x] 2.4 Expose new endpoints in OpenAPI alongside existing Flow B routes; leave `generate-blog-drafts`, `discover-topics`, `calendar-gaps`, and settings GET/PUT contracts unchanged

## 3. Silverman Authority Manager UI

- [x] 3.1 Extend `frontend/linkedin-variant-supervision-console/` with a Flow B pending-drafts presentation (view/panel reachable from AppShell — not a separate app) that lists pending drafts and shows title/topic, body, image, discovery summary, and gap week / empty-days when present
- [x] 3.2 Wire Approve and Reject actions to the authenticated worker endpoints; honor console dry-run default; communicate approved-but-not-promoted, rejected/blocked, and failure states clearly; do not add revision-history CMS, multi-round feedback threads, or mandatory edit-apply loop
- [x] 3.3 Rebuild and publish static console assets into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` per existing pipeline

## 4. Tests

- [x] 4.1 Unit/API tests: list with discovery + optional gap fields; empty folder OK; detail body + auth image; path traversal rejected; approve updates sidecar and leaves files under `pending-approval/` with no `ready/` writes; reject updates sidecar and remains non-publishable; default list excludes rejected; dry-run does not mutate; auth required; no Flow A / LinkedIn publish calls
- [x] 4.2 Frontend tests for pending-drafts presentation and approve/reject affordances (mirror US-076 gap-settings test style); run targeted pytest + frontend tests; fix warnings attributable to this change; `git diff --check` clean

## 5. Docs and product status

- [x] 5.1 Update `docs/operations/flow-b-simplified-policy.md` (and glossary if needed) so US-080 approve/reject presentation is the runtime Authority Manager + worker path, and promote/spill/trigger are not claimed implemented
- [x] 5.2 Update `docs/CURRENT-STATE.md` to record blog draft approve/reject presentation **implemented** (not Story accepted / not deployed unless separately approved)
- [x] 5.3 After demonstrated automated AC, update `docs/product/user-stories.md` US-080 and `docs/product/progress-checklist.md` only to the validated state — do not mark Story accepted without operator walkthrough; do not close BL-018; leave US-081–US-082 unchecked

## 6. Business validation gate

- [x] 6.1 Walk US-080 acceptance criteria against local worker + console evidence (present pending drafts in Authority Manager; approve and reject actions; no revision CMS / multi-round feedback / mandatory edit-apply; rejected non-publishable; outcome and failures communicated; no unintended duplication of US-076–US-079; ADR-0001 HTTP)
- [x] 6.2 Record any remaining gaps explicitly; leave US-081–US-082 and BL-018 close unchecked

### Remaining gaps (explicit — fill after implementation)

- Operator walkthrough / “outcome visible” AC → Story accepted still open
- Deploy to `192.168.0.194` not done (requires separate approval)
- US-081 promote + spill A and US-082 gap trigger not implemented
- BL-018 remains open until US-080+US-081 Story accepted (and business outcome validated)
