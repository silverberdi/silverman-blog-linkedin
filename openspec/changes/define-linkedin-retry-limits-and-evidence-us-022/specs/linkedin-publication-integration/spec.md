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

## ADDED Requirements

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
