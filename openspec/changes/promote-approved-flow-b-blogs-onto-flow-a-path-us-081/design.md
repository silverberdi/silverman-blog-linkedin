## Context

US-080 is deployed on `192.168.0.194:8010` (`BUILD_REVISION=cb36fa9…`): authenticated list/detail/approve/reject under `/flow-b/pending-approval-drafts…` plus Authority Manager **Flow B drafts** panel. Approve records sidecar `status: approved`, `approved_at_utc`, `approved_by`, and returns `promoted: false` / `promotion_pending: true` without moving files. US-079 packages (`.md` + `.png` + `.flow-b.json`) remain under `blog-posts/pending-approval/`, often with optional `target_week` / `empty_days[]` from gap context.

Flow A already publishes from `blog-posts/ready/` (then queued/processed), packages LinkedIn derivatives, schedules with strategy `flow_a_staggered` (3-day stagger), and optionally supervises pending variants. US-040K `local_day_density` enforces max 2 members per operator-local day. Spill algorithm A is policy-locked in `docs/operations/flow-b-simplified-policy.md` but has no runtime placer yet.

Constraints: ADR-0001 (n8n → worker HTTP only); do not auto-publish without Flow A guards; do not re-implement US-080 approve/reject; do not implement US-082; do not close BL-018 or mark Story accepted without operator walkthrough; US-040K max 2 remains authoritative after promotion.

Stakeholders: content operator (promote approved drafts onto Flow A path); system operator (authenticated HTTP, clear errors); schedule implementer (spill A under density); US-082 (later trigger — must not be assumed live).

## Goals / Non-Goals

**Goals:**

- Authenticated promote that moves approved pairs into `blog-posts/ready/` with durable approval/promotion metadata.
- Authority Manager promote affordance (distinct from approve).
- After promotion, reuse Flow A publish/package/schedule/optional supervision — no second mandatory LinkedIn approval queue.
- Spill algorithm A when scheduling LinkedIn variants from Flow B–origin blogs under US-040K max 2.
- Fail closed: unapproved `pending-approval/` MUST NOT be accepted by Flow A publish paths.
- CURRENT-STATE as implemented (not Story accepted); BL-018 remains open.

**Non-Goals:**

- US-082 gap trigger.
- Auto-publish blog/LinkedIn outside Flow A guards / enablement flags.
- Revision CMS / multi-round feedback.
- Changing US-080 approve to also promote.
- Closing BL-018 or Story accepted without walkthrough.
- Changing default Flow A stagger for non–Flow-B-origin campaigns.

## Decisions

### D1 — Promote is a separate authenticated action (not approve)

**Choice:** Add `POST /flow-b/pending-approval-drafts/{draft_id}/promote` (authenticated). Preconditions:

1. Draft exists under `blog-posts/pending-approval/`.
2. Sidecar `status` is `approved` (US-080 decision already recorded).
3. Pair completeness: `.md` + sibling `.png` present (fail closed if image missing — operator can fix offline or reject).
4. Destination under `blog-posts/ready/` must not collide (same basename already present → fail closed with clear code).

Promote MUST NOT succeed for `pending_approval`, `rejected`, or already-`promoted` without idempotent semantics (see D3).

**Why:** US-080 AC and handoff explicitly split decision vs promote; user scope forbids re-implementing approve-as-promote.

**Alternatives rejected:** Promote-on-approve (breaks US-080 contract); filesystem-only operator move (no durable metadata / no ADR-0001 HTTP surface).

### D2 — Filesystem move: `.md` + `.png` + `.flow-b.json` → `ready/`

**Choice:** Atomically move the three artifacts from `pending-approval/` to `blog-posts/ready/` preserving the editorial basename (slug). Update sidecar after/during move:

| Field | Value |
|-------|--------|
| `status` | `promoted` |
| `promoted_at_utc` | UTC ISO now |
| `promoted_by` | request `promoted_by` / `approved_by` label or documented default `"operator"` |
| `draft_id` / `slug` | preserved |
| `approved_at_utc` / `approved_by` | preserved (confirm if missing → fail closed or backfill from promote principal — **prefer require approve fields present**) |
| `blog_relative_path` / `image_relative_path` / `metadata_relative_path` | updated to `ready/` paths |
| `target_week` / `empty_days` | preserved when present (needed for spill A) |
| `origin` | `flow_b` (explicit provenance stamp) |

Flow A ready scanners that select `*.md` MUST ignore `.flow-b.json` (already typical). Do not invent a new lifecycle folder.

**Why:** Keeps gap context colocated for schedule-time spill A; matches locked option A (`pending-approval/` → `ready/`).

**Alternatives rejected:** Move md/png only and drop sidecar (loses spill inputs); leave tombstone in pending-approval (double bookkeeping).

### D3 — Idempotency and status machine

**Choice:**

| Current status | Promote |
|----------------|---------|
| `approved` | Perform move + mark `promoted` |
| `promoted` and files already under `ready/` with matching provenance | Idempotent success (`promoted: true`, `already_promoted: true`) |
| `pending_approval` / `pending_approval_image_failed` | Fail closed (`draft_not_approved`) |
| `rejected` | Fail closed (`draft_rejected`) |
| `approved` but incomplete pair | Fail closed (`draft_pair_incomplete`) |

Optional `dry_run=true`: validate + return would-be ready paths **without** filesystem moves or sidecar mutation.

**Why:** Matches other Flow B dry-run / idempotent patterns; safe console retries.

### D4 — Authority Manager: Promote control on approved drafts

**Choice:** Extend existing Flow B drafts panel (do not new app):

- Show **Promote to ready/** when status is `approved` and `promotion_pending`.
- After success: show promoted / Flow A–eligible; hide promote; keep reject unavailable for promoted (or fail closed if attempted — prefer disable in UI).
- Clear copy distinguishing: pending → approved (not eligible) → promoted (Flow A eligible) → rejected.
- Honor console dry-run default.
- Do **not** remove or redesign US-080 approve/reject flows beyond adding promote and status labels.

**Why:** US-081 AC “outcome visible”; BL-018 surface is Authority Manager.

### D5 — After promotion: reuse Flow A; campaign remains `flow_a`

**Choice:** Promote only establishes Flow A eligibility (files in `ready/`). It MUST NOT itself call `publish_blog_post`, `generate_linkedin_package`, `schedule_linkedin_distribution`, LinkedIn API publish, or Git publish.

Subsequent orchestration (n8n → HTTP or operator) uses existing Flow A endpoints. New campaigns created from promoted sources MUST use `flow: flow_a` (existing publish already rejects `flow_b` campaigns). Provenance for spill A lives on sidecar / campaign metadata field `flow_b_origin` (or equivalent), **not** by setting campaign `flow` to `flow_b`.

No second mandatory LinkedIn approval queue: optional US-015/US-038+ supervision remains optional Flow A behavior only.

**Why:** AC + existing `linkedin_schedule_flow_not_allowed` / `blog_publish_flow_b_not_allowed` guards.

### D6 — Spill algorithm A as schedule strategy `flow_b_spill_a`

**Choice:** Extend `schedule_linkedin_distribution` to accept strategy `flow_b_spill_a` (in addition to default `flow_a_staggered`).

**Auto-select:** When request `strategy` is omitted/default **and** campaign (or sibling `.flow-b.json` beside source) carries Flow B gap provenance with usable `target_week` / `empty_days[]`, resolve strategy to `flow_b_spill_a`. When provenance absent, keep `flow_a_staggered`. Explicit `strategy=flow_a_staggered` MUST remain available to override.

**Placer algorithm (normative):**

1. Build occupancy for LinkedIn density members (`pending`/`queued`/`published`) per operator-local day using US-040K evaluator / calendar visibility; capacity ceiling = `density_max_per_local_day` from `load_gap_operator_settings()` (default **2**), never exceeding US-040K max 2.
2. Ordered candidate days:
   - (1) `empty_days[]` for `target_week` chronological;
   - (2) other days in that ISO week with remaining capacity;
   - (3) forward day-by-day after the week with remaining capacity.
3. Assign each package variant (canonical order) the next candidate day that has remaining capacity; place at a stable local time-of-day (reuse Flow A default anchor clock within the day, or request `start_at_utc` time component when provided).
4. Fail closed if no day can be assigned under the ceiling (structured error — do not silently exceed max 2).

Preserve schedule idempotency keys including strategy name; do not call LinkedIn API publish.

**Why:** Policy section 4; US-081 AC; keeps non–Flow-B Flow A stagger unchanged.

**Alternatives rejected:** Always replace Flow A stagger globally; invent a separate Flow B schedule endpoint (duplicates Flow A lifecycle).

### D7 — Reject `pending-approval/` on Flow A publish paths

**Choice:** At `publish_blog_post` (and queue acceptance if it accepts arbitrary paths) fail closed when `source_relative_path` is under `blog-posts/pending-approval/` or resolves there — stable error e.g. `blog_publish_pending_approval_not_allowed`. Unapproved drafts never become publish input via path aliasing. Ready-path processing MUST NOT scan `pending-approval/` as an inbox.

**Why:** US-081 AC #5; eligibility policy US-075.

### D8 — Module layout

**Choice:**

- `flow_b_blog_draft_promotion.py` — promote orchestration, path confinement, atomic moves, sidecar updates, response shaping.
- Spill placer helper (e.g. `flow_b_spill_schedule.py` or functions inside schedule module) called from `linkedin_distribution_schedule.py` when strategy is `flow_b_spill_a`.
- Thin FastAPI route in `main.py`: `POST /flow-b/pending-approval-drafts/{draft_id}/promote`.
- Frontend: promote button + status copy in `FlowBPendingDraftsModal` / related components; rebuild static assets.
- Tests: `tests/test_flow_b_blog_draft_promotion.py` (+ schedule spill unit tests; Vitest promote affordance).

Reuse US-080 path confinement / sidecar overwrite helpers where practical; do not fork approve/reject logic.

### D9 — Auth, secrets, dry-run

**Choice:** Same worker API-key auth as other `/flow-b/*` routes. Never return secrets. `dry_run` on promote as in D3. Default console mutations follow AppShell dry-run toggle.

### D10 — Docs / product status

**Choice:** Update `docs/CURRENT-STATE.md`, Flow B policy promote/spill cross-link, user-story automated AC only where demonstrated. Leave Story accepted unchecked; BL-018 open until US-080+US-081 Story accepted; US-082 unchecked. Do not claim auto-publish or gap trigger.

### D11 — Tests

**Choice:** Cover:

- Promote moves md/png/sidecar to `ready/`, records who/when/draft id, leaves no pending copies; idempotent re-promote.
- Promote of non-approved / rejected / incomplete pair fails closed; auth required; dry-run no move.
- Publish with `blog-posts/pending-approval/…` fails closed.
- Schedule with Flow B provenance applies spill A order under max 2; non–Flow-B keeps stagger; density never exceeds 2.
- No LinkedIn API / Git publish invoked by promote; no second LinkedIn approval queue introduced.
- UI: promote visible for approved; promoted state communicated.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators think promote = published | UI/API copy: Flow A–eligible only; CURRENT-STATE language |
| Ready/ basename collision | Fail closed before move |
| Spill A starves without gap context | Fall back to `flow_a_staggered` when provenance/gap fields absent; document |
| Exceeding US-040K max 2 | Capacity checks via density evaluator; fail closed |
| Scope creep into auto Flow A run | Promote MUST NOT invoke publish/package/schedule |
| Approve/promote confusion | Separate endpoints + UI labels; US-080 unchanged |
| `.flow-b.json` in ready/ confuses scanners | Ignore non-md; confine provenance read to sibling sidecar |

## Migration Plan

1. Implement after explicit `/opsx-apply` approval.
2. `/opsx-verify` → implementation commit → sync → archive (separate commits).
3. Deploy only with explicit approval; rebuild console static assets in worker image.
4. Rollback: revert worker build; already-promoted files in `ready/` remain valid Flow A inbox; sidecar `status: promoted` remains readable.
5. Drafts left `approved` but not promoted stay in `pending-approval/` until promote runs — no automatic migration.

## Open Questions

None blocking. Resolved by AC/proposal:

- Promote separate from approve (D1).
- Move trio to `ready/` with provenance (D2).
- Spill via strategy `flow_b_spill_a` + auto-select on provenance (D6).
- Campaign `flow` stays `flow_a` after promotion (D5).
- Pending-approval publish rejected (D7).
