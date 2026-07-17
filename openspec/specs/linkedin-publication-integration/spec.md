# linkedin-publication-integration

## Purpose

Flow A deferred LinkedIn API publication for the `silverman-blog-linkedin` HTTP worker: queue-and-safety-delay model with separate queue, publish-due, and cancel actions; worker-side scheduling only (no LinkedIn native scheduling); personal-profile text posts; per-variant state model; dry-run defaults; smoke tooling; and operator documentation. Implements umbrella slice 8 as a follow-up to Flow A Core.

## Requirements

### Requirement: Umbrella and dependency references

This child change SHALL implement Flow A LinkedIn API publication under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 8), as a **follow-up** to Flow A Core completion at `distribution_scheduled`.

Publication behavior MUST align with Flow A policy in canonical spec `editorial-canon`.

Campaign metadata and variant IDs MUST use canonical spec `flow-a-lifecycle` and worker module `campaign_lifecycle.py`.

Publication MUST consume scheduling metadata from canonical spec `linkedin-distribution-scheduling-model` and artifacts from `linkedin-derivative-package-generation`.

Existing `scheduled_at_utc` MUST remain the internal distribution schedule. LinkedIn MUST receive posts only when the worker calls the LinkedIn API. This change MUST NOT assume LinkedIn native personal-profile scheduled posting.

Flow B campaigns MUST NOT enter this publication path.

This capability is **separate from Flow A Core** — Flow A Core success does not require LinkedIn API publication.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, lifecycle, package generation, and distribution scheduling child changes

#### Scenario: Worker-side scheduling only

- **WHEN** a variant is queued or published
- **THEN** timing is controlled by worker metadata (`scheduled_at_utc`, `publish_after_utc`) and worker endpoint invocation, not LinkedIn-side scheduling

### Requirement: Per-variant publish states

LinkedIn publication MUST use these per-variant `publish_state` values:

- `pending` — scheduled by Flow A Core; not authorized for LinkedIn API publication
- `queued` — authorized; waiting for `publish_after_utc` before eligible for real publish
- `published` — successfully sent to LinkedIn
- `failed` — real LinkedIn API attempt failed or content/platform rejection for that variant
- `cancelled` — operator cancelled before real publish (from `pending` pre-queue or from `queued` post-queue)

#### Scenario: Initial state after Flow A Core

- **WHEN** distribution scheduling completes
- **THEN** each variant has `publish_state` `pending`

#### Scenario: Queue transitions pending to queued

- **WHEN** real queue succeeds for a `pending` variant
- **THEN** variant `publish_state` becomes `queued`

#### Scenario: Cancel transitions queued to cancelled

- **WHEN** real cancel succeeds for a `queued` variant
- **THEN** variant `publish_state` becomes `cancelled` and published variants are unchanged

#### Scenario: Cancel transitions pending to cancelled

- **WHEN** real cancel succeeds for a `pending` variant during the supervision window
- **THEN** variant `publish_state` becomes `cancelled`, `operator_supervision.cancellation.phase` is `pre_queue`, and published variants are unchanged

### Requirement: LinkedIn publication configuration

The worker SHALL support these environment variables:

- `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` — must be `true` for real LinkedIn API calls
- `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` — default safety delay; default value `120` for this phase
- `SILVERMAN_LINKEDIN_API_VERSION` — optional LinkedIn API version header override

For OAuth token lifecycle (canonical spec `linkedin-oauth-token-lifecycle`), the worker SHALL resolve access token and member URN through the token provider using `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` and OAuth configuration. Environment variables `SILVERMAN_LINKEDIN_ACCESS_TOKEN` and `SILVERMAN_LINKEDIN_MEMBER_URN` MAY remain as documented manual fallback only when token store is unavailable.

The worker MUST NOT print, log, or return access tokens, refresh tokens, or client secrets in HTTP responses, smoke scripts, diagnostic output, or error messages.

Missing or action-required OAuth credentials, missing member URN after provider resolution, or publication not enabled MUST fail the HTTP response with stable error codes but MUST NOT set variant `publish_state` to `failed`.

#### Scenario: OAuth action-required does not mark failed

- **WHEN** a real publish-due request runs with `dry_run` false and token provider returns `action_required` (for example reauthorization needed)
- **THEN** the operation fails with `linkedin_oauth_reauthorization_required` or related stable code, no LinkedIn publication API call occurs, and variant `publish_state` remains `queued`

#### Scenario: Missing member URN on real publish

- **WHEN** a real publish-due request runs with `dry_run` false and neither token store nor fallback env provides member URN
- **THEN** the operation fails with `linkedin_publish_member_urn_missing`, no LinkedIn API call occurs, and variant `publish_state` is unchanged

#### Scenario: Config error does not mark failed

- **WHEN** a real publish-due request fails because `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not `true`
- **THEN** response includes `linkedin_publish_not_enabled` and variant `publish_state` remains `queued` (not `failed`)

#### Scenario: Token never in response

- **WHEN** any LinkedIn publication operation completes or fails
- **THEN** HTTP response and campaign metadata do not contain token values

### Requirement: Safety delay and publish_after_utc

Real queue operations MUST set `publish_after_utc` on the variant using:

- request `publish_after_utc` when provided (UTC ISO8601), or
- `now_utc + safety_delay_minutes`, where `safety_delay_minutes` comes from request override or `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` (default `120`)

Real publish-due MUST publish a `queued` variant only when `publish_after_utc <= now_utc`, unless request `publish_now` is `true`.

Immediate publication MUST require either `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES=0` at queue time or explicit `publish_now: true` on publish-due.

Future immediate mode MUST be achievable by configuration or request flag without redesigning the queue/publish flow.

#### Scenario: Default safety delay applied on queue

- **WHEN** real queue runs without `publish_after_utc` or `safety_delay_minutes` and default delay is `120`
- **THEN** variant `publish_after_utc` is approximately `now + 120 minutes` and `publication_safety_delay_minutes` is `120`

#### Scenario: Publish-due skips not-yet-due variant

- **WHEN** publish-due runs in real mode for a `queued` variant whose `publish_after_utc` is in the future and `publish_now` is false
- **THEN** no LinkedIn API call occurs and response indicates variant not yet due

#### Scenario: Publish_now bypasses delay

- **WHEN** publish-due runs with `publish_now` true for a `queued` variant and real publish is enabled
- **THEN** LinkedIn API may be called regardless of `publish_after_utc`

### Requirement: Per-variant publication metadata fields

For queued variants, campaign metadata MUST record at minimum:

- `publish_after_utc`
- `publication_queued_at`
- `publication_mode` (for example `safety_delay`)
- `publication_safety_delay_minutes`

For published variants after a real successful publish, metadata MUST record the **complete publication evidence**, with the following mandatory fields:

- `linkedin_post_urn` — non-empty external publication identifier returned by LinkedIn (**mandatory**)
- `published_at` — UTC ISO8601 `Z` timestamp written at publish time (**mandatory**)
- `linkedin_publication` — safe provider subset (no tokens, no variant body text, no raw API response bodies) containing at minimum `provider`, `post_urn` (equal to `linkedin_post_urn`), `published_at` (equal to top-level `published_at`), and `http_status` (**mandatory**)

`linkedin_post_id` is an OPTIONAL additive alias field; it MUST NOT substitute for `linkedin_post_urn` as the required identifier.

A real API success response that does not yield a non-empty post identifier MUST be treated as a publish failure (stable code `linkedin_publish_api_error`), not as a published variant with incomplete evidence.

For failed variants after a real API attempt, metadata MUST record failure context in `linkedin_publication` containing at minimum these fields, in a safe shape (no secrets, no variant body text, no raw API response bodies — any future additional fields MUST honor the same prohibition):

- `last_error_code` — stable code from the documented set (**mandatory**)
- `last_failed_at` — UTC ISO8601 `Z` timestamp (**mandatory**)
- `retryable` — boolean, recorded as descriptive evidence only (**mandatory**)
- `http_status` — **mandatory but nullable**: null when no HTTP response was received (transport-level failure)

`http_status` is a MANDATORY field inside `linkedin_publication` in both success and failure evidence after a real attempt: numeric whenever an HTTP response was received, `null` only when none was (transport-level failure).

Content rejection by LinkedIn MUST be recorded with the dedicated stable code `linkedin_publish_content_invalid`, distinct from the generic `linkedin_publish_api_error`.

Every real LinkedIn API call MUST also append exactly one safe immutable entry to `linkedin_publication_attempts` under the contract defined by `linkedin-retry-recovery-classification`. The latest `linkedin_publication` object MUST remain available as the compatibility view of the latest outcome. Queueing a failed variant MUST NOT remove it.

Every successful mutating failed-state re-queue, correction, or cancellation MUST append the corresponding safe immutable `linkedin_recovery_history` event. Campaign metadata and HTTP responses MUST NOT include variant body text, tokens, secrets, or raw API response bodies.

#### Scenario: Queue writes publication metadata

- **WHEN** real queue succeeds
- **THEN** variant records `publication_queued_at`, `publish_after_utc`, `publication_mode`, and `publication_safety_delay_minutes`

#### Scenario: Publish writes URN without body text

- **WHEN** real publish succeeds
- **THEN** variant records `linkedin_post_urn`, `published_at`, `linkedin_publication`, and one published attempt-history entry without artifact body text in metadata or HTTP response

#### Scenario: Complete evidence after real successful publish

- **WHEN** a real publish succeeds for a variant
- **THEN** variant metadata contains non-empty `linkedin_post_urn`, UTC `published_at`, and `linkedin_publication` with `provider`, `post_urn`, `published_at`, and `http_status`, `linkedin_publication.post_urn` equals `linkedin_post_urn`, and attempt history retains this outcome

#### Scenario: Failure context shape after real API failure

- **WHEN** a real publish attempt receives a LinkedIn API error response
- **THEN** variant `publish_state` becomes `failed`, `linkedin_publication` contains `last_error_code`, `last_failed_at`, `retryable`, and numeric `http_status`, and one failed attempt entry is appended with no secrets, body text, or raw API response

#### Scenario: Content rejection records dedicated stable code

- **WHEN** a real publish attempt receives a LinkedIn API response rejecting the post content
- **THEN** variant `publish_state` becomes `failed` and both latest evidence and attempt history use `linkedin_publish_content_invalid` with numeric `http_status`

#### Scenario: Transport failure records null http_status

- **WHEN** a real publish attempt fails at transport level without receiving an HTTP response
- **THEN** variant `publish_state` becomes `failed` and both latest evidence and attempt history record `http_status` null

#### Scenario: Success without post identifier treated as failure

- **WHEN** a real publish attempt receives an API success response without a usable post identifier
- **THEN** the attempt is recorded as failed with `linkedin_publish_api_error` and `http_status` `201`, and the variant does not become `published`

### Requirement: Queue publication service

The worker SHALL expose a queue service entry point that validates eligibility and moves eligible variants from `pending` or manually recoverable `failed` to `queued` without calling LinkedIn API.

The queue entry point MUST NOT call LinkedIn API, move editorial source files, or run git operations.

When `dry_run` is true, the entry point MUST validate and return the planned queue outcome, recovery class, attempt count, retries used, and retries remaining without mutating metadata or `publish_state`.

When `dry_run` is false for `pending`, the entry point MUST preserve existing behavior: transition `pending -> queued` and write queue metadata.

When `dry_run` is false for `failed`, the entry point MUST:

- normalize valid legacy failure evidence when required;
- classify through `linkedin-retry-recovery-classification`;
- enforce the three-attempt limit and class-specific confirmation/correction requirements;
- transition `failed -> queued`;
- append one `manual_requeue` recovery event;
- preserve latest `linkedin_publication` and all attempt history.

#### Scenario: Real queue from pending

- **WHEN** queue is called with `dry_run` false for a `pending` variant on an eligible Flow A campaign with valid artifact
- **THEN** variant becomes `queued`, `publish_after_utc` is set, no LinkedIn API call occurs, and no recovery confirmation is accepted

#### Scenario: Dry-run queue does not mutate state

- **WHEN** queue is called with `dry_run` true for an eligible variant
- **THEN** response is completed or carries the stable recovery block, reports counters, and variant metadata is unchanged

#### Scenario: Real manual re-queue preserves evidence

- **WHEN** queue is called with `dry_run` false for a below-limit failed variant satisfying its US-021 recovery requirements
- **THEN** variant becomes `queued`, one recovery event is appended, latest failure and attempt history are retained, and no LinkedIn API call occurs

#### Scenario: Retry exhaustion blocks queue

- **WHEN** queue is called for a failed variant with three real attempts
- **THEN** it returns `linkedin_publish_retry_limit_exhausted`, reports zero retries remaining, and writes no metadata

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

### Requirement: Cancel publication service

The worker SHALL expose a cancel service entry point that transitions `queued -> cancelled`, `pending -> cancelled`, or `failed -> cancelled`.

Cancel from `pending` MUST record `operator_supervision` cancellation audit with `phase` `pre_queue`.

Cancel from `queued` MUST record `operator_supervision` cancellation audit with `phase` `post_queue` (or preserve existing `linkedin_publication.cancelled_at` alongside `operator_supervision`).

Cancel from `failed` MUST preserve latest publication evidence and all attempt/recovery history, append a `recovery_cancelled` event tied to the latest attempt, and report attempt/retry counters.

Cancel MUST set `operator_supervision.auto_queue_eligible` to `false` when persisting cancellation.

Cancel MUST NOT affect `published` variants and MUST NOT call LinkedIn API.

#### Scenario: Cancel queued variant

- **WHEN** cancel runs with `dry_run` false for a `queued` variant
- **THEN** variant `publish_state` becomes `cancelled` under existing post-queue behavior

#### Scenario: Cancel pending variant during supervision

- **WHEN** cancel runs with `dry_run` false for a `pending` variant
- **THEN** variant `publish_state` becomes `cancelled` and `operator_supervision.cancellation.phase` is `pre_queue`

#### Scenario: Cancel failed variant preserves recovery evidence

- **WHEN** cancel runs with `dry_run` false for a failed or retry-exhausted variant
- **THEN** variant becomes `cancelled`, its publication attempts remain unchanged, one recovery cancellation event is appended, and no LinkedIn API call occurs

#### Scenario: Cancel rejected for published

- **WHEN** cancel is requested for a `published` variant
- **THEN** operation fails with `linkedin_publish_cancel_not_allowed` and variant remains `published`

### Requirement: Campaign eligibility

Queue, publish-due, and cancel MUST require campaign metadata at `metadata/campaigns/<campaign-id>.json`, `flow` `flow_a`, and campaign `state` `distribution_scheduled`.

Queue MUST require variant `publish_state` `pending` (or `failed` when re-queue retry is supported).

Publish-due MUST require variant `publish_state` `queued` for real publish attempts.

Cancel MUST require variant `publish_state` `queued`, `pending`, or `failed` (US-022 failed-state cancellation).

Artifact existence and hash verification MUST match distribution scheduling rules before queue or publish.

This change MUST NOT transition campaign state to `distribution_complete` or beyond in v1.

#### Scenario: Cancel pending requires distribution_scheduled campaign

- **WHEN** cancel is requested for a `pending` variant on a `distribution_scheduled` Flow A campaign
- **THEN** the operation is eligible for validation or execution per `dry_run`

#### Scenario: Campaign state unchanged after publish

- **WHEN** a variant is successfully published
- **THEN** campaign `state` remains `distribution_scheduled`

#### Scenario: Queue rejected before distribution_scheduled

- **WHEN** queue is requested for a campaign in state `derivatives_generated`
- **THEN** the operation fails with `linkedin_publish_invalid_campaign_state`

### Requirement: HTTP endpoint POST /queue-linkedin-publication

The worker SHALL expose `POST /queue-linkedin-publication` with API key authentication.

Request body MUST include `campaign_id`, `variant`, and optional `dry_run` (default `true`), `safety_delay_minutes`, `publish_after_utc`, and `recovery_confirmation`.

`recovery_confirmation` MUST accept only `remediation_completed` or `linkedin_post_absence_verified`. It MUST be absent for `pending` queue and transient failed recovery, MUST match the US-021 class when required, and MUST NOT replace mechanically required content correction.

Request model MUST use `extra="forbid"`.

Response MUST include at minimum: `status`, `campaign_id`, `variant`, `state`, `publish_state`, `dry_run`, `publish_after_utc`, `errors`, `warnings`, `metadata_written`, and additive nullable `publication_attempt_count`, `manual_retries_used`, `manual_retries_remaining`, and `recovery_classification`.

#### Scenario: Queue endpoint defaults to dry-run

- **WHEN** request omits `dry_run`
- **THEN** worker treats request as `dry_run` true

#### Scenario: Queue endpoint requires auth

- **WHEN** called without valid API key
- **THEN** request is rejected unauthorized

#### Scenario: Queue endpoint rejects unknown confirmation

- **WHEN** request supplies a `recovery_confirmation` outside the two supported values
- **THEN** request is rejected with HTTP 422 and metadata is unchanged

#### Scenario: Pending queue rejects recovery confirmation

- **WHEN** a pending queue request supplies either recovery confirmation
- **THEN** queue returns `linkedin_publish_recovery_confirmation_invalid` and leaves the variant pending

### Requirement: HTTP endpoint POST /publish-linkedin-due-variants

The worker SHALL expose `POST /publish-linkedin-due-variants` with API key authentication.

Request body MUST include optional `campaign_id`, optional `variant`, optional `dry_run` (default `true`), optional `publish_now` (default `false`), and optional `auto_queue_pending` (default `false`).

When `campaign_id` and `variant` are omitted, worker MAY evaluate all eligible queued variants under base path (bounded behavior documented at apply); when `auto_queue_pending` is `true`, the bounded cross-campaign pending scan requirement applies additionally.

Response MUST include per-variant results or summary with `publish_state`, `linkedin_post_urn`, `published_at`, `errors`, `dry_run`; when `auto_queue_pending` is `true`, the response MUST additionally satisfy the auto-queue outcome visibility requirement.

For a variant whose outcome is `published` (first publish) or already-published (idempotent replay), the per-variant result MUST carry the stored non-null `linkedin_post_urn` and `published_at` as operator-visible publication evidence. This rule applies to publish-phase results and equally to `auto_queue_results` entries under `auto_queue_pending`, including the cross-campaign scan without `campaign_id`: a `published` variant encountered by the scan is still reported as a skip (`linkedin_publish_auto_queue_skipped_state`), but its entry MUST include the preserved `linkedin_post_urn` and `published_at`.

#### Scenario: Publish-due endpoint defaults to dry-run

- **WHEN** request omits `dry_run`
- **THEN** worker treats request as `dry_run` true and does not call LinkedIn API

#### Scenario: Publish-due invalid body returns 422

- **WHEN** request includes unknown extra fields
- **THEN** API returns HTTP 422

#### Scenario: Auto-queue defaults off

- **WHEN** request omits `auto_queue_pending`
- **THEN** worker treats request as `auto_queue_pending` false and does not evaluate `pending` variants

#### Scenario: Published outcome carries evidence in response

- **WHEN** a real publish-due request publishes a variant successfully
- **THEN** the per-variant result includes the non-null `linkedin_post_urn` and `published_at` that were written to campaign metadata

#### Scenario: Already-published replay carries preserved evidence in response

- **WHEN** publish-due runs for a variant already `published` with stored `linkedin_post_urn`
- **THEN** the per-variant result includes the preserved `linkedin_post_urn` and `published_at` and the warning `linkedin_publish_already_published`

#### Scenario: Cross-campaign scan skip entry carries preserved evidence

- **WHEN** publish-due runs with `auto_queue_pending` true and no `campaign_id` over metadata containing a `published` variant with stored `linkedin_post_urn`
- **THEN** the variant's `auto_queue_results` entry reports skip reason `linkedin_publish_auto_queue_skipped_state` and includes the preserved `linkedin_post_urn` and `published_at`

### Requirement: Auto-queue pending due variants (opt-in)

`POST /publish-linkedin-due-variants` SHALL support an optional request field `auto_queue_pending` (boolean, default `false`).

When `auto_queue_pending` is `false` or omitted, publish-due behavior MUST be unchanged from the canonical two-step contract (queue and publish-due remain separate operations).

When `auto_queue_pending` is `true`, the worker MUST, within the same request:

1. Identify eligible due `pending` variants (per the auto-queue eligibility requirement).
2. Queue each eligible variant using the existing queue publication service rules, computing `publish_after_utc` from the configured default safety delay (`SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES`); the publish-due request MUST NOT accept a `safety_delay_minutes` field (that override remains exclusive to `POST /queue-linkedin-publication`).
3. Evaluate publish-due for `queued` variants exactly as the existing publish-due service defines (including `publish_after_utc <= now_utc` unless `publish_now` is `true`).

A `pending` variant is **due for auto-queue** when its `scheduled_at_utc` is less than or equal to current worker UTC time. When request `publish_now` is `true`, the `scheduled_at_utc` due gate MAY be bypassed as an explicit operator override; supervision exclusions MUST still apply.

Variants with missing or unparsable `scheduled_at_utc` MUST be skipped with a stable reason and MUST NOT abort the operation.

The auto-queue phase MUST reuse the existing queue service validation (campaign eligibility, artifact existence and hash verification, source public URL) rather than a parallel implementation.

When `dry_run` is `true`, the combined operation MUST report planned queue and publish outcomes without mutating `publish_state`, writing metadata, or calling LinkedIn or OAuth endpoints.

#### Scenario: Default off preserves two-step contract

- **WHEN** `POST /publish-linkedin-due-variants` is called without `auto_queue_pending`
- **THEN** no `pending` variant is queued or evaluated and behavior matches the existing publish-due contract for `queued` variants only

#### Scenario: Due pending variant queued and published in one call

- **WHEN** publish-due runs with `auto_queue_pending` true, `dry_run` false, `publish_now` true, and real publish enabled for an eligible `pending` variant whose `scheduled_at_utc` is in the past
- **THEN** the variant is queued via existing queue rules and then published once, ending in `publish_state` `published`

#### Scenario: Not-yet-due pending variant skipped when respecting schedule

- **WHEN** publish-due runs with `auto_queue_pending` true and `publish_now` false for a `pending` variant whose `scheduled_at_utc` is in the future
- **THEN** the variant is not queued, remains `pending`, and the response reports it skipped as not due

#### Scenario: Safety delay still gates publish after auto-queue

- **WHEN** publish-due runs with `auto_queue_pending` true and `publish_now` false, and the queue phase sets `publish_after_utc` in the future via nonzero safety delay
- **THEN** the variant ends the call in `publish_state` `queued` with no LinkedIn API call, and the response communicates it was queued but not yet due for publish

#### Scenario: Dry-run auto-queue does not mutate state

- **WHEN** publish-due runs with `auto_queue_pending` true and `dry_run` true for an eligible due `pending` variant
- **THEN** the variant remains `pending`, no metadata is written, and no LinkedIn or OAuth call occurs

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
### Requirement: Bounded cross-campaign pending scan

When `auto_queue_pending` is `true` and `campaign_id` is omitted, the worker MUST bound the pending scan to campaign metadata documents under `metadata/campaigns/` and MUST consider only campaigns with `flow` `flow_a` and `state` `distribution_scheduled`.

Campaigns that are ineligible or unreadable MUST be skipped without failing the overall operation.

When `variant` is provided without `campaign_id`, the request MUST be rejected as invalid (HTTP 422).

When `campaign_id` is provided, the scan MUST be limited to that campaign; when `variant` is additionally provided, to that single variant.

#### Scenario: Cross-campaign scan targets only eligible Flow A campaigns

- **WHEN** publish-due runs with `auto_queue_pending` true and no `campaign_id` while the metadata folder contains a `distribution_scheduled` Flow A campaign and a campaign in another state
- **THEN** only the `distribution_scheduled` Flow A campaign's pending variants are considered for auto-queue

#### Scenario: Variant filter without campaign rejected

- **WHEN** `POST /publish-linkedin-due-variants` is called with `variant` set and no `campaign_id`
- **THEN** the API returns HTTP 422

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
### Requirement: Once-only publication under auto-queue

The combined operation MUST NOT create duplicate LinkedIn posts or duplicate queue metadata:

- variants already `queued` MUST NOT be re-queued (no rewrite of `publication_queued_at` or reset of `publish_after_utc` by the auto-queue phase)
- variants already `published` MUST retain the existing idempotent behavior (no LinkedIn API call; URN and `published_at` preserved)
- repeating the same combined request after a successful real run MUST NOT publish any variant a second time

Real LinkedIn API calls under `auto_queue_pending` MUST still require `dry_run` false, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`, and valid credentials via the token provider; enablement-off MUST fail closed with `linkedin_publish_not_enabled` without marking variants `failed`.

#### Scenario: Repeat combined run is idempotent

- **WHEN** a real combined run publishes a variant and the identical request is repeated
- **THEN** the second run makes no LinkedIn API call for that variant and its `linkedin_post_urn` and `published_at` are unchanged

#### Scenario: Already-queued variant not double-queued

- **WHEN** publish-due runs with `auto_queue_pending` true for a campaign containing a `queued` variant
- **THEN** the auto-queue phase does not modify that variant's queue metadata and the publish phase evaluates it under existing due rules

#### Scenario: Enablement off fails closed under auto-queue

- **WHEN** a real combined run executes with `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` not `true`
- **THEN** no LinkedIn API call occurs, the response includes `linkedin_publish_not_enabled`, and no variant transitions to `failed`

### Requirement: No automatic retry within publication execution

The publication execution capability MUST NOT automatically retry a failed real LinkedIn API attempt — not within the same request, not via background jobs, and not by automatically re-queueing `failed` variants.

The `retryable` field recorded in failure context remains descriptive evidence only. Classification, confirmation, and retry-limit decisions MUST be delegated to the canonical `linkedin-retry-recovery-classification` capability and enforced only on explicit manual re-queue.

Manual re-queue of a `failed` variant via `POST /queue-linkedin-publication` MUST remain the only retry path. It MUST enforce at most two manual retries after the initial real attempt and preserve latest, attempt, and recovery evidence.

#### Scenario: Failed real attempt is not retried in the same request

- **WHEN** a real publish-due attempt calls LinkedIn for a variant and returns a failure
- **THEN** variant becomes `failed`, exactly one LinkedIn call and one attempt-history append occur, and no automatic retry occurs

#### Scenario: Failed variant excluded from automatic paths

- **WHEN** a later publish-due request runs with or without `auto_queue_pending` over a failed variant
- **THEN** it is not published or auto-queued, and only explicit manual re-queue can make it eligible

#### Scenario: Explicit manual retry remains bounded

- **WHEN** an operator explicitly queues a recoverable failed variant
- **THEN** publication integration applies the retry limit and recovery requirements without deriving behavior from `retryable` alone

### Requirement: Publish-pending operator script

The repository MUST provide `deploy/server/run-publish-pending-linkedin-variants.sh` that:

- calls `POST /publish-linkedin-due-variants` with `auto_queue_pending: true` over HTTP with API key auth
- defaults to dry-run; real mode requires an explicit `--real` flag and preflights `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` in the server env file
- supports `--respect-schedule` (maps to `publish_now: false`) and optional `--campaign-id` / `--variant` filters (`--variant` requires `--campaign-id`)
- never prints secret values
- reports the worker response and an overall pass/fail derived from response `status`

The repository MAY provide `deploy/server/finish-pending-linkedin-publication.sh` as a Mac-side copy-and-run helper; it MUST invoke the server script over the same HTTP-only contract and MUST NOT bypass worker endpoints.

#### Scenario: Script defaults to dry-run

- **WHEN** the operator runs `run-publish-pending-linkedin-variants.sh` without flags
- **THEN** the request is sent with `dry_run: true` and no LinkedIn API call occurs

#### Scenario: Real mode preflights enablement

- **WHEN** the operator runs the script with `--real` and the server env file does not set `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`
- **THEN** the script fails with remediation guidance before sending a real request and prints no secrets

### Requirement: Manual inactive publish-pending n8n workflow

The repository MUST provide `n8n/workflows/silverman-blog-linkedin-publish-pending.json` as a manual-trigger workflow that orchestrates only worker HTTP calls (health check then `POST /publish-linkedin-due-variants` with `auto_queue_pending: true`), consistent with ADR-0001.

The repo export MUST have `"active": false`.

The repo export's default configuration MUST set `dry_run` `true`; real publication requires an explicit operator edit at execution time (worker enablement and dry-run guards still apply).

The workflow MUST NOT use n8n Execute Command nodes.

Importing this workflow MUST NOT be represented as unattended production automation; activation as a scheduled production workflow requires separate explicit approval outside this change.

#### Scenario: Repo export remains inactive

- **WHEN** the publish-pending workflow JSON is inspected in the repository
- **THEN** `active` is `false`, the default configuration sets `dry_run` `true`, and all nodes are HTTP/logic nodes with no Execute Command usage

#### Scenario: Workflow orchestrates worker HTTP only

- **WHEN** the publish-pending workflow runs manually against the worker
- **THEN** publication side effects occur only through `POST /publish-linkedin-due-variants` with the worker enforcing dry-run, enablement, and eligibility guards

### Requirement: HTTP endpoint POST /cancel-linkedin-publication

The worker SHALL expose `POST /cancel-linkedin-publication` with API key authentication.

Request body MUST include `campaign_id`, `variant`, optional `dry_run` (default `true`).

#### Scenario: Cancel endpoint defaults to dry-run

- **WHEN** cancel request omits `dry_run`
- **THEN** worker validates without mutating `publish_state`

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
- `linkedin_publish_retry_limit_exhausted`
- `linkedin_publish_recovery_confirmation_required`
- `linkedin_publish_recovery_confirmation_invalid`
- `linkedin_publish_content_correction_required`
- `linkedin_publish_recovery_evidence_invalid`
- `linkedin_oauth_token_missing`
- `linkedin_oauth_refresh_failed`
- `linkedin_oauth_reauthorization_required`

#### Scenario: Stable error codes in response

- **WHEN** a known eligibility, configuration, or recovery failure occurs
- **THEN** `errors[]` contains the documented stable code string
### Requirement: Safety and orchestration boundaries

All LinkedIn publication endpoints MUST default to `dry_run: true`.

This capability MUST NOT activate n8n workflows, cron jobs, or automatic publication when `scheduled_at_utc` or `publish_after_utc` elapses without an explicit HTTP request.

The repository MAY contain manual, inactive n8n workflow exports for LinkedIn publication orchestration (`"active": false`, HTTP-only per ADR-0001); providing or updating such exports MUST NOT activate them, and activation as scheduled production automation requires separate explicit approval.

No LinkedIn API call MUST occur unless `dry_run` is false, publication is enabled, credentials are valid, member URN is present, and variant is eligible (due or `publish_now`).

Operator review UI is out of scope; cancel endpoint is the v1 pre-publish escape hatch.

#### Scenario: No automatic trigger on schedule

- **WHEN** this change is applied
- **THEN** no background job publishes variants when `scheduled_at_utc` or `publish_after_utc` passes without operator or future orchestration calling publish-due

#### Scenario: Inactive workflow export does not publish

- **WHEN** the publish-pending workflow export exists in the repository with `active` false
- **THEN** no publication occurs unless an operator or approved orchestration explicitly executes the workflow or calls the worker endpoint

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
### Requirement: LinkedIn publication smoke script

The repository MUST provide `deploy/server/run-linkedin-publication-smoke.sh` that:

- defaults to dry-run for all steps
- exercises queue and publish-due dry-run paths (and optionally cancel dry-run)
- supports explicit real mode flags requiring `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`
- never prints secrets
- reports variant `publish_state` before and after each step

This smoke capability belongs to `linkedin-publication-integration`, not Flow A Core smoke.

#### Scenario: Smoke dry-run queue and publish-due

- **WHEN** smoke script runs without real flags
- **THEN** it calls queue and publish-due with `dry_run: true` without requiring LinkedIn credentials

#### Scenario: Smoke real mode gated

- **WHEN** smoke runs real publish without publication enabled
- **THEN** script reports failure with remediation and does not print tokens

### Requirement: Evidence collector LinkedIn state display

The repository MUST extend `deploy/server/collect-flow-a-smoke-evidence.sh` to optionally report per-variant LinkedIn publication state counts when campaign metadata includes `variants[]` with `publish_state`.

When reported, the summary MUST include counts for `pending`, `queued`, `published`, `failed`, and `cancelled` where present.

This informational display MUST NOT change Flow A Core PASS semantics (`distribution_scheduled` with `linkedin_distribution`).

#### Scenario: Evidence shows queued variants

- **WHEN** evidence collection runs for a campaign with one `queued` and three `pending` variants
- **THEN** script reports queued count 1 and pending count 3 without variant body text

#### Scenario: Flow A Core PASS unchanged

- **WHEN** evidence collection passes worker, public blog, and n8n checks with `distribution_scheduled`
- **THEN** `OVERALL: PASS` is reported even when all variants remain `pending` or `queued`

### Requirement: Operator documentation

Documentation MUST describe:

- LinkedIn Developer App, OAuth authorization flow, and token store (primary production path per `linkedin-oauth-token-lifecycle`)
- Required scopes `openid`, `profile`, `w_member_social` and member URN from OAuth/OIDC
- Manual env/Postman token as fallback only
- Queue → safety delay → publish-due two-step workflow; cancel before publish
- Default safety delay 120 minutes; future immediate mode via config `0` or `publish_now`
- Personal-profile text post only (commentary with variant text + URL); no image or company page
- Separation from Flow A Core; worker-side scheduling only
- Future operator UI need (out of scope v1)

#### Scenario: Two-step workflow documented

- **WHEN** operator reads LinkedIn publication docs
- **THEN** they find queue and publish-due as separate steps with safety delay and cancel guidance, and OAuth as primary credential path

### Requirement: Token provider integration for publication

Before any real LinkedIn API publication call, the publish-due service MUST resolve credentials through the token provider defined in `linkedin-oauth-token-lifecycle`.

Dry-run publish-due MUST NOT invoke token refresh or LinkedIn OAuth endpoints.

#### Scenario: Dry-run does not refresh tokens

- **WHEN** publish-due runs with `dry_run` true
- **THEN** token provider refresh and LinkedIn OAuth token endpoint are not called

### Requirement: US-003 operational validation script reference

The repository MUST provide `deploy/server/run-us003-linkedin-publication-validation-smoke.sh` as the canonical controlled-validation entry point for first real LinkedIn publication (backlog **BL-002**).

This script MUST compose the existing publication endpoints (`POST /queue-linkedin-publication`, `POST /publish-linkedin-due-variants`) and MUST NOT bypass HTTP auth, dry-run defaults in generic smoke, or publication enablement guards.

Generic `deploy/server/run-linkedin-publication-smoke.sh` remains the lower-level endpoint exerciser; US-003 script adds preflight, idempotency rerun, safeguard restoration checklist, and Phase 3 evidence hooks.

#### Scenario: US-003 script uses publication endpoints

- **WHEN** operator runs US-003 controlled validation
- **THEN** real publish path invokes worker HTTP endpoints only (ADR-0001), not direct module imports or n8n Execute Command

#### Scenario: Generic smoke remains dry-run default

- **WHEN** operator runs `run-linkedin-publication-smoke.sh` without real flags
- **THEN** behavior is unchanged — dry-run queue and publish-due with no LinkedIn API calls

### Requirement: Idempotent published variant on repeat publish-due

When `POST /publish-linkedin-due-variants` runs with `dry_run: false` for a variant already in `publish_state` `published` with a stored `linkedin_post_urn`, the worker MUST:

- NOT call LinkedIn publication API again;
- return a completed outcome indicating already published (stable code or status field documented for operators);
- preserve existing `linkedin_post_urn` and `published_at` in campaign metadata;
- NOT transition variant to `failed`.

Evidence preservation MUST hold under every request combination, including `publish_now: true` and `auto_queue_pending: true`: the stored `linkedin_post_urn` and `published_at` values are unchanged after the repeat run, and no queue metadata is rewritten for the published variant.

This requirement defines observable idempotency evidence for already-completed publications only. Recoverable/non-recoverable failure classification, retry limits, token renewal, and duplicate prevention after timeouts or uncertain API outcomes are **BL-008** and are not governed by this requirement.

#### Scenario: Repeat real publish-due for published variant

- **WHEN** publish-due runs with `dry_run: false` for a variant with `publish_state` `published` and existing `linkedin_post_urn`
- **THEN** no LinkedIn API call occurs, response indicates already published, and metadata URN is unchanged

#### Scenario: US-003 script asserts idempotency

- **WHEN** US-003 validation script runs repeat publish-due after successful first publish
- **THEN** script treats no-op idempotent response as pass for duplicate-prevention evidence

#### Scenario: Repeat combined run preserves evidence byte-for-byte

- **WHEN** a real run with `auto_queue_pending` true is repeated after a variant was published by an earlier run
- **THEN** the published variant's stored `linkedin_post_urn` and `published_at` are identical before and after the repeat run, the auto-queue phase reports it skipped with `linkedin_publish_auto_queue_skipped_state` with the preserved `linkedin_post_urn` and `published_at` in its `auto_queue_results` entry, and no LinkedIn API call occurs for it

#### Scenario: publish_now does not bypass already-published protection

- **WHEN** publish-due runs with `dry_run: false` and `publish_now: true` for a `published` variant
- **THEN** no LinkedIn API call occurs and the stored `linkedin_post_urn` and `published_at` are preserved

### Requirement: Operator documentation for first real publish validation

Operator documentation MUST describe the US-003 controlled validation procedure including:

- prerequisites (OAuth token store, member URN, publication flag enablement window);
- selection of one approved variant;
- queue → `publish_now` publish-due sequence;
- idempotency verification;
- manual LinkedIn visibility confirmation;
- mandatory restoration of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` after validation;
- reference to Phase 3 evidence report location.

Documentation MUST distinguish **implemented** LinkedIn publication from **operationally validated** publication per `docs/CURRENT-STATE.md` completion layers.

#### Scenario: Operator finds US-003 runbook

- **WHEN** operator reads LinkedIn publication deployment documentation
- **THEN** they find the US-003 script path, enablement window rules, and safeguard restoration steps

### Requirement: Correct LinkedIn variant service

The worker SHALL expose a correction service entry point that updates the variant draft artifact and metadata while `publish_state` is `pending`, and additionally while `publish_state` is `failed` only for latest evidence `linkedin_publish_content_invalid`.

Correction MUST write `linkedin-posts/generated/<campaign_id>/<variant_id>.md` atomically, update `derivative_content_sha256`, and append an entry to `operator_supervision.edit_history`.

For `pending`, correction MUST preserve existing behavior: set `operator_supervision.last_action` to `edit`, `operator_supervision.phase` to `pre_queue`, set `auto_queue_eligible` true unless explicitly false, make no LinkedIn call, and leave state `pending`.

For eligible `failed`, correction MUST first normalize legacy attempt evidence if needed, preserve `publish_state=failed` and all publication evidence, set a recovery-phase supervision action, and append `content_corrected` recovery evidence with source attempt number and previous/new hashes. It MUST NOT make the variant auto-queue eligible, call LinkedIn, or authorize another attempt.

Failed correction for any other US-021 class MUST be rejected with a stable supervision action error and no mutation.

#### Scenario: Correct pending variant updates artifact and hash

- **WHEN** correction runs with `dry_run` false for a pending variant with new content
- **THEN** existing artifact/hash, supervision history, and pending-state behavior are preserved

#### Scenario: Correct content-invalid failed variant

- **WHEN** correction runs with `dry_run` false for a failed variant whose latest evidence is `linkedin_publish_content_invalid`
- **THEN** artifact and hash change atomically, original attempt evidence is retained, correction evidence is appended, state remains `failed`, and explicit manual queue is still required

#### Scenario: Correction rejected for queued variant

- **WHEN** correction is requested for a `queued` variant
- **THEN** operation fails with `linkedin_supervision_variant_not_pending` and artifact and metadata are unchanged

#### Scenario: Correction rejected for other failed class

- **WHEN** correction is requested for a failed variant not classified content-invalid/non-recoverable-as-is
- **THEN** operation fails with `linkedin_supervision_action_not_allowed` and artifact and metadata are unchanged

### Requirement: Defer LinkedIn variant service

The worker SHALL expose a defer service entry point (for example `defer_linkedin_variant(base_path, *, campaign_id, variant, new_scheduled_at_utc, dry_run=True, reason=None, idempotency_key=None, ...)`) that reschedules a `pending` variant.

Defer MUST update variant `scheduled_at_utc` to `new_scheduled_at_utc` (UTC ISO8601).

Defer MUST require `new_scheduled_at_utc` to be strictly after current UTC time.

Defer MUST append an entry to `operator_supervision.deferral_history` with previous and new schedule timestamps.

Defer MUST set `operator_supervision.last_action` to `defer`, `operator_supervision.phase` to `pre_queue`, and `operator_supervision.auto_queue_eligible` to `false`.

Defer MUST NOT change `publish_state` from `pending`.

Defer MUST NOT call LinkedIn API.

#### Scenario: Defer pending variant updates schedule

- **WHEN** defer runs with `dry_run` false for a `pending` variant with valid future `new_scheduled_at_utc`
- **THEN** `scheduled_at_utc` is updated, `deferral_history` records the change, and `auto_queue_eligible` is `false`

#### Scenario: Defer rejected for past timestamp

- **WHEN** defer is requested with `new_scheduled_at_utc` not in the future
- **THEN** the operation fails with `linkedin_supervision_defer_time_invalid` and schedule is unchanged

### Requirement: HTTP endpoint POST /correct-linkedin-variant

The worker SHALL expose `POST /correct-linkedin-variant` with API key authentication.

Request body MUST include `campaign_id`, `variant`, `draft_content`, optional `dry_run` (default `true`), optional `reason`, and optional `idempotency_key`.

#### Scenario: Correct endpoint defaults to dry-run

- **WHEN** correction request omits `dry_run`
- **THEN** worker validates without mutating artifact or metadata

### Requirement: HTTP endpoint POST /defer-linkedin-variant

The worker SHALL expose `POST /defer-linkedin-variant` with API key authentication.

Request body MUST include `campaign_id`, `variant`, `new_scheduled_at_utc`, optional `dry_run` (default `true`), optional `reason`, and optional `idempotency_key`.

#### Scenario: Defer endpoint defaults to dry-run

- **WHEN** defer request omits `dry_run`
- **THEN** worker validates without mutating `scheduled_at_utc` or metadata

### Requirement: Supervision idempotency and dry-run defaults

Correction, defer, and cancel supervision operations MUST default `dry_run` to `true`.

When `idempotency_key` is provided and a prior successful non-dry-run operation used the same key with identical payload, replay MUST return `completed` without duplicate history entries.

When `idempotency_key` is provided but payload differs from the stored proof, the operation MUST fail with a stable validation error.

#### Scenario: Idempotent defer replay

- **WHEN** defer is called twice with `dry_run` false, the same `idempotency_key`, and identical `new_scheduled_at_utc`
- **THEN** the second call returns `completed` without a second `deferral_history` entry

### Requirement: Stable error codes for supervision

Supervision operations MUST use stable error codes including at minimum:

- `linkedin_supervision_variant_not_pending`
- `linkedin_supervision_action_not_allowed`
- `linkedin_supervision_defer_time_invalid`
- `linkedin_supervision_edit_unchanged`
- `linkedin_supervision_idempotency_conflict`

Existing publication error codes (`linkedin_publish_cancel_not_allowed`, `linkedin_publish_variant_not_queued` for non-cancel contexts) MUST remain stable.

#### Scenario: Supervision error codes are stable strings

- **WHEN** a supervision validation failure occurs
- **THEN** the HTTP response includes a stable machine-readable error code from the supervision set

### Requirement: Attempt counters in publication and supervision results

Queue results and each per-variant publish result MUST expose nullable additive `publication_attempt_count`, `manual_retries_used`, and `manual_retries_remaining`. Failed-state queue, correction, and cancellation results MUST additionally expose `recovery_classification` where classification evidence is valid.

Counters MUST be derived from validated attempt history (or valid normalized legacy evidence), MUST NOT count blocked/no-call operations, and MUST report zero remaining immediately after a third failed attempt. Responses MUST NOT contain secrets or variant body text.

#### Scenario: Third failure visibly exhausts retries

- **WHEN** a third real API attempt fails
- **THEN** its publish result reports attempt count 3, manual retries used 2, and manual retries remaining 0

#### Scenario: Blocked publish preserves counters

- **WHEN** a queued variant is blocked before any LinkedIn call
- **THEN** its result reports unchanged counters and no attempt entry is appended

### Requirement: US-022 behavioral test coverage

The repository MUST extend LinkedIn publication and supervision tests to cover:

- attempt history for success, API failure, transport failure, and success-without-URN;
- valid legacy failed-evidence normalization and invalid-evidence fail-closed behavior;
- two manual retries allowed, third re-queue blocked, and only real LinkedIn calls counted;
- no shared campaign retry pool and no automatic retry;
- all US-021 class confirmation/correction paths, including unlisted combinations as uncertain;
- latest and historical evidence preserved across re-queue and later outcomes;
- failed content correction remains failed and requires explicit queue;
- failed and exhausted cancellation preserves evidence;
- dry-run zero mutation, API-key auth, strict 422 request validation, stable errors, counters, and absence of secrets/body text;
- unchanged US-018, US-019, and US-020 behavior.

#### Scenario: Focused and regression tests pass

- **WHEN** the US-022 implementation is verified
- **THEN** focused publication/supervision tests and the existing full test suite pass without weakened BL-007 assertions or new warnings
