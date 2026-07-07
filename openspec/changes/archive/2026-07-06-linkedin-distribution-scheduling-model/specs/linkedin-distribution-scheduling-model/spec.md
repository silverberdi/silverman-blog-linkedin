# linkedin-distribution-scheduling-model

## Purpose

Flow A LinkedIn distribution scheduling for the `silverman-blog-linkedin` HTTP worker: campaign eligibility after derivative package generation, lifecycle transition (`derivatives_generated` → `distribution_scheduled`), per-variant staggered `scheduled_at_utc` and `publish_state` `pending`, artifact hash verification, schedule idempotency, and `POST /schedule-linkedin-distribution`. Implements child slice 6 under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`.

## ADDED Requirements

### Requirement: Umbrella and dependency references

This child change SHALL implement Flow A LinkedIn distribution scheduling under active umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 6).

Scheduling behavior MUST align with Flow A distribution policy in canonical spec `editorial-canon` and artifact `content-strategy/silverman-editorial-system.md` (`#linkedin-distribution-strategy`, `#no-redundancy-rules`).

Campaign metadata, state transitions, variant IDs, and idempotency keys MUST use canonical spec `flow-a-lifecycle` and worker module `campaign_lifecycle.py`.

Scheduling MUST consume package metadata and artifacts produced by canonical spec `linkedin-derivative-package-generation` and worker module `linkedin_package_flow.py` (`linkedin_package`, `variants[]`, `linkedin-posts/generated/<campaign_id>/<variant_id>.md`).

Flow B campaigns MUST NOT enter this scheduling path.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, editorial canon child `editorial-canon-and-linkedin-distribution-strategy`, lifecycle child `flow-a-lifecycle-and-duplicate-prevention`, and package generation child `linkedin-derivative-package-generation`

#### Scenario: Flow B blocked

- **WHEN** `schedule_linkedin_distribution` is invoked for a campaign with `flow` `flow_b`
- **THEN** the operation fails with error code `linkedin_schedule_flow_not_allowed` and does not write scheduling metadata

### Requirement: LinkedIn distribution scheduling service entry point

The worker SHALL expose a distribution scheduling service entry point (for example `schedule_linkedin_distribution(base_path, *, campaign_id=None, source_relative_path=None, strategy=None, start_at_utc=None, timezone=None)`) that orchestrates campaign eligibility, artifact verification, schedule computation, campaign metadata updates, and lifecycle transitions for one Flow A campaign.

The entry point MUST return a structured `LinkedInDistributionScheduleResult` (or equivalent dataclass) serializable to JSON for HTTP and n8n consumers.

The entry point MUST NOT move editorial source files between `ready`, `processed`, or `error` folders.

The entry point MUST NOT run `git commit` or `git push`.

The entry point MUST NOT call LinkedIn API publish endpoints.

The entry point MUST NOT change `publish_state` to any value other than `pending`.

The entry point MUST NOT perform immediate LinkedIn publication.

#### Scenario: Schedule distribution by campaign_id

- **WHEN** `schedule_linkedin_distribution` is called with `campaign_id` for a `flow_a` campaign in state `derivatives_generated` with valid `linkedin_package`, matching `variants[]`, and on-disk artifacts with matching hashes
- **THEN** the function computes staggered per-variant schedules, updates campaign metadata, transitions to `distribution_scheduled`, and returns a structured result without relocating source Markdown files

#### Scenario: Schedule distribution by source_relative_path

- **WHEN** `schedule_linkedin_distribution` is called with `source_relative_path` and campaign metadata exists for that path
- **THEN** the function resolves `campaign_id` from campaign metadata and proceeds with distribution scheduling

#### Scenario: No LinkedIn API side effects

- **WHEN** this child change is applied and distribution scheduling succeeds
- **THEN** no LinkedIn API publish is attempted and every scheduled variant has `publish_state` `pending`

### Requirement: Campaign eligibility for distribution scheduling

Distribution scheduling MUST require an existing campaign metadata document at `metadata/campaigns/<campaign-id>.json`.

The campaign MUST have `flow` `flow_a`.

The campaign `state` MUST be `derivatives_generated`, or `distribution_scheduled` for idempotent re-run only when idempotency rules below match.

The campaign MUST have a non-null `linkedin_package` object with `idempotency_key` and `variant_ids`.

The campaign MUST have `variants[]` entries matching each `linkedin_package.variant_ids` entry.

Each referenced artifact at `artifact_relative_path` MUST exist on disk under the editorial base path.

The current artifact SHA-256 MUST match stored `derivative_content_sha256` in the matching `variants[]` entry.

Distribution scheduling MUST be rejected when:

- campaign metadata does not exist (`linkedin_schedule_campaign_not_found`)
- `flow` is not `flow_a` (`linkedin_schedule_flow_not_allowed`)
- `state` is before `derivatives_generated` (`linkedin_schedule_invalid_campaign_state`)
- `state` is `distribution_complete` or `flow_a_complete` (`linkedin_schedule_invalid_campaign_state`)
- `linkedin_package` is missing (`linkedin_schedule_package_missing`)
- `variants[]` is missing a required variant entry (`linkedin_schedule_variant_metadata_missing`)
- artifact file is missing (`linkedin_schedule_artifact_missing`)
- artifact content hash differs from stored hash (`linkedin_schedule_artifact_hash_changed`)
- variant list is empty (`linkedin_schedule_no_variants`)

#### Scenario: Campaign not found

- **WHEN** distribution scheduling is requested for a `campaign_id` with no metadata file
- **THEN** the operation fails with `linkedin_schedule_campaign_not_found`

#### Scenario: State before derivatives_generated rejected

- **WHEN** distribution scheduling is requested for a campaign in state `blog_published`
- **THEN** the operation fails with `linkedin_schedule_invalid_campaign_state`

#### Scenario: Missing linkedin_package rejected

- **WHEN** distribution scheduling is requested for a `derivatives_generated` campaign without `linkedin_package` metadata
- **THEN** the operation fails with `linkedin_schedule_package_missing`

#### Scenario: Missing artifact rejected

- **WHEN** distribution scheduling is requested and a variant's `artifact_relative_path` does not exist on disk
- **THEN** the operation fails with `linkedin_schedule_artifact_missing`

#### Scenario: Artifact hash changed rejected

- **WHEN** distribution scheduling is requested and an on-disk artifact SHA-256 differs from stored `derivative_content_sha256`
- **THEN** the operation fails with `linkedin_schedule_artifact_hash_changed`

### Requirement: Default staggered scheduling strategy

The default scheduling strategy MUST be named `flow_a_staggered`.

The default strategy MUST schedule canonical variants on separate calendar days with minimum spacing of 3 calendar days between consecutive variants in the same campaign.

The default strategy MUST NOT schedule two variants at the same `scheduled_at_utc` timestamp.

The default strategy MUST apply audience-aware sequencing aligned with editorial canon `#linkedin-distribution-strategy`:

1. `executive-recruiter` first
2. `engineering-leadership` second (when present)
3. `technical-architect` third (when present)
4. `short-provocative` last (when present)

When the package contains a subset of canonical variants, the strategy MUST preserve relative order from the full sequence and apply the same day-offset spacing from the schedule anchor.

Request MAY supply an alternate `strategy` name. Unknown strategy names MUST fail with `linkedin_schedule_invalid_strategy`.

#### Scenario: Variants are staggered not simultaneous

- **WHEN** distribution scheduling succeeds for a campaign with four canonical variants using default strategy
- **THEN** each variant has a distinct `scheduled_at_utc` and consecutive variants are at least 3 calendar days apart

#### Scenario: Invalid strategy rejected

- **WHEN** distribution scheduling is requested with `strategy` set to an unknown name
- **THEN** the operation fails with `linkedin_schedule_invalid_strategy`

### Requirement: Schedule anchor and UTC storage

The worker MUST accept an optional `start_at_utc` request field as a UTC ISO 8601 timestamp anchoring the first variant's schedule.

When `start_at_utc` is omitted, the worker MUST compute a deterministic default anchor (next eligible preferred weekday at default publish window in UTC).

All `scheduled_at_utc` values MUST be stored and returned in UTC.

Invalid `start_at_utc` format MUST fail with `linkedin_schedule_invalid_anchor`.

#### Scenario: Explicit anchor used

- **WHEN** distribution scheduling is called with `start_at_utc` `2026-07-07T14:00:00Z`
- **THEN** the first variant in sequence is scheduled at `2026-07-07T14:00:00Z` and subsequent variants follow staggered offsets from that anchor

#### Scenario: Invalid anchor rejected

- **WHEN** distribution scheduling is called with `start_at_utc` that is not valid UTC ISO 8601
- **THEN** the operation fails with `linkedin_schedule_invalid_anchor`

### Requirement: Per-variant scheduling metadata

For each scheduled variant, campaign metadata MUST record:

- `variant` (canonical variant ID)
- `artifact_relative_path`
- `derivative_content_sha256`
- `scheduled_at_utc`
- `publish_state` set to `pending`
- `schedule_idempotency_key` (stable per-variant scheduling idempotency key)

Campaign metadata MUST also include a `linkedin_distribution` object with at minimum:

- `distribution_id`
- `idempotency_key` (schedule-level)
- `strategy`
- `anchor_utc`
- `variant_ids`

Campaign metadata and HTTP responses MUST NOT include generated variant body text (`markdown_content`, `generated_draft_content`, or equivalent).

Existing variant fields from package generation MUST be preserved when adding scheduling fields.

#### Scenario: Per-variant schedule metadata written

- **WHEN** distribution scheduling succeeds for the first time
- **THEN** each variant in `variants[]` gains `scheduled_at_utc`, `publish_state` `pending`, and `schedule_idempotency_key`, and `linkedin_distribution` is written

#### Scenario: Metadata excludes body text

- **WHEN** distribution scheduling succeeds
- **THEN** campaign metadata JSON and HTTP response do not contain generated LinkedIn post body text

### Requirement: Distribution scheduling idempotency

The worker MUST define a stable schedule-level idempotency key from:

- `campaign_id`
- `source_content_sha256`
- `linkedin_package.idempotency_key`
- sorted variant list
- `strategy`
- schedule anchor (`anchor_utc`)
- `flow_a`

When campaign `state` is `distribution_scheduled` and stored schedule idempotency proof matches the expected key and per-variant `scheduled_at_utc` values:

- the operation MUST return `status` `completed`
- the operation MUST NOT append duplicate `state_history` entries
- the operation MUST NOT rewrite `scheduled_at_utc` values

When campaign `state` is `distribution_scheduled` but stored scheduling metadata does not match the idempotency proof:

- the operation MUST fail with `linkedin_schedule_metadata_mismatch`

#### Scenario: Idempotent rerun returns completed

- **WHEN** distribution scheduling is invoked again for a `distribution_scheduled` campaign with matching schedule idempotency proof
- **THEN** the operation returns `status` `completed` without duplicate `state_history` and without changing `scheduled_at_utc` values

#### Scenario: Scheduling mismatch fails safely

- **WHEN** distribution scheduling is invoked for a `distribution_scheduled` campaign with a different `start_at_utc` than stored `anchor_utc`
- **THEN** the operation fails with `linkedin_schedule_metadata_mismatch`

### Requirement: Campaign lifecycle transition

On successful first-time distribution scheduling, the worker MUST transition campaign state from `derivatives_generated` to `distribution_scheduled` using `transition_state(..., actor="worker")`.

The worker MUST NOT transition beyond `distribution_scheduled` in this child change.

Failed eligibility or verification MUST NOT change campaign state.

#### Scenario: Successful scheduling transitions state

- **WHEN** distribution scheduling succeeds for a campaign in `derivatives_generated`
- **THEN** campaign `state` becomes `distribution_scheduled` with a `state_history` entry recording the transition

#### Scenario: Failed scheduling does not transition

- **WHEN** distribution scheduling fails due to missing artifact
- **THEN** campaign `state` remains unchanged

### Requirement: HTTP endpoint POST /schedule-linkedin-distribution

The worker HTTP API SHALL expose `POST /schedule-linkedin-distribution` protected by API key authentication (`Depends(require_api_key)`), consistent with `POST /generate-linkedin-package` and `POST /publish-blog-post`.

The request body MUST accept exactly one of `campaign_id` or `source_relative_path`.

The request body MAY accept optional `strategy`, `start_at_utc`, and `timezone`.

The request Pydantic model MUST use `extra="forbid"`.

The response MUST be JSON containing at minimum:

- `status` (`completed` or `failed`)
- `campaign_id`
- `state`
- `distribution_id` (or `schedule_id`)
- `variant_schedules` (per-variant summary array)
- `errors`
- `warnings`
- `metadata_written`
- `metadata_error_code`

Invalid request bodies MUST return HTTP 422.

Unauthorized requests MUST be rejected.

#### Scenario: HTTP endpoint requires auth

- **WHEN** `POST /schedule-linkedin-distribution` is called without a valid API key
- **THEN** the request is rejected with an unauthorized response

#### Scenario: HTTP successful response shape

- **WHEN** `POST /schedule-linkedin-distribution` succeeds
- **THEN** the JSON response includes `status`, `campaign_id`, `state`, `distribution_id`, `variant_schedules`, `errors`, `warnings`, `metadata_written`, and `metadata_error_code`, and does not include variant body text

#### Scenario: HTTP invalid body returns 422

- **WHEN** `POST /schedule-linkedin-distribution` is called with an empty body or both `campaign_id` and `source_relative_path`
- **THEN** the API returns HTTP 422

### Requirement: Stable error codes

Distribution scheduling MUST use stable machine-readable error codes including at minimum:

- `linkedin_schedule_campaign_not_found`
- `linkedin_schedule_flow_not_allowed`
- `linkedin_schedule_invalid_campaign_state`
- `linkedin_schedule_package_missing`
- `linkedin_schedule_variant_metadata_missing`
- `linkedin_schedule_artifact_missing`
- `linkedin_schedule_artifact_hash_changed`
- `linkedin_schedule_metadata_mismatch`
- `linkedin_schedule_no_variants`
- `linkedin_schedule_invalid_strategy`
- `linkedin_schedule_invalid_anchor`
- `linkedin_schedule_metadata_write_failed`

#### Scenario: Error codes are stable strings

- **WHEN** distribution scheduling fails for a known eligibility violation
- **THEN** the `errors` array contains the corresponding stable error code string

### Requirement: Test coverage

The repository MUST include `tests/test_linkedin_distribution_scheduling.py` covering at minimum:

- campaign not found
- Flow B rejected
- campaign before `derivatives_generated` rejected
- missing `linkedin_package` rejected
- missing variants rejected
- missing artifact rejected
- artifact hash changed rejected
- successful scheduling writes per-variant schedule metadata
- successful scheduling transitions to `distribution_scheduled`
- `publish_state` is `pending` for every variant
- variants are staggered, not simultaneous
- no LinkedIn API publication attempted
- no n8n workflow JSON changed
- metadata and response do not include generated body text
- idempotent rerun returns `completed` without duplicate `state_history`
- scheduling mismatch fails safely
- HTTP endpoint requires auth
- HTTP successful response shape
- HTTP invalid body returns 422

Full `pytest` and `openspec validate --all` MUST pass after apply.

#### Scenario: Test module exists and passes

- **WHEN** `pytest` runs after this child change is applied
- **THEN** `tests/test_linkedin_distribution_scheduling.py` passes and no n8n workflow JSON files are modified
