## Why

BL-013 / US-034 requires that simultaneous or repeated Flow A triggers cannot create duplicate distribution schedules or duplicate LinkedIn API publications, and that abandoned processing claims can be recovered via stale detect + reclaim with operator-visible outcomes. US-033 already hardened claim CAS, image skip/reuse, and blog handoff idempotency; schedule and LinkedIn publish still rely primarily on sequential idempotency (matching schedule keys / `linkedin_publish_already_published` + URN evidence) without a story-scoped concurrency contract, and abandoned-claim reclaim is implemented vocabulary without being an accepted US-034 deliverable. Without closing those gaps, overlapping calendar/n8n/manual HTTP calls can still risk duplicate schedule metadata transitions, duplicate LinkedIn API posts under first-publish races, or unclear reclaim outcomes.

## What Changes

- Extend the existing `flow-a-concurrency-duplicate-execution-protection` capability with a **US-034-only** slice: duplicate scheduling prevention, duplicate LinkedIn API publication prevention, and abandoned-claim stale detect + reclaim as a story deliverable with operator-visible outcomes.
- Harden distribution scheduling so concurrent or repeated `schedule_linkedin_distribution` / `POST /schedule-linkedin-distribution` for the same campaign / schedule identity cannot create duplicate schedule slots, duplicate `state_history` transitions, or conflicting anchors; reuse existing schedule idempotency key and `linkedin_schedule_metadata_mismatch` vocabulary.
- Harden LinkedIn publish-due / queue paths so once-only LinkedIn API publish holds under concurrent or repeated triggers; reuse existing publication idempotency, `linkedin_publish_already_published`, and URN / `published_at` evidence preservation (including BL-008 recovery contracts left intact).
- Make abandoned processing-claim recovery a demonstrated deliverable: stale detection (`processing` → `stale`, `recovery_classification=retryable`) and reclaim (`stale` → `processing` via existing claim helpers) with clear operator-visible completed / skipped / blocked outcomes — without inventing a parallel queue ontology.
- Prefer additive contracts on existing schedule, LinkedIn publication, and claim/stale/reclaim paths; **do not** introduce new primary endpoints unless design inspection proves an unavoidable gap after inspecting `src/` and `tests/`.
- Preserve US-033 protections unchanged except where a narrow shared dependency (for example CAS write helpers reused by schedule/publish) is required.
- Update CURRENT-STATE and product progress only to the demonstrated implementation level; do **not** mark US-034 accepted, US-035 started, or BL-013 closed from proposal or code alone.

## Goals

- Satisfy US-034 acceptance criteria: prevent duplicate scheduling; prevent duplicate LinkedIn publication; recover abandoned processing claims; make outcomes visible; communicate failures/blocks clearly; avoid duplicating or unintentionally changing completed work (including US-033 and completed schedule / LinkedIn publish evidence).
- Reuse existing claim / stale / reclaim vocabulary from `flow-a-operational-queue-lifecycle` and schedule / LinkedIn once-only / idempotency vocabulary from `linkedin-distribution-scheduling-model` and `linkedin-publication-integration`.
- Prefer ADR-0001 HTTP worker enforcement over relying solely on n8n single-flight (n8n guard remains complementary; worker must remain safe if orchestration overlaps).
- Fail closed on ambiguous schedule or publication identity; secret-safe responses.
- Keep scope to the smallest coherent worker capability for **US-034 only**.

## Non-goals

- **US-033 surfaces** already done: post-processing claim CAS, image ComfyUI skip/reuse, blog handoff `already_published` / `blog_publish_target_exists` — except narrow shared dependencies (for example reusing CAS/flock write helpers).
- **US-035:** restart validation.
- Changing BL-012 incomplete-campaign recovery contracts except where reclaim/claim rejection is exercised without changing recovery semantics.
- Reworking LinkedIn publication recovery (BL-008 / US-021–US-022) beyond ensuring once-only publish under concurrency reuses those contracts.
- Broad metadata locking for unrelated campaign fields, new queue folders, or a second claim ontology / parallel queue model.
- Git push, live-site mutation, deploy, or production n8n activation as part of this change.
- New primary HTTP endpoints unless apply-time design inspection proves an unavoidable gap.
- Marking US-034 accepted or BL-013 closed from proposal/code alone.

## Acceptance Criteria Coverage

- **Prevent duplicate scheduling:** concurrent or repeated schedule triggers for the same campaign / distribution identity must not create a second schedule set, duplicate `distribution_scheduled` history, or conflicting anchors; matching proof returns completed idempotent outcome; mismatch fails closed with `linkedin_schedule_metadata_mismatch` (or equivalent stable code).
- **Prevent duplicate LinkedIn publication:** concurrent or repeated publish-due / queue paths must not create a second LinkedIn API post for a variant that already has (or mid-flight obtains) durable URN evidence; reuse `linkedin_publish_already_published` / once-only publish rules; preserve stored `linkedin_post_urn` and `published_at`.
- **Recover abandoned processing claims:** stale detect marks eligible abandoned `processing` claims `stale` + `retryable`; reclaim via existing claim path yields a new `processing` attempt with `reclaimed_from_stale` (or equivalent) operator-visible outcome; non-stale active claims remain `manual_intervention_required` / already-claimed.
- **Visible and understandable outcome:** structured JSON / result fields expose schedule completed vs mismatch, LinkedIn already-published vs first publish, stale detect completed/skipped, reclaim completed vs already-claimed — no secrets or content bodies.
- **Failures or blocked states clearly communicated:** stable codes for schedule mismatch, already-published, already-claimed / non-stale block, auth/validation / not-enabled failures.
- **Existing completed work not duplicated or unintentionally changed:** US-033 protections, completed schedule evidence, and LinkedIn URN evidence are preserved; idempotent and contention-loser paths short-circuit rather than rewrite.

US-033 criteria (post / image / blog) and US-035 (restart validation) are intentionally excluded as deliverables of this change.

## Capabilities

### New Capabilities

- None. US-034 extends the existing concurrency capability rather than introducing a second named capability.

### Modified Capabilities

- `flow-a-concurrency-duplicate-execution-protection`: Extend purpose and requirements with the US-034 slice (duplicate scheduling, duplicate LinkedIn API publication, abandoned-claim stale detect + reclaim as deliverable, operator-visible outcomes, preserve US-033 / completed work). Update the US-033-only scope boundary so US-034 surfaces are in scope for this change while US-035 remains out.
- `linkedin-distribution-scheduling-model`: Narrow hardening so concurrent or repeated schedule requests for the same campaign / schedule identity cannot duplicate slots or transitions; clarify atomic or equivalent contention handling around first-time schedule apply while preserving sequential idempotency and mismatch fail-closed behavior.
- `linkedin-publication-integration`: Narrow hardening so concurrent or repeated publish-due / queue paths cannot double-call LinkedIn API for the same variant identity; strengthen once-only publish under contention while preserving `linkedin_publish_already_published`, URN evidence, enablement guards, and BL-008 recovery contracts.
- `flow-a-operational-queue-lifecycle`: Narrow clarification that stale detection and reclaim are US-034 story deliverables with operator-visible detect / reclaim / blocked outcomes, without inventing new execution states or changing the existing stale TTL / reclaim vocabulary.

## Impact

- **API:** no new primary endpoints expected; strengthen behavior and response clarity on `POST /schedule-linkedin-distribution`, LinkedIn queue / publish-due endpoints, and existing claim / stale / reclaim helpers (and any connector paths that invoke them). Any additive response fields must be secret-safe and non-breaking.
- **Worker:** schedule metadata writes and LinkedIn publish apply paths may reuse or extend campaign-metadata CAS/flock patterns introduced for US-033 claim; stale detect + reclaim remain in `flow_a_operational_queue` (and callers); incomplete-campaign recovery and LinkedIn publication recovery stay intact.
- **Data:** no new lifecycle states; optional additive operator-visible concurrency / reclaim outcome fields only if design proves they are required without overlapping US-035 restart semantics.
- **n8n:** orchestration single-flight remains complementary; this change does not ship or activate production workflows.
- **Tests and docs:** concurrent/repeated-trigger behavioral tests for schedule idempotency under race, LinkedIn once-only under race, stale detect + reclaim operator outcomes; CURRENT-STATE / operator docs / product progress updated only after demonstrated implementation — US-033 stays accepted; US-035 and BL-013 remain open.
- **Out of scope systems:** no Git/live-site mutation; no deploy; no production n8n activation; no US-035 restart validation as part of this change.
