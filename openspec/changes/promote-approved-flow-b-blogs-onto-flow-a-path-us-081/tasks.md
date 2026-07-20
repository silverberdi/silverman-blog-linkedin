## 1. Promote core (pending-approval → ready)

- [x] 1.1 Add `flow_b_blog_draft_promotion` orchestration: require sidecar `status=approved` with durable approval fields (`approved_at_utc`, draft id/slug, `approved_by` when present); validate complete `.md` + `.png` + `.flow-b.json` under `blog-posts/pending-approval/`; confine paths; reject traversal
- [x] 1.2 Implement atomic move of Markdown + PNG + sidecar into `blog-posts/ready/` preserving basename; update sidecar to `status: promoted` with `promoted_at_utc` / `promoted_by`, preserved approval fields, updated ready relative paths, `origin: flow_b`, and preserved `target_week` / `empty_days[]` when present; fail closed on ready basename collision or incomplete pair
- [x] 1.3 Support idempotent re-promote when already `promoted` with matching ready artifacts; optional `dry_run` validates without moves/sidecar mutation; MUST NOT invoke Flow A publish/package/schedule, Git publish, or LinkedIn API publish

## 2. Authenticated HTTP API

- [x] 2.1 Add authenticated `POST /flow-b/pending-approval-drafts/{draft_id}/promote` per design; reject unauthenticated callers; structured secret-safe errors for not-approved / rejected / incomplete / collision / missing
- [x] 2.2 Expose promote in OpenAPI alongside existing Flow B routes; leave US-080 approve/reject/list and US-076–US-079 contracts unchanged in purpose; no US-082 trigger; no n8n Execute Command (ADR-0001)

## 3. Spill algorithm A on Flow A schedule

- [x] 3.1 Implement `flow_b_spill_a` placement helper: (1) target-week gap days chronological → (2) other days in target week with capacity → (3) forward day-by-day after the week; capacity = US-040K / `density_max_per_local_day` max 2; fail closed rather than exceed density
- [x] 3.2 Wire `schedule_linkedin_distribution` to accept strategy `flow_b_spill_a`; auto-select when default strategy + Flow B provenance with usable gap context; keep `flow_a_staggered` for non–Flow-B (and explicit override); campaign `flow` remains `flow_a`; stamp/read provenance from promoted sidecar or campaign metadata; no LinkedIn API publish from schedule

## 4. Flow A pending-approval rejection

- [x] 4.1 Fail closed in `publish_blog_post` (and ready-inbox acceptance if needed) when `source_relative_path` targets `blog-posts/pending-approval/`; stable error e.g. `blog_publish_pending_approval_not_allowed`; no public writes

## 5. Silverman Authority Manager UI

- [x] 5.1 Extend Flow B drafts panel with Promote for approved-not-promoted drafts; communicate pending / approved-not-promoted / promoted / rejected and failures; honor dry-run; do not remove or redesign US-080 approve/reject; no revision CMS / multi-round feedback / mandatory edit-apply
- [x] 5.2 Rebuild and publish static console assets into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` per existing pipeline

## 6. Tests

- [x] 6.1 Unit/API tests: promote moves trio to `ready/` with who/when/draft id; idempotent re-promote; reject non-approved/rejected/incomplete/collision; dry-run no move; auth required; no Flow A/LinkedIn/Git side effects from promote
- [x] 6.2 Schedule tests: spill A order under max 2; within-week then forward; fail closed on density exhaustion; non–Flow-B keeps stagger; explicit stagger override
- [x] 6.3 Publish tests: `pending-approval/` path rejected; unapproved drafts not Flow A publish input
- [x] 6.4 Frontend tests for promote affordance and status copy; run targeted pytest + frontend tests; fix warnings attributable to this change; `git diff --check` clean

## 7. Docs and product status

- [x] 7.1 Update `docs/operations/flow-b-simplified-policy.md` (and glossary if needed) so US-081 promote + spill A is the runtime path, and US-082 trigger is not claimed implemented; approve remains decision-only
- [x] 7.2 Update `docs/CURRENT-STATE.md` to record promote + spill A **implemented** (not Story accepted / not deployed unless separately approved)
- [x] 7.3 After demonstrated automated AC, update `docs/product/user-stories.md` US-081 and `docs/product/progress-checklist.md` only to the validated state — do not mark Story accepted without operator walkthrough; do not close BL-018 without US-080+US-081 Story accepted; leave US-082 unchecked

## 8. Business validation gate

- [x] 8.1 Walk US-081 acceptance criteria against local worker + console evidence (approval metadata; promote to `ready/`; Flow A reuse / no second LinkedIn gate; spill A; pending-approval rejected by publish; outcome and failures communicated; Flow A guards and US-040K density remain authoritative; ADR-0001 HTTP)
- [x] 8.2 Record any remaining gaps explicitly; leave US-082 and BL-018 close unchecked

### Remaining gaps (explicit — fill after implementation)

- Operator walkthrough / “outcome visible” AC → Story accepted still open
- Deploy to `192.168.0.194` not done (requires separate approval)
- US-082 gap trigger not implemented
- BL-018 remains open until US-080+US-081 Story accepted (and business outcome validated)
- Console static rebuild present locally (`index-CQysXXxM.js` / `index-zJhhRJLW.css`); live worker still serves prior US-080 bundle until deploy
