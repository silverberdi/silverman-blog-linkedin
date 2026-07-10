# flow-a-lifecycle

## Purpose

Campaign metadata schema, Flow A lifecycle state machine, state history, idempotency keys for blog publish / LinkedIn derivative variants / schedule slots, canonical variant ID validation, metadata body exclusion, and metadata-only source file marking for the `silverman-blog-linkedin` worker. Implements child slice 2 under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`.

## Requirements

### Requirement: Umbrella and editorial policy references

This child change SHALL implement Flow A lifecycle and duplicate-prevention foundation under active umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap`.

Campaign metadata and lifecycle rules MUST align with Flow A vs Flow B policy documented in canonical spec `editorial-canon` and artifact `content-strategy/silverman-editorial-system.md`.

Flow A campaigns MUST record `flow: flow_a`. Flow B (`flow_b`) MAY be reserved in enums and guardrails but MUST NOT enter Flow A automatic publish paths.

This change MUST NOT parse or apply editorial canon content at runtime.

#### Scenario: Flow A campaign records flow field

- **WHEN** a new Flow A campaign metadata document is created for a user-provided ready post
- **THEN** the document includes `flow` with value `flow_a`

#### Scenario: Flow B blocked from Flow A automatic transitions

- **WHEN** lifecycle transition helpers are invoked for a campaign with `flow` `flow_b`
- **THEN** the operation is rejected with machine-readable error code `flow_b_not_eligible_for_flow_a`

### Requirement: Campaign metadata storage path

The system SHALL persist per-campaign lifecycle metadata at `metadata/campaigns/<campaign-id>.json` relative to the editorial base path.

The worker MUST verify `metadata/campaigns/` exists, is a directory, and is writable before writing campaign metadata (same readiness posture as `metadata/runs/`).

#### Scenario: Campaign file path is deterministic

- **WHEN** campaign ID is `flow-a-2026-07-06-why-i-did-not-start-with-the-database`
- **THEN** the relative metadata path is `metadata/campaigns/flow-a-2026-07-06-why-i-did-not-start-with-the-database.json`

#### Scenario: Campaigns folder not ready

- **WHEN** `metadata/campaigns/` is missing or not writable
- **THEN** campaign metadata write returns a structured result with `written: false` and error code `metadata_campaigns_not_ready` or `metadata_campaigns_not_writable` without creating a partial file

#### Scenario: Campaign metadata write returns structured result

- **WHEN** `write_campaign_metadata` completes (success or failure)
- **THEN** the caller receives a `CampaignMetadataWriteResult` with `written` boolean and optional `error_code` (`invalid_campaign_id`, `metadata_campaigns_not_ready`, `metadata_campaigns_not_writable`, or `campaign_metadata_write_failed`)

### Requirement: Campaign ID format

Campaign IDs MUST be stable across reruns and safe as single path segments.

For Flow A, campaign ID format MUST be `flow-a-<publication-date>-<public-slug>` where:

- `<publication-date>` is `YYYY-MM-DD` from the post's `publication_date`
- `<public-slug>` is the derived public slug after numeric ordering prefix strip (aligned with `github-pages-blog-publishing` public slug rules)
- The ID MUST contain only lowercase letters, digits, and hyphens (no `/`, `\`, `..`, or spaces)

Canonical example:

- `campaign_id`: `flow-a-2026-07-06-why-i-did-not-start-with-the-database`
- `source_slug`: `01-why-i-did-not-start-with-the-database`
- `public_slug`: `why-i-did-not-start-with-the-database`

#### Scenario: Canonical campaign ID generation

- **WHEN** generating a campaign ID for Flow A with `publication_date` `2026-07-06` and `public_slug` `why-i-did-not-start-with-the-database`
- **THEN** the campaign ID is `flow-a-2026-07-06-why-i-did-not-start-with-the-database`

#### Scenario: Unsafe slug rejected in campaign ID

- **WHEN** `public_slug` contains path separators or uppercase characters
- **THEN** campaign ID generation fails with a machine-readable validation error

#### Scenario: Invalid persisted campaign ID rejected before path resolution

- **WHEN** `campaign_metadata_relative_path`, `write_campaign_metadata`, or `read_campaign_metadata` is called with an invalid campaign ID (for example `../evil`, `random-file`, or uppercase slug segments)
- **THEN** path helpers raise `invalid_campaign_id`, write returns `written: false` with `error_code` `invalid_campaign_id`, and read returns `None` without attempting filesystem access

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

### Requirement: Metadata body exclusion

Campaign metadata MUST NOT store full content bodies.

Persisted campaign JSON MUST NOT include `markdown_content`, `generated_draft_content`, `draft_content`, or secrets such as `api_key`.

Campaign metadata MAY store paths, hashes, statuses, schedule times, and error codes only.

#### Scenario: Sanitization strips forbidden fields

- **WHEN** a campaign metadata payload containing `markdown_content` or `generated_draft_content` is prepared for persistence
- **THEN** those fields are removed before write

#### Scenario: Variant records exclude draft body

- **WHEN** a variant entry is recorded after LinkedIn draft generation
- **THEN** the variant record includes `draft_relative_path` and `draft_content_sha256` but not the draft text body

### Requirement: Canonical LinkedIn variant IDs

The `variants[].variant` field MUST use a canonical variant ID defined in `content-strategy/silverman-editorial-system.md` (`#linkedin-derivative-package`).

Canonical variant IDs are hyphenated lowercase strings:

- `executive-recruiter`
- `technical-architect`
- `engineering-leadership`
- `short-provocative`

Snake_case aliases (for example `short_provocative`) or shortened names (for example `executive`, `technical`) MUST NOT be used in campaign metadata or idempotency keys.

New variant IDs MAY be introduced only by updating the editorial canon first; this lifecycle change does not define an independent variant vocabulary.

#### Scenario: Variant field uses canonical ID

- **WHEN** a derivative variant entry is recorded in campaign metadata
- **THEN** `variant` is one of the canonical IDs from the editorial canon (for example `executive-recruiter`)

#### Scenario: Non-canonical variant ID rejected

- **WHEN** a variant entry is prepared with `variant` `executive` or `short_provocative`
- **THEN** validation rejects the entry with a machine-readable error (for example `invalid_variant_id`)

### Requirement: Lifecycle states

Flow A lifecycle MUST support at minimum these `state` values:

`ready`, `validation_failed`, `validated`, `blog_publish_pending`, `blog_published`, `derivatives_pending`, `derivatives_generated`, `distribution_scheduled`, `distribution_complete`, `flow_a_complete`, `error`

#### Scenario: Happy-path progression

- **WHEN** a Flow A campaign advances through validation, publish, derivatives, scheduling, and completion without unrecoverable errors
- **THEN** `state` progresses through the ordered states ending at `flow_a_complete`

#### Scenario: Validation failure state

- **WHEN** automated validation fails for a Flow A ready post
- **THEN** `state` becomes `validation_failed` and the campaign records machine-readable errors

### Requirement: State transition history

Each state change MUST append a `state_history` entry with:

- `at` (UTC ISO8601 timestamp)
- `from_state` (nullable on create)
- `to_state`
- `reason` (human-readable)
- `actor` (`worker`, `n8n`, or `manual`)
- `error_code` (required when transitioning to `validation_failed` or `error` due to failure)

Failure transitions MUST also append to top-level `errors[]`.

#### Scenario: Successful transition recorded

- **WHEN** state changes from `validated` to `blog_publish_pending` with actor `worker`
- **THEN** a history entry documents `from_state`, `to_state`, `reason`, `actor`, and timestamp

#### Scenario: Failure transition requires error code

- **WHEN** state transitions to `validation_failed` or `error` because of a failure
- **THEN** the history entry includes a non-empty `error_code` and `errors[]` is updated

### Requirement: State transition enforcement

The worker lifecycle helpers MUST enforce valid state transitions for Flow A campaigns.

Invalid transitions MUST be rejected with machine-readable error `invalid_state_transition` rather than silently overwriting `state`.

#### Scenario: Invalid skip rejected

- **WHEN** a transition from `ready` directly to `blog_published` is attempted
- **THEN** the transition is rejected with `invalid_state_transition`

#### Scenario: Valid adjacent transition accepted

- **WHEN** a transition from `validated` to `blog_publish_pending` is attempted for a Flow A campaign
- **THEN** the transition succeeds and `updated_at` is refreshed

### Requirement: Blog publish idempotency key

Blog publication intent MUST use an idempotency key derived from:

- `source_slug`
- `public_slug`
- `publication_date`
- `source_content_sha256`

Key format MUST be namespaced: `blog:{source_slug}:{public_slug}:{publication_date}:{source_content_sha256}`

Future blog publish operations MUST treat an existing published target for the same key as `already_published` without overwriting.

#### Scenario: Blog key stability

- **WHEN** the same source slug, public slug, publication date, and content hash are provided
- **THEN** the generated blog publish idempotency key is identical across calls

#### Scenario: Content change produces different blog key

- **WHEN** `source_content_sha256` changes while other blog key components are unchanged
- **THEN** the blog publish idempotency key changes

### Requirement: LinkedIn derivative idempotency key

LinkedIn derivative generation MUST use an idempotency key derived from:

- `campaign_id`
- `source_content_sha256`
- `variant`
- `flow`

Key format MUST be namespaced: `derivative:{campaign_id}:{source_content_sha256}:{variant}:{flow}`

The `{variant}` segment MUST be a canonical hyphenated variant ID from the editorial canon (not a shortened or snake_case alias).

Re-runs with unchanged source content and variant MUST NOT create duplicate draft files; existing `draft_relative_path` MUST be returned or reused.

#### Scenario: Derivative key per variant

- **WHEN** generating keys for variants `executive-recruiter` and `technical-architect` on the same campaign
- **THEN** the idempotency keys differ only in the `variant` segment

#### Scenario: Derivative key example format

- **WHEN** generating a derivative idempotency key for campaign `flow-a-2026-07-06-why-i-did-not-start-with-the-database`, variant `short-provocative`, flow `flow_a`, and content hash `abc123`
- **THEN** the key is `derivative:flow-a-2026-07-06-why-i-did-not-start-with-the-database:abc123:short-provocative:flow_a`

#### Scenario: Unchanged source skips duplicate draft

- **WHEN** derivative generation is requested for an idempotency key that already has a recorded `draft_relative_path` and matching `source_content_sha256`
- **THEN** no duplicate draft file is created for that variant

### Requirement: LinkedIn publication schedule slot idempotency key

Future LinkedIn API publication MUST use a schedule slot idempotency key derived from:

- `campaign_id`
- `variant`
- `scheduled_at` (normalized UTC ISO8601)

Key format MUST be namespaced: `schedule:{campaign_id}:{variant}:{scheduled_at}`

The `{variant}` segment MUST be a canonical hyphenated variant ID from the editorial canon.

Duplicate schedule slots for the same campaign, variant, and time MUST NOT create duplicate publish intents.

#### Scenario: Schedule key normalization

- **WHEN** `scheduled_at` is provided for scheduling metadata
- **THEN** the schedule idempotency key uses UTC ISO8601 form `YYYY-MM-DDTHH:MM:SSZ`

#### Scenario: Duplicate schedule slot detected

- **WHEN** scheduling is requested for a `schedule_idempotency_key` already present on a variant
- **THEN** the operation returns an already-scheduled outcome without creating a duplicate slot

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

### Requirement: Worker lifecycle module

The worker SHALL provide a lifecycle metadata module (for example `campaign_lifecycle.py`) implementing campaign ID generation, idempotency key builders, initial metadata construction, state transition enforcement, metadata sanitization, and campaign JSON read/write aligned with `run_metadata.py` patterns.

#### Scenario: Module exposes idempotency key builders

- **WHEN** unit tests invoke blog, derivative, and schedule idempotency key builder functions
- **THEN** outputs match the namespaced formats defined in this spec

#### Scenario: Module tests cover transition rules

- **WHEN** the test suite runs for campaign lifecycle
- **THEN** tests verify valid transitions, invalid transition rejection, forbidden field exclusion, and Flow B guardrails
