## MODIFIED Requirements

### Requirement: US-033 scope boundary for concurrency and duplicate-execution protection

The worker SHALL enforce concurrency and duplicate-execution protection for Flow A under simultaneous or repeated triggers. This capability covers:

**US-033 surfaces (already delivered; MUST remain intact):**

1. Post processing (queue acceptance identity + execution claim)
2. Image generation (ComfyUI invoke / skip / reuse)
3. Blog publication (handoff / checkout publish apply idempotency)

**US-034 surfaces (this change):**

4. Distribution scheduling (schedule identity idempotency under concurrent or repeated triggers)
5. LinkedIn API publication (once-only publish under concurrent or repeated publish-due / queue paths)
6. Abandoned processing-claim recovery (stale detect + reclaim as a story deliverable with operator-visible outcomes)

This capability MUST NOT, in this change, claim to satisfy US-035 (restart validation).

n8n orchestration single-flight MAY remain as complementary defense-in-depth. Worker HTTP paths MUST remain safe when overlapping calls occur (ADR-0001).

#### Scenario: US-033 surfaces remain in force

- **WHEN** concurrent or repeated worker calls contend on claim, image generation, or blog publish for the same campaign or publish identity
- **THEN** the worker continues to apply US-033 duplicate-prevention rules for those surfaces and returns operator-visible outcomes

#### Scenario: US-034 surfaces are in scope for this change

- **WHEN** concurrent or repeated worker calls contend on scheduling, LinkedIn API publish, or abandoned-claim reclaim for the same campaign or distribution / publication identity
- **THEN** the worker applies US-034 duplicate-prevention and reclaim rules for those surfaces and returns operator-visible outcomes

#### Scenario: Restart validation remains out of US-034 deliverables

- **WHEN** this capability’s US-034 requirements are evaluated
- **THEN** they do not redefine restart / crash-recovery validation as an in-scope deliverable of this change

## ADDED Requirements

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
