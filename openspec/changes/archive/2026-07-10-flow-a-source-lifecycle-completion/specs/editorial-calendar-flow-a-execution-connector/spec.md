## MODIFIED Requirements

### Requirement: Real execution Flow A sequence with result chaining

When `dry_run` is `false`, the connector MUST execute Flow A only for items where:

- Planner `selection_status` is `selected`
- `review_required` is `false`
- `flow_type` is `flow_a_ready_blog_post` and `content_mode` is `user_provided_approved_blog`
- Item is not skipped per existing-campaign or other skip rules

For each eligible item, the connector MUST invoke existing internal services in strict order:

1. `publish_blog_post`
2. `generate_linkedin_package`
3. `schedule_linkedin_distribution`
4. `complete_flow_a_source_lifecycle` (canonical spec `flow-a-source-lifecycle-completion`)

Each subsequent step MUST use the actual result object from the immediately prior step as its primary input source:

- After publish: `generate_linkedin_package` MUST prefer `campaign_id` from the publish result; when absent, MUST use `source_relative_path` from the publish result. Calendar `site_url` and other supported calendar fields MAY be passed when present.
- After package: `schedule_linkedin_distribution` MUST prefer `campaign_id` from the package result; when absent, MUST use `source_relative_path` from the package result. Calendar `strategy` MAY be passed when present and supported.
- After schedule: `complete_flow_a_source_lifecycle` MUST prefer `campaign_id` from the schedule result; when absent, MUST use `source_relative_path` from the schedule result.

The publish step result (`BlogPublishResult`) is the source of truth for resolved `campaign_id`, `source_public_url`, published blog path (`source_relative_path`), and blog publish status. Calendar hints MUST NOT override resolved publish/package outputs for subsequent steps.

The connector MUST preserve existing idempotency behavior of downstream services.

Lifecycle completion MUST NOT run when `schedule_linkedin_distribution` fails.

When scheduling succeeds but lifecycle completion fails, item `execution_status` MUST remain `executed` (scheduling succeeded) and item results MUST include `source_lifecycle_status` `failed` with lifecycle `errors[]` and `warnings[]` merged without exposing secrets.

When lifecycle completion succeeds or skips as already processed, item results MUST include `source_lifecycle_status` `completed` or `skipped`.

#### Scenario: Real mode executes Flow A sequence with chained inputs

- **WHEN** `dry_run=false`, one eligible due Flow A item exists, and no skip rule applies
- **THEN** `publish_blog_post`, `generate_linkedin_package`, `schedule_linkedin_distribution`, and `complete_flow_a_source_lifecycle` are invoked in order for that item, package receives publish result identifiers, schedule receives package result identifiers, lifecycle receives schedule result identifiers, and the item `execution_status` is `executed` when scheduling succeeds

#### Scenario: Real mode uses internal services not HTTP self-calls

- **WHEN** real execution runs for an eligible item
- **THEN** the connector invokes Python service functions directly rather than HTTP loopback to worker endpoints

#### Scenario: Schedule failure skips lifecycle completion

- **WHEN** `schedule_linkedin_distribution` fails for an item in real execution mode
- **THEN** `complete_flow_a_source_lifecycle` is not invoked and source files remain in `blog-posts/ready/`

## ADDED Requirements

### Requirement: Dry-run does not perform source lifecycle

When `dry_run` is `true`, the connector MUST NOT call `complete_flow_a_source_lifecycle` and MUST NOT move editorial source files.

#### Scenario: Dry-run excludes lifecycle completion

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true` for an eligible Flow A item
- **THEN** `complete_flow_a_source_lifecycle` is not invoked and `read_only` is `true`
