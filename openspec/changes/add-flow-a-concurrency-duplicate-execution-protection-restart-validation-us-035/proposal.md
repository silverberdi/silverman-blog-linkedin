## Why

BL-013 / US-035 requires that worker or process interruption mid-Flow A must not create duplicate artifacts or external publications when work resumes after restart. US-033 and US-034 already harden concurrent/repeated-trigger protection (claim CAS, image skip/reuse, blog handoff idempotency, schedule first-write CAS, LinkedIn once-only URN evidence, stale detect + reclaim), but restart/crash-recovery remains an open story without dedicated validation that mid-flight interruption plus post-restart re-triggers stay fail-closed, operator-visible, and non-duplicating. Without closing that gap, operators cannot treat BL-013 as complete: a crash can leave `execution_state=processing`, and re-entry via reclaim, calendar/n8n, or incomplete-campaign recovery must be proven safe across claim, image, blog, schedule, and LinkedIn surfaces.

## What Changes

- Extend the existing `flow-a-concurrency-duplicate-execution-protection` capability with a **US-035-only** slice: restart / crash-recovery validation for mid-flight Flow A interruption, using existing claim / stale / reclaim / stage-idempotency / incomplete-campaign recovery vocabulary (no parallel queue ontology).
- Prove that after worker/process interruption mid-Flow A, resumed work (post-restart re-trigger, stale reclaim, or BL-012 resume/repair) does not duplicate artifacts or external publications when durable stage evidence already exists.
- Cover mid-flight interruption scenarios for claim, image generation, blog handoff, distribution scheduling, and LinkedIn publish surfaces as needed for restart-safety evidence.
- Keep pre-TTL post-restart non-stale `processing` claims blocked (`flow_a_execution_already_claimed` / BL-012 active-claim codes + `manual_intervention_required`) — do **not** auto-clear claims on worker startup.
- Make restart-related blocked, reclaim, resume, and fail-closed outcomes operator-visible and secret-safe.
- Prefer existing endpoints/helpers; **do not** introduce new primary endpoints unless design inspection proves an unavoidable gap.
- Preserve US-033 and US-034 protections unchanged except where a narrow shared dependency is required for evidence/tests.
- Do not break BL-012 incomplete-campaign recovery or BL-008 LinkedIn publication recovery contracts (mid-API crash remains uncertain under BL-008 — not auto-republish).
- Update CURRENT-STATE and product progress only to the demonstrated implementation level; do **not** mark US-035 accepted or BL-013 closed from proposal or code alone. Keep US-033 and US-034 accepted.

## Goals

- Satisfy US-035 acceptance criteria: validate behavior during restarts; make outcomes visible; communicate failures/blocks clearly; avoid duplicating or unintentionally changing completed work (including US-033/US-034 protections and completed schedule / LinkedIn / blog / image evidence).
- Distinguish restart/crash-recovery validation from US-034 stale TTL reclaim: reuse the same stale/reclaim vocabulary as the recovery path after interruption; do not invent a second reclaim mechanism or queue model.
- Prefer ADR-0001 HTTP worker enforcement and existing recovery endpoints over n8n-only restart assumptions (n8n idle-restart evidence from other stories remains complementary, not a substitute).
- Fail closed on ambiguity; secret-safe responses.
- Keep scope to the smallest coherent worker capability for **US-035 only**.

## Non-goals

- **US-033 surfaces** already done: atomic claim CAS, already-queued identity, pre-ComfyUI skip/reuse, `already_published` / `blog_publish_target_exists` — except narrow shared dependencies for restart evidence.
- **US-034 surfaces** already done: schedule first-write CAS, LinkedIn pre-API URN re-check + publish CAS, stale detect + reclaim operator-visible outcomes — except exercising those paths under restart scenarios.
- Auto-clearing non-stale `processing` claims on worker process start / Docker restart.
- Auto LinkedIn API republish after mid-publish crash (BL-008 uncertain / confirmation remains authoritative).
- Changing BL-012 incomplete-campaign recovery contracts beyond validating resume/repair under restart fixtures.
- Reworking LinkedIn publication recovery (BL-008 / US-021–US-022) taxonomy.
- New primary HTTP endpoints, new lifecycle states, new folders, or a parallel claim/queue ontology.
- Git push, live-site mutation, deploy, or production n8n activation as part of this change.
- Marking US-035 accepted or BL-013 closed from proposal/code alone; do not reopen or un-accept US-033 / US-034.

## Acceptance Criteria Coverage

- **Validate behavior during restarts:** mid-flight worker/process interruption must leave durable evidence intact; post-restart re-entry (blocked while non-stale, then stale reclaim and/or BL-012 resume/repair) must not create duplicate claim attempts, image generation, blog checkout artifacts, schedule sets, or LinkedIn API publications when evidence already exists.
- **Visible and understandable outcome:** structured JSON / result fields expose already-claimed / active non-stale claim blocks, stale detect + `reclaimed_from_stale`, BL-012 resume/repair/blocked reasons, and stage idempotent completes — operators can distinguish blocked waiting, reclaim resume, and fail-closed conflict.
- **Failures or blocked states clearly communicated:** stable codes for already-claimed / `manual_intervention_required`, BL-012 active-claim and evidence-ambiguity blocks, schedule mismatch, blog target-exists, LinkedIn already-published / BL-008 uncertain — secret-safe.
- **Existing completed work not duplicated or unintentionally changed:** US-033 and US-034 protections and completed schedule / LinkedIn / blog / image evidence are preserved; resume paths short-circuit on durable evidence rather than rewriting winners.

US-033 criteria (post / image / blog concurrency) and US-034 criteria (schedule / LinkedIn / stale reclaim as deliverables) are intentionally excluded as re-proposed deliverables of this change; they are preserved and exercised only as restart-safety dependencies.

## Capabilities

### New Capabilities

- None. US-035 extends the existing concurrency capability rather than introducing a second named capability.

### Modified Capabilities

- `flow-a-concurrency-duplicate-execution-protection`: Extend purpose and requirements with the US-035 slice (restart / crash-recovery validation across claim, image, blog, schedule, and LinkedIn surfaces; operator-visible blocked/reclaim/resume outcomes; preserve US-033 / US-034 / completed work). Update the scope boundary so US-035 is in scope while US-033/US-034 remain intact and are not redefined as new deliverables.
- `flow-a-operational-queue-lifecycle`: Narrow clarification that post-restart stuck `processing` claims remain blocked until stale TTL (or allowlisted BL-012 repair), and that reclaim after interruption reuses existing stale detect + claim vocabulary — without inventing startup auto-release or new execution states.
- `flow-a-incomplete-campaign-recovery`: Narrow clarification that restart validation exercises existing inspect/resume/repair contracts under mid-flight interruption fixtures without changing last-valid-stage rules, active non-stale claim blocking, allowlisted repairs, or cancel gating.

## Impact

- **API:** no new primary endpoints expected; strengthen evidence and response clarity on existing claim / stale / reclaim helpers, Flow A execute / publish / schedule / LinkedIn routes, incomplete-campaign recovery, and operational-status visibility. Any additive response fields must be secret-safe and non-breaking.
- **Worker:** primarily validation, tests, and any narrow hardening discovered when restart fixtures expose gaps (prefer stage idempotency and existing CAS / reclaim / BL-012 paths over new machinery). No startup reclaim hook unless design proves an unavoidable gap and fails closed.
- **Data:** no new lifecycle states; optional additive operator-visible fields only if design proves they are required without overlapping a parallel ontology.
- **n8n:** orchestration restart/single-flight remains complementary; this change does not ship or activate production workflows.
- **Tests and docs:** mid-flight interruption + post-restart re-entry behavioral tests for claim, image, blog, schedule, and LinkedIn; operator docs for restart vs stale reclaim; CURRENT-STATE / product progress updated only after demonstrated implementation — US-033 and US-034 stay accepted; BL-013 remains open until US-035 acceptance.
- **Out of scope systems:** no Git/live-site mutation; no deploy; no production n8n activation; no re-implementation of US-033/US-034 surfaces except narrow shared dependencies.
