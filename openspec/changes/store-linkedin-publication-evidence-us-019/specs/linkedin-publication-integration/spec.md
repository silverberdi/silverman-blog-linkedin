# Delta: linkedin-publication-integration (store-linkedin-publication-evidence-us-019)

US-019 (BL-007 story 2): formalize complete publication evidence, operator-readable failure taxonomy, and observable idempotency. This delta MODIFIES existing requirements additively (full blocks copied) and ADDS one requirement. It does not change the `publish_state` state machine and renames no fields; the only touch to the US-018 auto-queue contract is additive — optional `linkedin_post_urn` / `published_at` evidence fields on `auto_queue_results` entries.

## ADDED Requirements

### Requirement: No automatic retry within publication execution

The publication execution capability MUST NOT automatically retry a failed real LinkedIn API attempt — not within the same request, not via background jobs, and not by automatically re-queueing `failed` variants.

The `retryable` field recorded in failure context is descriptive evidence only. No retry behavior, recoverable/non-recoverable classification, token-renewal-on-failure behavior, or timeout-duplicate mitigation is derived from it by this capability.

Normative boundary: retry limits, recoverable/non-recoverable classification rules, token-renewal behavior, duplicate prevention after timeouts or uncertain outcomes, and preservation of attempt history across manual re-queues are **BL-008** concerns and are explicitly out of scope for this capability. Manual re-queue of a `failed` variant via `POST /queue-linkedin-publication` remains the only retry path. The behavior of stored evidence after such a manual re-queue (preservation, clearing, or attempt history) is EXPLICITLY out of scope of US-019 and is a BL-008 normative decision; US-019 neither authorizes nor prohibits evidence loss in that case.

#### Scenario: Failed real attempt is not retried in the same request

- **WHEN** a real publish-due attempt calls the LinkedIn API for a variant and the API returns a failure
- **THEN** the variant becomes `failed`, exactly one LinkedIn API call was made for that variant in that request, and no automatic retry occurs

#### Scenario: Failed variant excluded from automatic paths

- **WHEN** a later publish-due request runs (with or without `auto_queue_pending`) over a campaign containing a `failed` variant
- **THEN** the `failed` variant is not published and not auto-queued; only explicit manual re-queue via `POST /queue-linkedin-publication` can make it eligible again

## MODIFIED Requirements

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
- `retryable` — boolean, recorded as descriptive evidence only (**mandatory**; interpretation is BL-008)
- `http_status` — **mandatory but nullable**: null when no HTTP response was received (transport-level failure)

`http_status` is a MANDATORY field inside `linkedin_publication` in both success and failure evidence after a real attempt: numeric whenever an HTTP response was received, `null` only when none was (transport-level failure).

Content rejection by LinkedIn MUST be recorded with the dedicated stable code `linkedin_publish_content_invalid`, distinct from the generic `linkedin_publish_api_error`.

Campaign metadata and HTTP responses MUST NOT include variant body text.

#### Scenario: Queue writes publication metadata

- **WHEN** real queue succeeds
- **THEN** variant records `publication_queued_at`, `publish_after_utc`, `publication_mode`, and `publication_safety_delay_minutes`

#### Scenario: Publish writes URN without body text

- **WHEN** real publish succeeds
- **THEN** variant records `linkedin_post_urn`, `published_at`, and `linkedin_publication` without artifact body text in metadata or HTTP response

#### Scenario: Complete evidence after real successful publish

- **WHEN** a real publish succeeds for a variant
- **THEN** variant metadata contains non-empty `linkedin_post_urn`, UTC `published_at`, and `linkedin_publication` with `provider`, `post_urn`, `published_at`, and `http_status`, and `linkedin_publication.post_urn` equals `linkedin_post_urn`

#### Scenario: Failure context shape after real API failure

- **WHEN** a real publish attempt receives a LinkedIn API error response
- **THEN** variant `publish_state` becomes `failed` and `linkedin_publication` contains `last_error_code`, `last_failed_at`, `retryable`, and the numeric `http_status`, with no secrets, body text, or raw API response bodies

#### Scenario: Content rejection records dedicated stable code

- **WHEN** a real publish attempt receives a LinkedIn API response rejecting the post content
- **THEN** variant `publish_state` becomes `failed` and `linkedin_publication.last_error_code` is `linkedin_publish_content_invalid` (not the generic `linkedin_publish_api_error`), with the numeric `http_status` recorded

#### Scenario: Transport failure records null http_status

- **WHEN** a real publish attempt fails at transport level without receiving an HTTP response
- **THEN** variant `publish_state` becomes `failed` and `linkedin_publication` records `last_error_code`, `last_failed_at`, `retryable`, and `http_status` null

#### Scenario: Success without post identifier treated as failure

- **WHEN** a real publish attempt receives an API success response without a usable post identifier
- **THEN** the attempt is recorded as failed with `linkedin_publish_api_error` and the variant does not become `published` with missing `linkedin_post_urn`

### Requirement: Publish due variants service

The worker SHALL expose a publish-due service entry point (for example `publish_linkedin_due_variants(base_path, *, campaign_id=None, variant=None, dry_run=True, publish_now=False, ...)`) that publishes eligible `queued` variants to LinkedIn when due.

Real LinkedIn API calls MUST require `dry_run` false, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`, and a valid access token and member URN resolved through the token provider (or documented env fallback).

The service MUST read variant text from `artifact_relative_path` and include `source_public_url` in commentary (text post format).

The service MUST NOT upload images or publish to company pages.

On real API success, variant MUST become `published`. On real API failure or content rejection, variant MUST become `failed`.

Configuration errors and OAuth `action_required` results from the token provider MUST NOT mark variant `failed`.

**Failure taxonomy (normative consolidation):** variant `publish_state` becomes `failed` only after a real LinkedIn API attempt — API error response (including token invalid/expired, insufficient permission, content rejection, API error), transport-level failure during the call, or success response without a usable post identifier. Blocked conditions fail the HTTP response with a stable code but MUST leave `publish_state` unchanged: publication not enabled (`linkedin_publish_not_enabled`), OAuth reauthorization required (`linkedin_oauth_reauthorization_required` or related), missing member URN (`linkedin_publish_member_urn_missing`), missing token (`linkedin_publish_token_missing`), and dry-run.

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

### Requirement: Auto-queue outcome visibility

When `auto_queue_pending` is `true`, the response MUST include operator-understandable per-variant results covering both phases:

- variants queued by the auto-queue phase (with resulting `publish_state` and `publish_after_utc`)
- variants published, already published, or failed by the publish phase (existing publish-due result semantics)
- variants skipped, with stable machine-readable reasons distinguishing at minimum: not due per schedule, supervision-excluded (cancelled or `auto_queue_eligible` `false`), not in an auto-queueable `publish_state`, and campaign-level ineligibility

Stable reason/warning codes MUST include at minimum:

- `linkedin_publish_auto_queue_skipped_not_due`
- `linkedin_publish_auto_queue_skipped_supervision`
- `linkedin_publish_auto_queue_skipped_state`

When a variant results `published` or already-published within the auto-queue operation — including the cross-campaign scan without `campaign_id` — its `auto_queue_results` entry MUST include `linkedin_post_urn` and `published_at` (additive optional fields on the existing result shape; absent or null for entries with no publication evidence).

Responses MUST NOT include variant body text or secret values.

#### Scenario: Skip reasons visible per variant

- **WHEN** publish-due runs with `auto_queue_pending` true over a campaign with one due eligible variant, one future-scheduled variant, and one cancelled variant
- **THEN** the response reports the first as queued (and published or queued-not-due per publish rules), the second skipped with `linkedin_publish_auto_queue_skipped_not_due`, and the third skipped with `linkedin_publish_auto_queue_skipped_supervision`

#### Scenario: No secrets or body text in combined response

- **WHEN** the combined auto-queue and publish operation completes or fails
- **THEN** the HTTP response contains no token values and no variant body text

#### Scenario: Auto-queue results carry evidence for published outcomes

- **WHEN** a real combined run with `auto_queue_pending` true results in a variant `published`, or encounters a variant already `published` with stored evidence
- **THEN** that variant's `auto_queue_results` entry includes non-null `linkedin_post_urn` and `published_at`

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

OAuth lifecycle tests belong to `linkedin-oauth-token-lifecycle` but publication integration tests MUST cover provider `action_required` behavior.

#### Scenario: Test module passes

- **WHEN** `pytest` runs after apply
- **THEN** `tests/test_linkedin_publication.py` passes
