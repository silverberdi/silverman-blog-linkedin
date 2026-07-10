## MODIFIED Requirements

### Requirement: Campaign metadata required fields

Each campaign metadata document MUST include at minimum:

- `campaign_id`, `flow`, `state`, `created_at`, `updated_at`
- `source_slug`, `public_slug`, `source_relative_path`, `image_relative_path`
- `source_content_sha256`, `publication_date`
- `source_public_url` (nullable until publish-confirmed)
- `blog_publish` (object with idempotency key and publish status)
- `variants` (array of derivative variant records)
- `state_history` (array of transition records)
- `errors` and `warnings` (arrays)

After successful Flow A source lifecycle completion, the document MUST also include:

- `original_source_relative_path` (immutable ready-folder path once set)
- `processed_source_relative_path` (processed-folder path after move)
- `original_image_relative_path` and `processed_image_relative_path` when a companion image was moved

After queue acceptance (canonical spec `flow-a-operational-queue-lifecycle`), the document MUST also include when applicable:

- `queued_source_relative_path` and optional `queued_image_relative_path`
- `queued_at` and `last_transition_at`

After error-folder placement, the document MUST also include when applicable:

- `error_source_relative_path` and optional `error_image_relative_path`

The document MUST include `source_file_status` with physical `location`, logical `execution_state`, optional execution attempt fields, `recovery_classification` (canonical enum), and `last_error` when set.

`source_slug` and `public_slug` MUST remain unchanged by physical collision suffixes in `processed/` or `error/`.

#### Scenario: Initial campaign document shape

- **WHEN** a Flow A campaign is created for a ready post
- **THEN** all required top-level fields are present, `state` is `ready`, `variants` is an array (possibly empty), and `state_history` contains the initial transition

#### Scenario: Source fingerprint recorded without body

- **WHEN** campaign metadata is created from source Markdown bytes
- **THEN** `source_content_sha256` is a hex SHA-256 digest of the source content and no Markdown body field is stored in the campaign document

#### Scenario: Lifecycle completion adds path traceability fields

- **WHEN** Flow A source lifecycle completes successfully
- **THEN** campaign metadata includes `original_source_relative_path`, `processed_source_relative_path`, and optional image path fields while retaining `source_content_sha256`

#### Scenario: Queue acceptance adds queued path fields

- **WHEN** queue acceptance succeeds for a Flow A source
- **THEN** campaign metadata includes `queued_source_relative_path`, `queued_at`, `source_file_status.location` `queued`, and `execution_state` `idle`

### Requirement: Source file marking policy

Flow A source files SHALL be marked via `source_file_status`:

- `location` values: `ready`, `queued`, `processed`, `error` (physical folder semantics)
- `execution_state` values: `idle`, `processing`, `stale` (logical execution semantics; meaningful when `location` is `queued`)
- `marked_processed_at` and `marked_error_at` timestamps
- `physical_move_completed_at` when physical move to `processed/` succeeds
- `physical_move_state` values: `none`, `completed`, `partial`, `failed` (when applicable)
- `recovery_classification` when a recovery action is known (canonical enum: `no_action`, `retryable`, `repair_required`, `requeue_required`, `manual_intervention_required`)
- `last_error` object when the most recent operational failure is recorded

Physical moves from `blog-posts/queued/` to `blog-posts/processed/` are performed by canonical spec `flow-a-source-lifecycle-completion` after successful distribution scheduling. Queue acceptance per `flow-a-operational-queue-lifecycle` performs physical moves from `blog-posts/ready/` to `blog-posts/queued/`.

Deterministic non-retryable failures before durable external side effects after queue acceptance MUST perform physical moves to `blog-posts/error/` per `flow-a-operational-queue-lifecycle`. Post-side-effect failures normally remain in `queued/` with `repair_required`.

#### Scenario: Validation failure marks error in metadata

- **WHEN** deterministic editorial validation fails for a queued Flow A campaign and error-folder policy applies
- **THEN** `source_file_status.location` becomes `error`, `marked_error_at` is set, physical files exist under `blog-posts/error/` when move succeeds, and `last_error` records the failure category

#### Scenario: Lifecycle completion marks processed in metadata and on disk

- **WHEN** Flow A source lifecycle completes successfully
- **THEN** `source_file_status.location` becomes `processed`, `execution_state` becomes `idle`, `marked_processed_at` and `physical_move_completed_at` are set, source files exist under `blog-posts/processed/`, and campaign `state` is `flow_a_complete`

## ADDED Requirements

### Requirement: Operational execution attempt metadata

`source_file_status` MUST support execution attempt fields: `execution_attempt_id`, `attempt_count`, `processing_claimed_at`, `processing_started_at`, `last_progress_at`, and `processing_lease_expires_at`.

`processing_lease_expires_at` MUST be a derived convenience field equal to `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`, updated together with `last_progress_at`.

These fields MUST be set when `execution_state` transitions to `processing` and MUST be used for stale detection per `flow-a-operational-queue-lifecycle` using `last_progress_at` as the canonical clock.

#### Scenario: Processing claim records attempt metadata

- **WHEN** Flow A execution claims a queued campaign
- **THEN** `execution_attempt_id` is non-empty, `attempt_count` increments, `last_progress_at` is set, and `processing_lease_expires_at` equals `last_progress_at` plus configured stale seconds

#### Scenario: Stale detection uses last_progress_at

- **WHEN** stale detection runs for a campaign with `execution_state=processing`
- **THEN** staleness is determined from `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` and not from an independently maintained lease value

### Requirement: Legacy campaign compatibility for queue fields

When `queued_source_relative_path` is absent and `source_file_status.location` is `processed`, workers MUST resolve active source paths from `processed_source_relative_path` without requiring queue metadata.

When `queued_source_relative_path` is absent and source files remain only in `blog-posts/ready/`, the next real Flow A execution MUST perform queue acceptance before publish.

#### Scenario: Legacy processed campaign resolves without queue paths

- **WHEN** campaign metadata from before queue lifecycle has `processed_source_relative_path` and no `queued_source_relative_path`
- **THEN** downstream services resolve the processed path and idempotent operations succeed
