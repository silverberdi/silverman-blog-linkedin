## MODIFIED Requirements

### Requirement: Real execution Flow A sequence with result chaining

When `dry_run` is `false`, the connector MUST execute Flow A only for items where:

- Planner `selection_status` is `selected`
- `review_required` is `false`
- `flow_type` is `flow_a_ready_blog_post` and `content_mode` is `user_provided_approved_blog`
- Item is not skipped per existing-campaign or other skip rules

For each eligible item, the connector MUST invoke internal services in strict order:

0. `accept_flow_a_source_for_queue` (canonical spec `flow-a-operational-queue-lifecycle`) when source is in `blog-posts/ready/`; or resolve already-queued campaign per already-queued connector requirement when source has previously been accepted
1. `claim_flow_a_execution` then `publish_blog_post`
2. `generate_linkedin_package`
3. `schedule_linkedin_distribution`
4. `complete_flow_a_source_lifecycle` (canonical spec `flow-a-source-lifecycle-completion`) — terminal completion sets `location=processed` and `execution_state=idle`
5. `release_flow_a_execution` ONLY on recoverable or failed non-terminal exits; if invoked after successful lifecycle completion it MUST be idempotent (`already_released`)

Each subsequent step MUST use the actual result object from the immediately prior step as its primary input source:

- After queue acceptance or already-queued resolution: publish MUST use `campaign_id` and active queued `source_relative_path` from acceptance or skip result
- After publish: `generate_linkedin_package` MUST prefer `campaign_id` from the publish result; when absent, MUST use `source_relative_path` from the publish result. Calendar `site_url` and other supported calendar fields MAY be passed when present.
- After package: `schedule_linkedin_distribution` MUST prefer `campaign_id` from the package result; when absent, MUST use `source_relative_path` from the package result. Calendar `strategy` MAY be passed when present and supported.
- After schedule: `complete_flow_a_source_lifecycle` MUST prefer `campaign_id` from the schedule result; when absent, MUST use `source_relative_path` from the schedule result.

The publish step result (`BlogPublishResult`) is the source of truth for resolved `campaign_id`, `source_public_url`, published blog path (`source_relative_path`), and blog publish status. Calendar hints MUST NOT override resolved publish/package outputs for subsequent steps.

The connector MUST preserve existing idempotency behavior of downstream services.

Lifecycle completion MUST NOT run when `schedule_linkedin_distribution` fails.

When scheduling succeeds but lifecycle completion fails, item `execution_status` MUST remain `executed` (scheduling succeeded) and item results MUST include `source_lifecycle_status` `failed` with lifecycle `errors[]` and `warnings[]` merged without exposing secrets.

When lifecycle completion succeeds or skips as already processed, item results MUST include `source_lifecycle_status` `completed` or `skipped`.

Item results MUST include `queue_acceptance_status` (`completed`, `skipped_already_queued`, `failed`, `partial`, `repair_required`) when queue stage runs.

#### Scenario: Real mode executes queue acceptance then Flow A sequence

- **WHEN** `dry_run=false`, one eligible due Flow A item exists with source in `blog-posts/ready/`, and no skip rule applies
- **THEN** `accept_flow_a_source_for_queue`, `publish_blog_post`, `generate_linkedin_package`, `schedule_linkedin_distribution`, and `complete_flow_a_source_lifecycle` are invoked in order, the source ends under `blog-posts/processed/`, and the item `execution_status` is `executed` when scheduling succeeds

#### Scenario: Real mode uses internal services not HTTP self-calls

- **WHEN** real execution runs for an eligible item
- **THEN** the connector invokes Python service functions directly rather than HTTP loopback to worker endpoints

#### Scenario: Schedule failure skips lifecycle completion

- **WHEN** `schedule_linkedin_distribution` fails for an item in real execution mode after queue acceptance
- **THEN** `complete_flow_a_source_lifecycle` is not invoked and source files remain in `blog-posts/queued/`

### Requirement: Dry-run does not perform source lifecycle

When `dry_run` is `true`, the connector MUST NOT call `accept_flow_a_source_for_queue`, `claim_flow_a_execution`, `complete_flow_a_source_lifecycle`, or move editorial source files.

#### Scenario: Dry-run excludes queue acceptance and lifecycle

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true` for an eligible Flow A item
- **THEN** queue acceptance and lifecycle completion are not invoked, no `execution_state=processing` is written, and `read_only` is `true`

## ADDED Requirements

### Requirement: Dry-run queue acceptance reporting

When `dry_run` is `true` and an item would pass queue acceptance eligibility, the item result MUST report a would-accept queue decision without fabricated `queued_source_relative_path` values on disk.

#### Scenario: Dry-run reports would-accept without queue move

- **WHEN** `dry_run=true` and a due eligible Flow A item references a valid ready source
- **THEN** the item result indicates queue acceptance would occur and the source remains in `blog-posts/ready/`

### Requirement: Queue acceptance failure stops Flow A sequence

In real execution mode, when queue acceptance fails for an eligible item, the connector MUST NOT invoke publish, package, schedule, or lifecycle completion for that item.

The item MUST have `execution_status` `failed` and `failed_step` `queue_acceptance`.

#### Scenario: Queue acceptance failure prevents publish

- **WHEN** real execution runs for an eligible item and queue acceptance returns failed status
- **THEN** `publish_blog_post` is not invoked and `failed_step` is `queue_acceptance`

### Requirement: Already-queued campaign connector behavior

When `calendar.json` still references the original ready path but the campaign source has already moved to `queued`, a later connector invocation MUST:

- Resolve an existing campaign by persisted `campaign_id` before requiring the calendar source path to exist in `ready/`
- Match the calendar's original source path against `original_source_relative_path` (or first recorded `source_relative_path` when original is not yet set)
- Recognize `source_file_status.location=queued`
- Return `queue_acceptance_status=skipped_already_queued`
- Use `queued_source_relative_path` as the active path for subsequent Flow A steps
- Claim or reclaim execution according to execution state (including stale reclaim)
- Resume from the persisted Flow A pipeline `state`
- NOT move the source back to `ready/`
- NOT create a duplicate campaign
- NOT require the original ready file to exist

#### Scenario: Transient failure followed by later connector invocation

- **WHEN** queue acceptance succeeded and Flow A failed transiently with source in `blog-posts/queued/`, and a later connector invocation runs for the same calendar item still referencing the original ready path
- **THEN** `queue_acceptance_status` is `skipped_already_queued`, the ready file is not required, execution reclaims or resumes from persisted pipeline state, and the source is not moved back to `ready/`

#### Scenario: Stale claim followed by reclaim

- **WHEN** a campaign has `execution_state=stale` with source in `blog-posts/queued/` and the connector runs for the same calendar item
- **THEN** `queue_acceptance_status` is `skipped_already_queued`, execution is reclaimed, and Flow A resumes idempotently without duplicate side effects

#### Scenario: Distribution scheduled campaign requires only lifecycle completion

- **WHEN** a campaign has `state=distribution_scheduled`, `source_file_status.location=queued`, and scheduling metadata already exists
- **THEN** the connector skips queue acceptance with `skipped_already_queued`, resumes from `distribution_scheduled`, and invokes lifecycle completion when appropriate without re-running publish, package, or schedule unnecessarily

#### Scenario: Already-queued source after original due time

- **WHEN** a source was queue-accepted on its due date, the due time has passed, and the connector runs again for the same calendar item
- **THEN** `queue_acceptance_status` is `skipped_already_queued`, the source remains in `blog-posts/queued/`, and Flow A may continue without dequeuing or moving back to `ready/`
