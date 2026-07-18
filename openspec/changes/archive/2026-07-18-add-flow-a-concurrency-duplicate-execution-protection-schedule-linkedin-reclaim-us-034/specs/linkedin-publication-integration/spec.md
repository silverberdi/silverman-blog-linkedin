## ADDED Requirements

### Requirement: Concurrent LinkedIn publish-due is once-only under contention

Real LinkedIn publish-due paths MUST remain once-only for a given variant publication identity under concurrent or repeated triggers, reusing existing already-published idempotency and URN evidence rules.

Before invoking the LinkedIn publication API for a `queued` variant in a real (`dry_run=false`) publish attempt, the worker MUST re-read on-disk campaign/variant publication evidence. If the variant is already `published` with a non-empty `linkedin_post_urn`, the worker MUST NOT call LinkedIn and MUST return the existing already-published outcome (`linkedin_publish_already_published` warning or equivalent) while preserving `linkedin_post_urn` and `published_at`.

Persisting a successful real publish transition to `published` with URN evidence MUST use an atomic compare-and-swap (or equivalent) against campaign metadata so two overlapping first-publish attempts cannot both commit conflicting durable publication identities without fail-closed handling.

When a peer has already committed durable URN evidence, the worker MUST preserve that evidence, MUST NOT clear it, and MUST NOT perform an additional LinkedIn API call solely to acknowledge the losing attempt.

This requirement MUST NOT redefine BL-008 uncertain-outcome classification, recovery confirmation, or retry-limit contracts. Enablement and OAuth blocked conditions remain fail-closed without incorrectly marking `publish_state=failed`.

#### Scenario: Pre-API re-check prevents second LinkedIn call

- **WHEN** a real publish-due attempt is about to call LinkedIn but on-disk evidence already shows the variant `published` with `linkedin_post_urn`
- **THEN** no LinkedIn API call occurs and the result indicates already published with preserved URN and `published_at`

#### Scenario: Overlapping first publish retains a single URN identity

- **WHEN** two concurrent real publish-due attempts race for the same previously unpublished `queued` variant
- **THEN** at most one durable `linkedin_post_urn` identity is retained for that variant and any loser/conflict path does not invent a second stored URN or clear the winner’s evidence

#### Scenario: publish_now does not bypass concurrent already-published protection

- **WHEN** publish-due runs with `dry_run=false` and `publish_now=true` for a variant that already has durable published URN evidence
- **THEN** no LinkedIn API call occurs and stored `linkedin_post_urn` / `published_at` are preserved
