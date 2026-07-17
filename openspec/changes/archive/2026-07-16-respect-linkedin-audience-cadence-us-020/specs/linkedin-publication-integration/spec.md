# Delta: linkedin-publication-integration (respect-linkedin-audience-cadence-us-020)

US-020 (BL-007 story 3): respect audience cadence and sequence at scheduled publication execution time. This delta ADDS one requirement (per-campaign publish-time sequence and cadence guard) and MODIFIES five existing requirements additively (full canonical blocks copied). The guard is enforced **at publish time** for every publish-due evaluation over `queued` variants — plain publish-due (`auto_queue_pending` `false`), the combined flow, targeted requests, and the bounded cross-campaign scan — and additionally as an auto-queue pre-filter for `pending` variants. It does not change the `publish_state` state machine, renames no fields, retypes no fields, adds no endpoints and no request flags, and does not modify `POST /queue-linkedin-publication` or US-017 supervision mechanics/endpoints. `linkedin-distribution-scheduling-model` is not modified: the canonical audience sequence and the 3-day stagger remain defined there; this delta only consumes them at execution time. Retry, recovery, recoverable/non-recoverable classification, token renewal, timeout duplicate mitigation, and attempt history after manual re-queue remain **BL-008** and are explicitly out of scope.

## ADDED Requirements

### Requirement: Per-campaign publish-time sequence and cadence guard

The worker MUST enforce a per-campaign guard with two rules — audience **sequence** and real publication **cadence** — every time a `queued` variant is evaluated for publication by the publish-due service. The guard MUST apply identically in the plain publish-due path (`auto_queue_pending` `false` or omitted), in the combined flow (`auto_queue_pending` `true`), for targeted requests (`campaign_id`/`variant` provided), and for variants reached through the bounded cross-campaign scan. Variants queued manually via `POST /queue-linkedin-publication` are governed by the guard at publish time exactly like auto-queued variants; that endpoint's queue contract is unchanged, but manual queueing MUST NOT allow publication that the guard forbids.

**Sequence ordering source.** The sequence MUST be the canonical audience sequence used by the `flow_a_staggered` strategy (`executive-recruiter`, then `engineering-leadership`, then `technical-architect`, then `short-provocative`), restricted to the campaign's variant set. Variants outside the canonical sequence MUST be ordered deterministically after canonical variants by ascending `scheduled_at_utc`, then variant id.

**Sequence rule.** A variant V of campaign C MUST NOT be published while any variant E earlier than V in the sequence within C is **awaiting publication**, meaning:

- E has `publish_state` `pending` — including a `pending` variant deferred via US-017 (`operator_supervision.last_action` `defer`): a deferred earlier variant blocks later variants until it is published, fails, or is cancelled; blocking is execution-time only and MUST NOT mutate any sibling's `scheduled_at_utc` or supervision metadata (US-017 mechanics unchanged), or
- E has `publish_state` `queued` and not published

Earlier variants in the following conditions release the sequence (they do not block V):

- `published` — the sequence advances past E, and E's `published_at` participates in the cadence rule below
- `failed` — never retried automatically (BL-008 boundary); stored US-019 failure evidence MUST remain intact; manual re-queue via `POST /queue-linkedin-publication` remains the only retry path, and a re-queued earlier variant is again `queued` and therefore blocks its followers until resolved
- `cancelled` — the operator removed the variant from the plan

This rule does not guarantee strict canonical publication order in every history: a `failed` earlier variant releases the chain, and its later manual re-queue can produce an inversion relative to already-published followers. The guarantee is narrower and normative: **a later variant is never published while an earlier variant is still awaiting publication.**

**Cadence rule.** Within one campaign, successful publications MUST be separated by a minimum real interval of 3 days (72 hours), regardless of invocation frequency, accumulated schedule delays, or `publish_now`. A variant of campaign C MUST NOT be published unless, for every variant of C with `publish_state` `published`, `published_at + 72h <= now_utc`. The campaign's last successful publication MUST be determined from stored `published_at` evidence (US-019). A publication completed earlier within the same request MUST count: after one successful publish for campaign C, no further variant of C may be published in that request. A campaign with no `published` variants has no cadence constraint. The cadence rule is strictly per campaign: in the cross-campaign scan each campaign is evaluated independently, one campaign's publications never gate another campaign's, and no global cross-campaign cadence is introduced.

**Evidence fail-closed rule.** If any `published` variant of campaign C has a missing, empty, or unparsable `published_at`, the cadence interval cannot be computed and the guard MUST fail closed: no variant of C may be published, and each blocked candidate MUST be reported with stable reason `linkedin_publish_blocked_evidence_invalid` (distinct from the sequence and cadence reasons). The blocked variants MUST NOT change `publish_state`, no LinkedIn or OAuth call may occur for them, and the condition MUST NOT by itself fail the overall operation or the cross-campaign scan — other campaigns are still evaluated. Repair of the evidence is a manual metadata operation outside this capability.

**Stable reasons and precedence.** Publish-time guard blocks MUST be reported per variant with these stable reasons:

- `linkedin_publish_blocked_sequence` — blocked by the sequence rule
- `linkedin_publish_blocked_cadence` — blocked by the 72-hour cadence rule
- `linkedin_publish_blocked_evidence_invalid` — blocked because a `published` sibling lacks valid `published_at`

Existing publish-phase semantics MUST be preserved: already-published idempotent handling, `linkedin_publish_variant_not_queued`, and the `publish_after_utc` timing skip (`linkedin_publish_variant_not_due`) are evaluated exactly as before this change, before the guard. The guard is then evaluated in the order sequence → evidence → cadence. Guard-blocked variants MUST NOT change `publish_state`, MUST NOT trigger any LinkedIn or OAuth call, and MUST NOT by themselves fail the overall operation.

**`publish_now` scope.** `publish_now` bypasses only the ordinary timing gates (`scheduled_at_utc` due gate at auto-queue and `publish_after_utc` at publish), exactly as today. `publish_now` MUST NOT bypass the sequence rule, the cadence rule, the evidence fail-closed rule, supervision exclusions, or a deferred time.

**Auto-queue pre-filter.** When `auto_queue_pending` is `true`, the auto-queue phase MUST NOT queue a due `pending` variant whose earlier variant in the sequence is awaiting publication (as defined above), reporting it with stable reason `linkedin_publish_auto_queue_skipped_sequence` (see the auto-queue eligibility requirement). This pre-filter is visibility and churn reduction only; the publish-time guard remains the normative enforcement point and MUST hold even if a variant was queued despite it (for example manually).

**Dry-run.** Under `dry_run` `true`, guard evaluation MUST be reported as planned outcomes (including planned blocks with the stable reasons above) with zero metadata writes and zero LinkedIn or OAuth calls.

No new endpoints, request fields, environment variables, or `publish_state` values are introduced by this requirement.

#### Scenario: Later queued variant not published while earlier variant remains queued

- **WHEN** publish-due runs (with or without `auto_queue_pending`) for a campaign whose `executive-recruiter` variant is `queued` and unpublished and whose `engineering-leadership` variant is `queued` and past its `publish_after_utc`
- **THEN** `engineering-leadership` is not published, is reported with `linkedin_publish_blocked_sequence`, remains `queued`, and no LinkedIn API call occurs for it

#### Scenario: Plain publish-due enforces the guard

- **WHEN** publish-due runs with `auto_queue_pending` false over a campaign with two `queued` variants both past `publish_after_utc`
- **THEN** at most the earlier canonical variant is published and the later is blocked with a stable guard reason without a `publish_state` change

#### Scenario: publish_now bypasses neither sequence nor cadence

- **WHEN** publish-due runs with `publish_now` true for a `queued` variant that is sequence-blocked or whose campaign published another variant less than 72 hours ago
- **THEN** the variant is not published and is reported with `linkedin_publish_blocked_sequence` or `linkedin_publish_blocked_cadence` respectively

#### Scenario: Publication less than 3 days after the previous one is blocked

- **WHEN** publish-due runs in real mode for a due `queued` variant whose campaign has a `published` variant with `published_at` less than 72 hours before now
- **THEN** the variant is not published, is reported with `linkedin_publish_blocked_cadence`, remains `queued`, and no LinkedIn API call occurs

#### Scenario: Publication 3 or more days after the previous one is allowed

- **WHEN** publish-due runs in real mode for a due `queued` variant whose campaign's latest `published_at` is 72 hours or more before now and the sequence rule is satisfied
- **THEN** the variant proceeds to publication under the existing publish rules

#### Scenario: Successful publish within the run blocks further same-campaign publication

- **WHEN** a combined real run publishes one variant of a campaign and a later variant of the same campaign is also due in the same request
- **THEN** the later variant is not published in that request and is reported with `linkedin_publish_blocked_cadence`

#### Scenario: Failed and cancelled earlier variants release the sequence

- **WHEN** publish-due runs for a campaign whose earlier-sequence variant is `failed` or `cancelled` and whose next variant is `queued` and due, with the cadence rule satisfied
- **THEN** the next variant is published, the `failed` variant is not retried, and its stored failure evidence is unchanged

#### Scenario: Deferred earlier variant blocks its followers

- **WHEN** publish-due runs (including with `publish_now` true) for a campaign whose earlier-sequence variant is `pending` with `operator_supervision.last_action` `defer` and a deferred `scheduled_at_utc` in the future, and whose later variant is `queued` and due
- **THEN** the later variant is not published, is reported with `linkedin_publish_blocked_sequence`, and no sibling `scheduled_at_utc` or supervision metadata is mutated

#### Scenario: Campaigns are evaluated independently in the cross-campaign scan

- **WHEN** publish-due runs with no `campaign_id` over two eligible campaigns, one cadence- or sequence-blocked and one with a due publishable variant
- **THEN** the blocked campaign's variants are reported with their stable guard reasons while the other campaign's variant is published, and the overall operation does not fail

#### Scenario: Manually queued out-of-order variant is blocked at publish time

- **WHEN** an operator manually queues a later-sequence variant via `POST /queue-linkedin-publication` while an earlier variant is still `pending` or `queued`, and publish-due then runs
- **THEN** the manually queued variant is not published and is reported with `linkedin_publish_blocked_sequence`

#### Scenario: Missing published_at evidence fails closed and visibly

- **WHEN** publish-due runs for a campaign containing a `published` variant without a parsable `published_at` and a due `queued` variant
- **THEN** the `queued` variant is not published, is reported with `linkedin_publish_blocked_evidence_invalid`, remains `queued`, no LinkedIn or OAuth call occurs for it, and other campaigns in the scan are still evaluated

#### Scenario: Guard evaluation in dry-run mutates nothing

- **WHEN** publish-due runs with `dry_run` true over campaigns with sequence-, cadence-, and evidence-blocked variants
- **THEN** planned blocks are reported with the stable reasons, no metadata is written, and no LinkedIn or OAuth call occurs

## MODIFIED Requirements

### Requirement: Publish due variants service

The worker SHALL expose a publish-due service entry point (for example `publish_linkedin_due_variants(base_path, *, campaign_id=None, variant=None, dry_run=True, publish_now=False, ...)`) that publishes eligible `queued` variants to LinkedIn when due.

Real LinkedIn API calls MUST require `dry_run` false, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`, and a valid access token and member URN resolved through the token provider (or documented env fallback).

The service MUST read variant text from `artifact_relative_path` and include `source_public_url` in commentary (text post format).

The service MUST NOT upload images or publish to company pages.

On real API success, variant MUST become `published`. On real API failure or content rejection, variant MUST become `failed`.

Configuration errors and OAuth `action_required` results from the token provider MUST NOT mark variant `failed`.

**Failure taxonomy (normative consolidation):** variant `publish_state` becomes `failed` only after a real LinkedIn API attempt — API error response (including token invalid/expired, insufficient permission, content rejection, API error), transport-level failure during the call, or success response without a usable post identifier. Blocked conditions fail the HTTP response with a stable code but MUST leave `publish_state` unchanged: publication not enabled (`linkedin_publish_not_enabled`), OAuth reauthorization required (`linkedin_oauth_reauthorization_required` or related), missing member URN (`linkedin_publish_member_urn_missing`), missing token (`linkedin_publish_token_missing`), and dry-run.

**Publish-time sequence and cadence guard:** for every `queued` variant evaluated by this service — in the plain path, in the combined `auto_queue_pending` flow, for targeted requests, and in the cross-campaign scan — the service MUST enforce the per-campaign publish-time sequence and cadence guard (see that requirement) after the existing state and `publish_after_utc` checks and before any dry-run report, configuration validation, token resolution, or LinkedIn API call. Guard-blocked variants are reported with `linkedin_publish_blocked_sequence`, `linkedin_publish_blocked_cadence`, or `linkedin_publish_blocked_evidence_invalid`, MUST NOT change `publish_state`, MUST NOT trigger LinkedIn or OAuth calls, and MUST NOT by themselves fail the overall operation. `publish_now` bypasses only the `publish_after_utc` timing gate, never the guard.

Apply phase MUST verify exact current LinkedIn Posts API payload and required headers against official documentation.

#### Scenario: Successful text post publish

- **WHEN** publish-due runs in real mode for a due `queued` variant with valid credentials from token provider
- **THEN** LinkedIn receives a personal-profile text post whose commentary includes variant text and blog URL, and variant becomes `published`

#### Scenario: API failure marks failed

- **WHEN** publish-due runs in real mode, LinkedIn API is called, and API returns a publish failure
- **THEN** variant `publish_state` becomes `failed` with stable error code in `linkedin_publication`

#### Scenario: Action-required skips LinkedIn API

- **WHEN** publish-due runs in real mode and token provider returns `action_required`
- **THEN** no LinkedIn publication API call occurs and variant `publish_state` remains `queued`

#### Scenario: Dry-run publish-due does not call API

- **WHEN** publish-due runs with `dry_run` true for a due `queued` variant
- **THEN** no LinkedIn API call occurs and variant remains `queued`

#### Scenario: Blocked conditions never mark failed

- **WHEN** a real publish-due request is blocked by enablement off, OAuth reauthorization required, missing member URN, or missing token
- **THEN** the response fails with the corresponding stable code, no LinkedIn API call occurs, and no variant transitions to `failed`

#### Scenario: Guard-blocked variant never marks failed

- **WHEN** a real publish-due request evaluates a `queued` variant blocked by the sequence, cadence, or evidence rule
- **THEN** the variant is reported with the corresponding stable guard reason, remains `queued`, and no LinkedIn API call occurs

### Requirement: Auto-queue eligibility exclusions honor operator supervision

Auto-queue MUST NOT queue a variant when any of the following apply:

- `publish_state` is not `pending` (automatic re-queue from `failed` is excluded; manual re-queue via `POST /queue-linkedin-publication` remains the only `failed` path)
- `publish_state` is `cancelled`
- `operator_supervision.auto_queue_eligible` is `false`, except under the defer runtime re-evaluation rule below
- the variant is not due per `scheduled_at_utc` and `publish_now` is `false`
- an earlier variant in the campaign's canonical audience sequence is awaiting publication — `publish_state` `pending` (including operator-deferred) or `queued` — per the per-campaign publish-time sequence and cadence guard requirement; this exclusion MUST be evaluated last, only for variants that pass every exclusion above, so existing skip reasons (`linkedin_publish_auto_queue_skipped_state`, `linkedin_publish_auto_queue_skipped_supervision`, `linkedin_publish_auto_queue_skipped_not_due`) are reported exactly as before this change; blocked variants are reported with `linkedin_publish_auto_queue_skipped_sequence`

Absent `operator_supervision` on a `pending` variant MUST mean strategy-driven eligible (per `linkedin-variant-review-process`).

**Defer runtime re-evaluation:** US-017 defer persists `auto_queue_eligible` `false` with no persisted flip back. Auto-queue MUST evaluate deferred variants at runtime: a `pending` variant whose `operator_supervision.last_action` is `defer` MUST be treated as eligible once its deferred `scheduled_at_utc` is less than or equal to current worker UTC time, without requiring a persisted `auto_queue_eligible` flip to `true`. While the deferred `scheduled_at_utc` is in the future, the variant MUST be skipped — including when `publish_now` is `true` (`publish_now` never bypasses a deferred time). A deferred earlier variant blocks its followers under the sequence exclusion above until it is published, fails, or is cancelled; this blocking MUST NOT mutate the deferred variant or its siblings (US-017 mechanics and endpoints unchanged).

`publish_now` MUST NOT override supervision exclusions: cancelled variants, variants with `auto_queue_eligible` `false` from cancel, and deferred variants whose new schedule is not yet due are never auto-queued regardless of `publish_now`. `publish_now` MUST NOT override the sequence exclusion either.

Excluded variants MUST NOT change `publish_state` and MUST NOT by themselves cause the overall operation to fail.

#### Scenario: Cancelled variant never auto-queued

- **WHEN** publish-due runs with `auto_queue_pending` true and `publish_now` true for a campaign containing a `cancelled` variant
- **THEN** the cancelled variant is not queued, not published, and remains `cancelled`

#### Scenario: Deferred variant skipped while new schedule not due

- **WHEN** publish-due runs with `auto_queue_pending` true for a `pending` variant with `operator_supervision.last_action` `defer`, `auto_queue_eligible` `false`, and deferred `scheduled_at_utc` still in the future
- **THEN** the variant is skipped with a stable supervision skip reason and remains `pending`

#### Scenario: Deferred variant eligible again when new schedule due

- **WHEN** publish-due runs with `auto_queue_pending` true for a `pending` variant with `operator_supervision.last_action` `defer` and persisted `auto_queue_eligible` `false`, whose deferred `scheduled_at_utc` is now in the past
- **THEN** the variant is treated as eligible per runtime re-evaluation and may be queued without a persisted `auto_queue_eligible` flip to `true`, subject to the sequence exclusion

#### Scenario: publish_now does not bypass a deferred time

- **WHEN** publish-due runs with `auto_queue_pending` true and `publish_now` true for a deferred `pending` variant whose new `scheduled_at_utc` is still in the future
- **THEN** the variant is not queued, remains `pending`, and the response reports a supervision skip reason

#### Scenario: Failed variant not auto-requeued

- **WHEN** publish-due runs with `auto_queue_pending` true for a campaign containing a `failed` variant
- **THEN** the `failed` variant is not queued and the response communicates it is excluded from auto-queue

#### Scenario: Deferred earlier variant blocks followers from auto-queue

- **WHEN** publish-due runs with `auto_queue_pending` true (including with `publish_now` true) for a campaign whose `executive-recruiter` variant is `pending` and operator-deferred with a future deferred `scheduled_at_utc`, and whose `engineering-leadership` variant is `pending` and due
- **THEN** `engineering-leadership` is skipped with `linkedin_publish_auto_queue_skipped_sequence`, remains `pending`, and no metadata of either variant is mutated

#### Scenario: Sequence exclusion evaluated after existing exclusions

- **WHEN** publish-due runs with `auto_queue_pending` true for a campaign whose earlier-sequence variant is awaiting publication and whose later variant is not due per `scheduled_at_utc` with `publish_now` false
- **THEN** the later variant is reported with `linkedin_publish_auto_queue_skipped_not_due` (not the sequence reason), preserving pre-existing skip-reason behavior

### Requirement: Auto-queue outcome visibility

When `auto_queue_pending` is `true`, the response MUST include operator-understandable per-variant results covering both phases:

- variants queued by the auto-queue phase (with resulting `publish_state` and `publish_after_utc`)
- variants published, already published, or failed by the publish phase (existing publish-due result semantics)
- variants skipped, with stable machine-readable reasons distinguishing at minimum: not due per schedule, supervision-excluded (cancelled or `auto_queue_eligible` `false`), not in an auto-queueable `publish_state`, blocked by the audience sequence at auto-queue, blocked at publish time by sequence, by cadence, or by missing/invalid publication evidence, and campaign-level ineligibility

Stable reason/warning codes MUST include at minimum:

- `linkedin_publish_auto_queue_skipped_not_due`
- `linkedin_publish_auto_queue_skipped_supervision`
- `linkedin_publish_auto_queue_skipped_state`
- `linkedin_publish_auto_queue_skipped_sequence`

Publish-phase results within the combined operation MUST surface the guard reasons `linkedin_publish_blocked_sequence`, `linkedin_publish_blocked_cadence`, and `linkedin_publish_blocked_evidence_invalid` per variant when the publish-time guard blocks a `queued` variant.

When a variant results `published` or already-published within the auto-queue operation — including the cross-campaign scan without `campaign_id` — its `auto_queue_results` entry MUST include `linkedin_post_urn` and `published_at` (additive optional fields on the existing result shape; absent or null for entries with no publication evidence).

Responses MUST NOT include variant body text or secret values.

#### Scenario: Skip reasons visible per variant

- **WHEN** publish-due runs with `auto_queue_pending` true over a campaign with one due eligible variant, one future-scheduled variant, and one cancelled variant
- **THEN** the response reports the first as queued (and published or queued-not-due per publish rules), the second skipped with `linkedin_publish_auto_queue_skipped_not_due`, and the third skipped with `linkedin_publish_auto_queue_skipped_supervision`

#### Scenario: Sequence skip reason visible per variant at auto-queue

- **WHEN** publish-due runs with `auto_queue_pending` true over a campaign with two due eligible `pending` variants in canonical sequence
- **THEN** the later variant's `auto_queue_results` entry reports it skipped with reason `linkedin_publish_auto_queue_skipped_sequence`

#### Scenario: Publish-time guard reasons visible per variant

- **WHEN** a combined run evaluates a `queued` variant blocked at publish time by sequence, cadence, or invalid evidence
- **THEN** the per-variant publish result carries the corresponding stable reason (`linkedin_publish_blocked_sequence`, `linkedin_publish_blocked_cadence`, or `linkedin_publish_blocked_evidence_invalid`)

#### Scenario: No secrets or body text in combined response

- **WHEN** the combined auto-queue and publish operation completes or fails
- **THEN** the HTTP response contains no token values and no variant body text

#### Scenario: Auto-queue results carry evidence for published outcomes

- **WHEN** a real combined run with `auto_queue_pending` true results in a variant `published`, or encounters a variant already `published` with stored evidence
- **THEN** that variant's `auto_queue_results` entry includes non-null `linkedin_post_urn` and `published_at`

### Requirement: Stable error codes

LinkedIn publication MUST use stable error codes including at minimum:

- `linkedin_publish_campaign_not_found`
- `linkedin_publish_flow_not_allowed`
- `linkedin_publish_invalid_campaign_state`
- `linkedin_publish_variant_not_found`
- `linkedin_publish_variant_not_pending`
- `linkedin_publish_variant_not_queued`
- `linkedin_publish_variant_not_due`
- `linkedin_publish_blocked_sequence`
- `linkedin_publish_blocked_cadence`
- `linkedin_publish_blocked_evidence_invalid`
- `linkedin_publish_artifact_missing`
- `linkedin_publish_artifact_hash_changed`
- `linkedin_publish_missing_source_public_url`
- `linkedin_publish_token_missing`
- `linkedin_publish_member_urn_missing`
- `linkedin_publish_token_invalid`
- `linkedin_publish_token_expired`
- `linkedin_publish_insufficient_permission`
- `linkedin_publish_not_enabled`
- `linkedin_publish_api_error`
- `linkedin_publish_content_invalid`
- `linkedin_publish_metadata_write_failed`
- `linkedin_publish_cancel_not_allowed`
- `linkedin_oauth_token_missing`
- `linkedin_oauth_refresh_failed`
- `linkedin_oauth_reauthorization_required`

#### Scenario: Stable error codes in response

- **WHEN** a known eligibility or configuration failure occurs
- **THEN** `errors[]` contains the documented stable code string

### Requirement: Test coverage

The repository MUST include `tests/test_linkedin_publication.py` covering at minimum:

- successful queue `pending` → `queued` with `publish_after_utc`
- successful publish-due with mocked LinkedIn client → `published`
- cancel `queued` → `cancelled`
- missing token / missing member URN / not enabled — response fails, variant NOT `failed`
- OAuth token provider `action_required` — response fails, variant NOT `failed`, no LinkedIn API call
- invalid/expired token / insufficient permission on real API attempt → variant `failed`
- publish-due skips not-yet-due variant unless `publish_now`
- idempotent behavior for already `published`
- dry-run defaults and no mutation on queue/publish/cancel dry-run
- wrong campaign state, missing artifact, hash mismatch
- HTTP auth and 422 validation for all three endpoints
- `auto_queue_pending` default false leaves `pending` variants untouched
- auto-queue queues and publishes a due eligible `pending` variant once (mocked LinkedIn client)
- auto-queue skips: not due per `scheduled_at_utc`, `cancelled`, `operator_supervision.auto_queue_eligible` `false` from cancel, and `failed` variants, with stable skip reasons
- deferred variant skipped while its new `scheduled_at_utc` is in the future (persisted `auto_queue_eligible` `false` from defer)
- deferred variant eligible again at runtime once new `scheduled_at_utc` is due, without a persisted `auto_queue_eligible` flip
- `publish_now` bypasses the schedule gate for strategy-default variants but never supervision exclusions, including a deferred variant whose new schedule is not yet due
- repeat combined run does not duplicate LinkedIn posts and does not re-queue `queued` variants
- dry-run combined run performs no mutation and no LinkedIn/OAuth calls
- `variant` without `campaign_id` returns HTTP 422
- publish-pending n8n workflow export has `active` false and no Execute Command nodes
- **US-019 evidence completeness:** after mocked real publish success, metadata contains non-empty `linkedin_post_urn`, UTC `published_at`, and `linkedin_publication` with `provider`, `post_urn` equal to `linkedin_post_urn`, `published_at`, and `http_status`
- **US-019 failure context shape:** after mocked real API failure, `linkedin_publication` contains at minimum `last_error_code`, `last_failed_at`, `retryable`, `http_status`, with no secrets or body text; transport-level failure records `http_status` null
- **US-019 content rejection code:** mocked LinkedIn content-rejection response yields `failed` with `last_error_code` `linkedin_publish_content_invalid` (distinct from generic `linkedin_publish_api_error`) and numeric `http_status`
- **US-019 success-without-identifier:** mocked API success without a post identifier yields `failed` with `linkedin_publish_api_error`, never `published` without URN
- **US-019 blocked-vs-failed taxonomy:** enablement off, OAuth `action_required`, missing member URN, and missing token each fail the response with the stable code while `publish_state` is unchanged
- **US-019 response evidence:** per-variant HTTP result carries `linkedin_post_urn` and `published_at` for published and already-published outcomes
- **US-019 auto-queue evidence:** under `auto_queue_pending` (including the cross-campaign scan without `campaign_id`), `auto_queue_results` entries for published and already-published variants include non-null `linkedin_post_urn` and `published_at`
- **US-019 idempotency evidence:** repeat runs (direct, `publish_now: true`, and `auto_queue_pending: true`) over a `published` variant preserve stored `linkedin_post_urn` and `published_at` byte-for-byte with zero LinkedIn API calls
- **US-019 no automatic retry:** a mocked failed real attempt produces exactly one LinkedIn API call and the `failed` variant is excluded from subsequent automatic publish/auto-queue paths
- **US-020 sequence over queued variants:** with two `queued` variants of one campaign both past `publish_after_utc`, variant N is not published while variant N-1 remains `queued`/unpublished; N reports `linkedin_publish_blocked_sequence` (mocked LinkedIn client, zero real calls)
- **US-020 plain publish-due guard:** the same sequence enforcement holds with `auto_queue_pending` false
- **US-020 publish_now non-bypass:** `publish_now` true bypasses neither the sequence rule nor the cadence rule; blocked variants keep their `publish_state`
- **US-020 cadence blocks under 3 days:** a campaign with a `published` variant whose `published_at` is less than 72 hours before now does not publish its next due `queued` variant; the variant reports `linkedin_publish_blocked_cadence`
- **US-020 cadence allows at 3 or more days:** with the latest `published_at` 72 hours or more before now and the sequence satisfied, the next due `queued` variant publishes
- **US-020 within-run cadence:** after a successful publish in the current run, no second variant of the same campaign publishes in that run
- **US-020 releasing states:** earlier `failed` and `cancelled` variants release the chain; the `failed` variant is not retried and its stored failure evidence is byte-for-byte unchanged
- **US-020 defer blocks followers:** an operator-deferred earlier `pending` variant blocks later variants from auto-queue and publish, including under `publish_now`, without mutating any sibling metadata
- **US-020 per-campaign scope:** the cross-campaign scan evaluates each campaign's sequence and cadence independently; one campaign's block never affects another campaign's publication
- **US-020 dry-run:** sequence, cadence, and evidence blocks are reported under `dry_run` true with no metadata writes and no LinkedIn/OAuth calls
- **US-020 evidence fail-closed:** a `published` variant with missing or unparsable `published_at` blocks further publication in its campaign with `linkedin_publish_blocked_evidence_invalid`, visibly, without failing the overall operation or affecting other campaigns
- **US-020 no contract reshape:** existing US-018 auto-queue and US-019 evidence tests pass unmodified with no weakened assertions (skip-reason precedence preserved; no renamed or retyped fields)

OAuth lifecycle tests belong to `linkedin-oauth-token-lifecycle` but publication integration tests MUST cover provider `action_required` behavior.

#### Scenario: Test module passes

- **WHEN** `pytest` runs after apply
- **THEN** `tests/test_linkedin_publication.py` passes
