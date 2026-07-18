## MODIFIED Requirements

### Requirement: US-033 scope boundary for concurrency and duplicate-execution protection

The worker SHALL enforce concurrency and duplicate-execution protection for Flow A under simultaneous or repeated triggers. This capability covers:

**US-033 surfaces (already delivered; MUST remain intact):**

1. Post processing (queue acceptance identity + execution claim)
2. Image generation (ComfyUI invoke / skip / reuse)
3. Blog publication (handoff / checkout publish apply idempotency)

**US-034 surfaces (already delivered; MUST remain intact):**

4. Distribution scheduling (schedule identity idempotency under concurrent or repeated triggers)
5. LinkedIn API publication (once-only publish under concurrent or repeated publish-due / queue paths)
6. Abandoned processing-claim recovery (stale detect + reclaim as a story deliverable with operator-visible outcomes)

**US-035 surfaces (this change):**

7. Restart / crash-recovery validation for mid-flight Flow A interruption (claim, image, blog handoff, schedule, and LinkedIn publish surfaces as needed for restart-safety evidence)

This capability MUST preserve US-033 and US-034 protections and MUST NOT redefine them as new deliverables of US-035.

n8n orchestration single-flight MAY remain as complementary defense-in-depth. Worker HTTP paths MUST remain safe when overlapping calls occur after restart (ADR-0001).

#### Scenario: US-033 surfaces remain in force

- **WHEN** concurrent or repeated worker calls contend on claim, image generation, or blog publish for the same campaign or publish identity
- **THEN** the worker continues to apply US-033 duplicate-prevention rules for those surfaces and returns operator-visible outcomes

#### Scenario: US-034 surfaces remain in force

- **WHEN** concurrent or repeated worker calls contend on scheduling, LinkedIn API publish, or abandoned-claim reclaim for the same campaign or distribution / publication identity
- **THEN** the worker continues to apply US-034 duplicate-prevention and reclaim rules for those surfaces and returns operator-visible outcomes

#### Scenario: US-035 restart validation is in scope for this change

- **WHEN** a worker or process interruption leaves mid-flight Flow A work and execution later resumes via reclaim, calendar/execute, or incomplete-campaign recovery
- **THEN** the worker applies US-035 restart-safety rules so duplicate artifacts and external publications are not created when durable evidence already exists

## ADDED Requirements

### Requirement: Mid-flight restart does not duplicate Flow A artifacts or publications

When a worker or process interruption occurs mid-Flow A, subsequent re-entry after restart MUST NOT create duplicate artifacts or external publications for identities that already have durable evidence.

Re-entry paths in scope include:

- duplicate claim / calendar execute while a non-stale `processing` claim remains;
- stale detect + reclaim followed by stage resume;
- incomplete-campaign recovery resume / allowlisted repair after interruption.

Across claim, image generation, blog handoff, distribution scheduling, and LinkedIn publish surfaces, resume MUST reuse existing US-033 and US-034 idempotency and once-only contracts (skip/reuse image, `already_published` / `blog_publish_target_exists`, schedule matching proof / `linkedin_schedule_metadata_mismatch`, `linkedin_publish_already_published` / URN evidence).

This requirement MUST NOT introduce a parallel queue ontology or new execution states. Stale TTL reclaim remains the clock-based recovery path for abandoned `processing` claims (US-034 vocabulary).

This requirement MUST NOT claim Git remote push or live-site HTTP confirmation as completed by US-035.

#### Scenario: Pre-TTL post-restart claim remains blocked

- **WHEN** a campaign is left with non-stale `execution_state=processing` after mid-flight interruption and a claim or execute is requested before the stale threshold
- **THEN** the attempt fails closed with `flow_a_execution_already_claimed` (or the canonical BL-012 active non-stale claim reason) and `recovery_classification=manual_intervention_required`, and no second publish/image/schedule/LinkedIn pipeline starts for that attempt

#### Scenario: Post-TTL reclaim resumes without duplicating completed stages

- **WHEN** a mid-flight interrupted campaign becomes stale, is reclaimed with `reclaimed_from_stale`, and resume runs against existing durable stage evidence
- **THEN** reclaim/resume does not create a second campaign document, second reusable image generation when a reusable PNG exists, second blog publish apply for matching identity, second schedule set for matching proof, or second LinkedIn API publication when URN evidence exists

#### Scenario: Concurrent re-trigger immediately after restart loses to non-stale claim

- **WHEN** a calendar or HTTP re-trigger overlaps a still non-stale post-restart `processing` claim for the same campaign
- **THEN** the overlapping attempt is rejected as already-claimed / manual intervention required and does not leave a second active claim

### Requirement: Restart interruption scenarios cover claim, image, blog, schedule, and LinkedIn surfaces

US-035 validation MUST cover mid-flight interruption scenarios for:

1. Claim-only (claimed, interrupted before publish)
2. Image generation (interrupted during or after ComfyUI / before complete handoff)
3. Blog handoff (interrupted during or after checkout apply evidence)
4. Distribution scheduling (interrupted during or after first schedule apply)
5. LinkedIn publish (interrupted with durable URN evidence, or mid-API without durable URN)

Image and blog paths MUST continue to fail closed or short-circuit via existing US-033 outcomes. Schedule paths MUST continue to use US-034 schedule CAS / matching-proof / mismatch outcomes. LinkedIn paths with durable URN MUST short-circuit as already-published; mid-API interruption without durable URN MUST remain under LinkedIn publication recovery (BL-008) uncertain / confirmation contracts and MUST NOT auto-republish via Flow A reclaim alone.

#### Scenario: Claim-only interruption then reclaim does not invent publish success

- **WHEN** execution is interrupted after claim and before blog publish evidence exists, then stale reclaim and resume run
- **THEN** resume continues from evidence-derived unfinished stages without inventing `already_published`, schedule success, or LinkedIn URN evidence

#### Scenario: Image interruption reuses existing PNG after reclaim

- **WHEN** a reusable active-folder or public PNG exists after an image-stage interruption and reclaim/resume reaches image generation
- **THEN** ComfyUI is not invoked again solely to regenerate that asset, and a readable public asset is not overwritten solely due to restart resume

#### Scenario: Blog interruption preserves handoff idempotency after reclaim

- **WHEN** blog handoff evidence already satisfies matching publish identity after interruption and publish is re-entered
- **THEN** the outcome is completed `already_published` (or equivalent) without rewriting public targets; when targets exist without matching proof, publish fails closed with `blog_publish_target_exists` (or equivalent)

#### Scenario: Schedule interruption leaves at most one durable schedule set

- **WHEN** schedule apply is interrupted mid-flight and reclaim/resume re-enters scheduling for the same identity
- **THEN** at most one durable matching schedule set remains and mismatch inputs fail closed with `linkedin_schedule_metadata_mismatch`

#### Scenario: LinkedIn mid-flight without URN stays BL-008 uncertain

- **WHEN** LinkedIn publish is interrupted after a suspected API attempt without durable `linkedin_post_urn` evidence
- **THEN** Flow A reclaim/resume does not auto-call LinkedIn publish again as a success path, and uncertain / confirmation handling remains under LinkedIn publication recovery contracts

### Requirement: Operator-visible restart outcomes and fail-closed blocks

US-035 restart blocked, reclaim, resume, and fail-closed outcomes MUST be operator-visible through structured, secret-safe result fields: stable status/error codes, already-claimed / active non-stale claim reasons, `reclaimed_from_stale` when reclaim succeeds, stage idempotent completes, and `recovery_classification` when claim/stale/recovery vocabulary requires it.

Responses and logs for these paths MUST NOT include secrets, tokens, absolute editorial/public base paths, Markdown/draft bodies, or raw provider payloads.

Auth and validation failures on existing authenticated routes remain fail-closed with appropriate HTTP status codes.

#### Scenario: Post-restart already-claimed block is understandable

- **WHEN** a second non-stale claim or resume attempt is rejected after mid-flight interruption
- **THEN** the result includes a stable already-claimed / active non-stale claim code and `recovery_classification=manual_intervention_required` without secret or content-body leakage

#### Scenario: Reclaim after restart interruption is understandable

- **WHEN** a stale claim created by mid-flight interruption is successfully reclaimed
- **THEN** the result indicates completed reclaim with `reclaimed_from_stale` (or equivalent) and the new processing attempt identity without secret leakage

#### Scenario: Ambiguous blog evidence after interruption fails closed visibly

- **WHEN** resume or publish encounters public targets or partial handoff evidence that does not prove matching publish identity
- **THEN** the operation fails closed with a stable code (`blog_publish_target_exists`, `flow_a_recovery_evidence_ambiguous`, or the canonical equivalent) and does not invent success

### Requirement: Completed work is preserved under US-035 restart paths

US-035 enforcement and validation MUST NOT duplicate or unintentionally change already-completed durable claim / image / blog / schedule / LinkedIn evidence, including US-033 and US-034 protections.

Idempotent and blocked restart paths MUST preserve winner/completed artifacts and MUST NOT clear confirmed `already_published` identity fields, schedule anchors, or LinkedIn URN / `published_at` solely to acknowledge a post-restart loser or reclaim.

Incomplete-campaign recovery (BL-012) and LinkedIn publication recovery (BL-008) contracts MUST remain intact unless a narrow shared dependency on claim rejection, reclaim, or once-only evidence is exercised without changing their recovery semantics.

Worker startup / process restart MUST NOT auto-clear a non-stale `execution_state=processing` claim.

#### Scenario: Completed LinkedIn URN survives restart reclaim

- **WHEN** a variant already has durable `linkedin_post_urn` / `published_at` and reclaim/resume runs after worker interruption
- **THEN** the path short-circuits or fails closed without clearing or inventing alternate publication identity evidence

#### Scenario: Completed schedule evidence survives restart reclaim

- **WHEN** a campaign already has matching `distribution_scheduled` schedule proof and scheduling is re-entered after interruption
- **THEN** stored `scheduled_at_utc` values and schedule idempotency proof remain unchanged

#### Scenario: Non-stale processing claim is not auto-cleared on restart

- **WHEN** the worker process restarts while a campaign still has a non-stale `execution_state=processing` claim
- **THEN** the claim remains `processing` until stale detection, allowlisted stale claim repair, or normal release — and is not cleared solely by process start
