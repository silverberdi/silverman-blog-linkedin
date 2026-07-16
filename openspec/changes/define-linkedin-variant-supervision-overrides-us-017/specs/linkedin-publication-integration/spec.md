## MODIFIED Requirements

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

### Requirement: Cancel publication service

The worker SHALL expose a cancel service entry point (for example `cancel_linkedin_publication(base_path, *, campaign_id, variant, dry_run=True, ...)`) that transitions `queued` → `cancelled` and `pending` → `cancelled`.

Cancel from `pending` MUST record `operator_supervision` cancellation audit with `phase` `pre_queue`.

Cancel from `queued` MUST record `operator_supervision` cancellation audit with `phase` `post_queue` (or preserve existing `linkedin_publication.cancelled_at` alongside `operator_supervision`).

Cancel MUST set `operator_supervision.auto_queue_eligible` to `false` when persisting cancellation.

Cancel MUST NOT affect `published` variants.

Cancel MUST NOT call LinkedIn API.

#### Scenario: Cancel queued variant

- **WHEN** cancel runs with `dry_run` false for a `queued` variant
- **THEN** variant `publish_state` becomes `cancelled`

#### Scenario: Cancel pending variant during supervision

- **WHEN** cancel runs with `dry_run` false for a `pending` variant
- **THEN** variant `publish_state` becomes `cancelled` and `operator_supervision.cancellation.phase` is `pre_queue`

#### Scenario: Cancel rejected for published

- **WHEN** cancel is requested for a `published` variant
- **THEN** the operation fails with `linkedin_publish_cancel_not_allowed` and variant remains `published`

### Requirement: Campaign eligibility

Queue, publish-due, and cancel MUST require campaign metadata at `metadata/campaigns/<campaign-id>.json`, `flow` `flow_a`, and campaign `state` `distribution_scheduled`.

Queue MUST require variant `publish_state` `pending` (or `failed` when re-queue retry is supported).

Publish-due MUST require variant `publish_state` `queued`.

Cancel MUST require variant `publish_state` `queued` or `pending`.

Artifact existence and hash verification MUST match distribution scheduling rules before queue or publish.

#### Scenario: Cancel pending requires distribution_scheduled campaign

- **WHEN** cancel is requested for a `pending` variant on a `distribution_scheduled` Flow A campaign
- **THEN** the operation is eligible for validation or execution per `dry_run`

## ADDED Requirements

### Requirement: Correct LinkedIn variant service

The worker SHALL expose a correction service entry point (for example `correct_linkedin_variant(base_path, *, campaign_id, variant, draft_content, dry_run=True, reason=None, idempotency_key=None, ...)`) that updates the variant draft artifact and metadata while `publish_state` is `pending`.

Correction MUST write `linkedin-posts/generated/<campaign_id>/<variant_id>.md` atomically.

Correction MUST update `derivative_content_sha256` to match the new artifact content.

Correction MUST append an entry to `operator_supervision.edit_history`.

Correction MUST set `operator_supervision.last_action` to `edit` and `operator_supervision.phase` to `pre_queue`.

Correction MUST set `operator_supervision.auto_queue_eligible` to `true` unless the request explicitly sets it `false`.

Correction MUST NOT call LinkedIn API.

Correction MUST NOT change `publish_state` from `pending`.

#### Scenario: Correct pending variant updates artifact and hash

- **WHEN** correction runs with `dry_run` false for a `pending` variant with new `draft_content`
- **THEN** the draft file is updated, `derivative_content_sha256` matches the new content, and `operator_supervision.edit_history` records previous and new hashes

#### Scenario: Correction rejected when not pending

- **WHEN** correction is requested for a `queued` variant
- **THEN** the operation fails with `linkedin_supervision_variant_not_pending` and artifact and metadata are unchanged

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
