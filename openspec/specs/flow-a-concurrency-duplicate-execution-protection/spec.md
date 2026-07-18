# flow-a-concurrency-duplicate-execution-protection

## Purpose

Worker-side concurrency and duplicate-execution protection for Flow A under simultaneous or repeated triggers. US-033 covers post processing, image generation, and blog publication (checkout handoff apply). US-034 covers distribution scheduling, LinkedIn API once-only publish under contention, and abandoned-claim stale detect + reclaim. US-035 (restart validation) MAY extend this capability later.

## Requirements
### Requirement: US-033 scope boundary for concurrency and duplicate-execution protection

The worker SHALL enforce concurrency and duplicate-execution protection for Flow A under simultaneous or repeated triggers. This capability covers:

**US-033 surfaces (already delivered; MUST remain intact):**

1. Post processing (queue acceptance identity + execution claim)
2. Image generation (ComfyUI invoke / skip / reuse)
3. Blog publication (handoff / checkout publish apply idempotency)

**US-034 surfaces (delivered):**

4. Distribution scheduling (schedule identity idempotency under concurrent or repeated triggers)
5. LinkedIn API publication (once-only publish under concurrent or repeated publish-due / queue paths)
6. Abandoned processing-claim recovery (stale detect + reclaim as a story deliverable with operator-visible outcomes)

This capability MUST NOT claim to satisfy US-035 (restart validation) until that story is delivered.

n8n orchestration single-flight MAY remain as complementary defense-in-depth. Worker HTTP paths MUST remain safe when overlapping calls occur (ADR-0001).

#### Scenario: US-033 surfaces remain in force

- **WHEN** concurrent or repeated worker calls contend on claim, image generation, or blog publish for the same campaign or publish identity
- **THEN** the worker continues to apply US-033 duplicate-prevention rules for those surfaces and returns operator-visible outcomes

#### Scenario: US-034 surfaces are in scope

- **WHEN** concurrent or repeated worker calls contend on scheduling, LinkedIn API publish, or abandoned-claim reclaim for the same campaign or distribution / publication identity
- **THEN** the worker applies US-034 duplicate-prevention and reclaim rules for those surfaces and returns operator-visible outcomes

#### Scenario: Restart validation remains out of US-034 deliverables

- **WHEN** this capability’s US-034 requirements are evaluated
- **THEN** they do not redefine restart / crash-recovery validation as an in-scope deliverable of US-034

### Requirement: Concurrent post processing is single-claim and single-queue identity

For a given Flow A campaign identity, the worker MUST ensure that concurrent or repeated post-processing attempts cannot create two active non-stale `execution_state=processing` claims and cannot create a duplicate queued source or second campaign document for the same acceptance identity.

Execution claim transitions that move `execution_state` to `processing` MUST use an atomic compare-and-swap (or equivalent) against the on-disk campaign metadata so that two overlapping claim attempts observing `idle` (or eligible `stale`) cannot both persist `processing`.

When a second claim loses contention against a non-stale active claim, the worker MUST fail closed with `flow_a_execution_already_claimed`, `already_claimed=true` semantics, and `recovery_classification=manual_intervention_required`, without starting a second publish/image pipeline for that claim attempt.

Queue acceptance MUST continue to treat same-identity already-queued sources as idempotent (`skipped_already_queued` or equivalent completed accept) and MUST NOT create a duplicate campaign JSON document.

#### Scenario: Overlapping claims yield one winner and one already-claimed loser

- **WHEN** two concurrent `claim_flow_a_execution` calls race for the same queued campaign that is not stale
- **THEN** exactly one claim persists `execution_state=processing` with a single new `execution_attempt_id`, and the other returns failed with `flow_a_execution_already_claimed` and does not leave a second active claim

#### Scenario: Sequential duplicate claim still rejected

- **WHEN** a campaign already has a non-stale `execution_state=processing` claim and a later claim is requested
- **THEN** the later claim fails with `flow_a_execution_already_claimed` and `recovery_classification=manual_intervention_required`

#### Scenario: Same-identity queue acceptance does not duplicate campaign

- **WHEN** queue acceptance is repeated for a source already queued under the same campaign identity and matching `source_content_sha256`
- **THEN** acceptance returns idempotent already-queued/completed outcome without creating a second campaign document or duplicate queued Markdown body

### Requirement: Concurrent image generation does not duplicate ComfyUI work

When concurrent or repeated publish/image paths run for the same source post, the worker MUST NOT invoke ComfyUI when a reusable active-folder sibling PNG or readable public `assets/images/<public_slug>.png` already satisfies the image prerequisite.

Immediately before a ComfyUI provider call, the worker MUST re-check those reusable asset locations. If a reusable asset is present, generation MUST be skipped or reused per `blog-image-public-asset-handoff` rules with a durable operator-visible skip/reuse outcome, and an existing readable public asset MUST NOT be overwritten solely due to a concurrent generation attempt.

Calendar/connector Flow A executions that lose claim contention MUST NOT proceed to ComfyUI for that losing attempt.

#### Scenario: Existing public asset skips ComfyUI under repeated publish

- **WHEN** `publish_blog_post` is invoked again for a source whose public image asset already exists and is readable
- **THEN** ComfyUI is not called and image generation records a skipped/reuse outcome

#### Scenario: Claim loser does not generate an image

- **WHEN** a concurrent connector execution fails claim with `flow_a_execution_already_claimed`
- **THEN** that execution does not call ComfyUI and does not write a second companion PNG for the campaign

#### Scenario: Pre-ComfyUI re-check prevents overwrite of newly appeared asset

- **WHEN** a reusable public or active-folder PNG appears after an earlier existence check but before the ComfyUI provider call
- **THEN** the worker skips ComfyUI and does not overwrite the reusable public asset

### Requirement: Concurrent blog publication does not duplicate public artifacts

Concurrent or repeated blog publication for the same Flow A publish identity MUST NOT create duplicate `_posts/` or `assets/images/` artifacts or overwrite proven published targets.

When campaign metadata proves matching blog publish identity (`already_published` short-circuit conditions in `worker-blog-publishing-endpoint`), the worker MUST return completed `already_published` without validation, image, or public-repo mutating side effects.

When public targets already exist without matching identity proof, the worker MUST fail closed without overwrite (`blog_publish_target_exists` or the canonical equivalent).

Under concurrent first-time publish attempts for the same identity, at most one attempt MAY successfully apply public artifacts; other attempts MUST short-circuit as `already_published` or fail closed without corrupting the winner’s artifacts or inventing a second campaign.

This requirement covers worker handoff / checkout publish apply safety. It MUST NOT claim Git remote push or live-site HTTP confirmation as completed by US-033.

#### Scenario: Matching identity returns already_published without side effects

- **WHEN** publish is requested for a campaign that already satisfies `already_published` identity evidence
- **THEN** the response is completed with `blog_publish.status=already_published` and no public files are rewritten

#### Scenario: Unproven target collision fails closed

- **WHEN** public blog targets exist but campaign metadata does not prove the same blog publish idempotency key
- **THEN** publish fails with `blog_publish_target_exists` (or equivalent) and does not overwrite targets

#### Scenario: Concurrent first publish leaves a single artifact set

- **WHEN** two overlapping publish attempts race for the same previously unpublished Flow A identity
- **THEN** at most one successful public apply occurs and the other attempt ends as `already_published` or a fail-closed conflict without duplicate distinct publish artifacts for that identity

### Requirement: Operator-visible concurrency outcomes and fail-closed blocks

US-033 contention, skip, and idempotent-complete outcomes MUST be operator-visible through structured, secret-safe result fields: stable status/error codes, claim `already_claimed` when applicable, `recovery_classification` when a non-stale claim blocks execution, and image skip/reuse reasons when generation is skipped.

Responses and logs for these paths MUST NOT include secrets, tokens, absolute editorial/public base paths, Markdown/draft bodies, or raw provider payloads.

Auth and validation failures on existing authenticated routes remain fail-closed with appropriate HTTP status codes.

#### Scenario: Already-claimed block is understandable

- **WHEN** a second non-stale claim attempt is rejected
- **THEN** the result includes `flow_a_execution_already_claimed` and `recovery_classification=manual_intervention_required` without secret or content-body leakage

#### Scenario: Already-published outcome is understandable

- **WHEN** an idempotent blog republish short-circuit applies
- **THEN** the result includes `blog_publish.status=already_published` (or equivalent completed status) that operators can distinguish from a fresh publish apply

### Requirement: Completed work is preserved under US-033 paths

US-033 enforcement MUST NOT duplicate or unintentionally change already-completed durable blog publish evidence or reusable image assets. Idempotent and contention-loser paths MUST preserve winner/completed artifacts and MUST NOT rewrite confirmed `already_published` identity fields solely to acknowledge a concurrent loser.

Incomplete-campaign recovery (BL-012) and LinkedIn publication recovery (BL-008) contracts MUST remain intact unless a narrow shared dependency on claim rejection is exercised without changing their recovery semantics.

#### Scenario: Completed publish evidence is not rewritten by loser

- **WHEN** a campaign already has durable `already_published` or published blog evidence and a concurrent/repeated publish attempt runs
- **THEN** the attempt short-circuits or fails closed without clearing or inventing alternate publish identity evidence

#### Scenario: Incomplete-campaign recovery claim rejection unchanged

- **WHEN** incomplete-campaign recovery resume encounters a non-stale `processing` claim
- **THEN** resume remains rejected consistently with duplicate-claim protection and no second execution claim is created

### Requirement: Concurrent distribution scheduling does not duplicate schedule identity

For a given Flow A campaign / distribution schedule identity, concurrent or repeated schedule triggers MUST NOT create a second schedule set, duplicate `distribution_scheduled` `state_history` entries, or conflicting anchors for matching schedule idempotency proof.

First-time schedule apply that transitions `derivatives_generated` → `distribution_scheduled` MUST use an atomic compare-and-swap (or equivalent) against on-disk campaign metadata so two overlapping schedule attempts cannot both persist a successful first-time schedule write.

When campaign state is already `distribution_scheduled` and stored schedule idempotency proof matches, the operation MUST return completed without rewriting `scheduled_at_utc` values or appending duplicate history.

When stored scheduling metadata does not match the expected proof, the operation MUST fail closed with `linkedin_schedule_metadata_mismatch` (or the canonical equivalent).

#### Scenario: Matching schedule proof remains idempotent under repeat

- **WHEN** distribution scheduling is invoked again for a `distribution_scheduled` campaign with matching schedule idempotency proof
- **THEN** the operation returns `status` `completed` without duplicate `state_history` and without changing `scheduled_at_utc` values

#### Scenario: Overlapping first-time schedule yields one durable schedule

- **WHEN** two concurrent schedule calls race for the same previously unscheduled `derivatives_generated` campaign with the same schedule identity inputs
- **THEN** at most one successful first-time schedule apply persists and the other attempt ends as completed idempotent or fail-closed without a second distinct schedule set for that identity

#### Scenario: Schedule mismatch fails closed

- **WHEN** scheduling is requested for a `distribution_scheduled` campaign with inputs that disagree with stored schedule proof
- **THEN** the operation fails with `linkedin_schedule_metadata_mismatch` and does not rewrite stored slots

### Requirement: Concurrent LinkedIn publication is once-only per variant evidence

Concurrent or repeated LinkedIn publish-due / queue paths for the same variant publication identity MUST NOT create a second LinkedIn API publication when durable publication evidence already exists or is won by a peer attempt.

When a variant is already `published` with a stored non-empty `linkedin_post_urn`, the worker MUST NOT call LinkedIn publication API again and MUST return the existing already-published outcome (`linkedin_publish_already_published` or equivalent) while preserving `linkedin_post_urn` and `published_at`.

Immediately before a real LinkedIn API publish call, the worker MUST re-check on-disk variant publication evidence. If peer evidence already shows published + URN, the worker MUST short-circuit as already-published without calling LinkedIn.

Successful real publish evidence persistence MUST use atomic compare-and-swap (or equivalent) so overlapping first-publish attempts cannot both leave conflicting durable publication identities without fail-closed handling. When a peer’s URN evidence is already durable, the worker MUST preserve that evidence and MUST NOT clear it to acknowledge a loser.

This requirement reuses LinkedIn publication idempotency and URN evidence contracts. It MUST NOT redefine BL-008 uncertain-outcome / recovery-confirmation taxonomy.

Enablement, OAuth, and dry-run guards remain fail-closed without incorrect `failed` transitions.

#### Scenario: Already-published repeat does not call LinkedIn

- **WHEN** publish-due runs for a variant with `publish_state` `published` and existing `linkedin_post_urn`
- **THEN** no LinkedIn API call occurs, the outcome indicates already published, and stored URN / `published_at` are unchanged

#### Scenario: Pre-API evidence re-check skips duplicate publish

- **WHEN** a concurrent peer has already persisted published URN evidence after an earlier check but before this attempt’s LinkedIn API call
- **THEN** this attempt does not call LinkedIn and returns already-published (or equivalent) with peer URN preserved

#### Scenario: Concurrent first publish leaves one URN identity

- **WHEN** two overlapping real publish-due attempts race for the same previously unpublished queued variant
- **THEN** at most one LinkedIn publication identity is durably retained for that variant and loser/conflict handling does not invent a second stored URN or clear the winner’s evidence

### Requirement: Abandoned processing claims are recoverable via stale detect and reclaim

The worker MUST recover abandoned processing claims as a US-034 deliverable using existing operational-queue vocabulary:

1. Detect stale when `execution_state=processing` and current UTC time is greater than or equal to `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`.
2. Stale detection MUST set `execution_state=stale` and `recovery_classification=retryable` without moving editorial files.
3. Reclaim MUST transition eligible `stale` (or detect-then-claim) campaigns to `execution_state=processing` with a new `execution_attempt_id` and operator-visible `reclaimed_from_stale` (or equivalent) semantics via existing claim helpers.
4. Non-stale active `processing` claims MUST continue to reject duplicate claim with `flow_a_execution_already_claimed` and `recovery_classification=manual_intervention_required`.

Reclaim MUST resume using existing campaign evidence and completed-stage markers and MUST NOT duplicate schedule slots or LinkedIn publications when durable evidence already exists.

#### Scenario: Stale detect marks abandoned processing claim

- **WHEN** a queued campaign has `execution_state=processing` and `last_progress_at` plus configured stale seconds is in the past
- **THEN** stale detection completes with `execution_state=stale` and `recovery_classification=retryable` without moving files

#### Scenario: Reclaim from stale yields new processing attempt

- **WHEN** `claim_flow_a_execution` runs for a campaign in `execution_state=stale`
- **THEN** claim completes with `execution_state=processing`, a new `execution_attempt_id`, and `reclaimed_from_stale` true (or equivalent operator-visible indicator)

#### Scenario: Non-stale claim remains blocked

- **WHEN** reclaim or claim is requested while `execution_state=processing` and the claim is not stale
- **THEN** the operation fails with `flow_a_execution_already_claimed` and `recovery_classification=manual_intervention_required`

### Requirement: Operator-visible US-034 concurrency and reclaim outcomes

US-034 schedule contention, LinkedIn once-only, stale detect, and reclaim outcomes MUST be operator-visible through structured, secret-safe result fields: stable status/error codes, already-published warnings when applicable, `reclaimed_from_stale` when reclaim succeeds, and `recovery_classification` when claim/stale vocabulary requires it.

Responses and logs for these paths MUST NOT include secrets, tokens, absolute editorial/public base paths, Markdown/draft bodies, or raw provider payloads.

#### Scenario: Schedule mismatch is understandable

- **WHEN** a schedule request fails closed on identity mismatch
- **THEN** the result includes `linkedin_schedule_metadata_mismatch` without secret or content-body leakage

#### Scenario: Already-published LinkedIn outcome is understandable

- **WHEN** an idempotent LinkedIn republish short-circuit applies
- **THEN** the result includes `linkedin_publish_already_published` (or equivalent) that operators can distinguish from a fresh publish

#### Scenario: Reclaim outcome is understandable

- **WHEN** a stale claim is successfully reclaimed
- **THEN** the result indicates completed reclaim with `reclaimed_from_stale` (or equivalent) and the new processing attempt identity without secret leakage

### Requirement: Completed work is preserved under US-034 paths

US-034 enforcement MUST NOT duplicate or unintentionally change already-completed durable schedule evidence, LinkedIn URN / `published_at` evidence, or US-033 claim / image / blog protections.

Idempotent and contention-loser paths MUST preserve winner/completed artifacts and MUST NOT rewrite confirmed schedule anchors or LinkedIn publication identity solely to acknowledge a concurrent loser.

Incomplete-campaign recovery (BL-012) and LinkedIn publication recovery (BL-008) contracts MUST remain intact unless a narrow shared dependency on claim rejection or once-only publish evidence is exercised without changing their recovery semantics.

#### Scenario: Completed LinkedIn URN is not rewritten by loser

- **WHEN** a variant already has durable `linkedin_post_urn` / `published_at` and a concurrent or repeated publish attempt runs
- **THEN** the attempt short-circuits or fails closed without clearing or inventing alternate publication identity evidence

#### Scenario: Completed schedule evidence is not rewritten by matching rerun

- **WHEN** a campaign already has matching `distribution_scheduled` schedule proof and scheduling is repeated
- **THEN** stored `scheduled_at_utc` values and schedule idempotency proof remain unchanged
