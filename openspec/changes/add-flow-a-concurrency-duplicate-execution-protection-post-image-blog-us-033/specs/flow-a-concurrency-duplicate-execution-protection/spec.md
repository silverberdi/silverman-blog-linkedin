## ADDED Requirements

### Requirement: US-033 scope boundary for concurrency and duplicate-execution protection

The worker SHALL enforce concurrency and duplicate-execution protection for Flow A under simultaneous or repeated triggers for the US-033 surface only:

1. Post processing (queue acceptance identity + execution claim)
2. Image generation (ComfyUI invoke / skip / reuse)
3. Blog publication (handoff / checkout publish apply idempotency)

This capability MUST NOT, in this change, claim to satisfy US-034 (duplicate scheduling, duplicate LinkedIn API publication, abandoned-claim reclaim as a deliverable) or US-035 (restart validation).

n8n orchestration single-flight MAY remain as complementary defense-in-depth. Worker HTTP paths MUST remain safe when overlapping calls occur (ADR-0001).

#### Scenario: US-033 surfaces are in scope

- **WHEN** concurrent or repeated worker calls contend on claim, image generation, or blog publish for the same campaign or publish identity
- **THEN** the worker applies US-033 duplicate-prevention rules for those surfaces and returns operator-visible outcomes

#### Scenario: Scheduling and LinkedIn publish remain out of US-033 deliverables

- **WHEN** this capability’s US-033 requirements are evaluated
- **THEN** they do not redefine schedule-slot idempotency, LinkedIn API once-only publish, or abandoned-claim reclaim policy as in-scope deliverables of this change

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
