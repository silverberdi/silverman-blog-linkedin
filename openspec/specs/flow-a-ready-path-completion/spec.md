# flow-a-ready-path-completion

## Purpose

Authenticated HTTP completion for the ready-folder Flow A n8n path after successful distribution scheduling: invoke `complete_flow_a_source_lifecycle`, optionally upsert/reconcile editorial calendar items from campaign facts, and return structured `completed` / `partial` / `failed` / `skipped` outcomes for n8n branching. Does not perform LinkedIn API publication.

## Requirements

### Requirement: Ready-path completion HTTP entry point

The worker SHALL expose authenticated `POST /complete-flow-a-ready-path` that completes ready-path Flow A after successful distribution scheduling by invoking `complete_flow_a_source_lifecycle` and optionally updating the editorial calendar.

The request body MUST accept:

- `campaign_id` (string, required)
- `source_relative_path` (string, optional) — passed through to lifecycle resolution
- `update_calendar` (boolean, default `true`)

The endpoint MUST require the same API-key authentication as other Flow A worker mutating routes.

Dry-run MUST NOT be implied; this endpoint performs real filesystem and metadata side effects when called.

#### Scenario: Lifecycle completes for distribution_scheduled campaign

- **WHEN** a client calls `POST /complete-flow-a-ready-path` with a valid API key and `campaign_id` for a Flow A campaign in `distribution_scheduled` whose source Markdown is still under `blog-posts/ready/` or `blog-posts/queued/`
- **THEN** the worker runs `complete_flow_a_source_lifecycle`, campaign `state` becomes `flow_a_complete` on success, and `source_file_status.location` becomes `processed`

#### Scenario: Auth required

- **WHEN** a client calls `POST /complete-flow-a-ready-path` without a valid API key
- **THEN** the worker rejects the request with the same auth failure behavior as other authenticated Flow A routes

#### Scenario: Premature lifecycle rejected

- **WHEN** a client calls the endpoint for a campaign that is not eligible for source lifecycle completion
- **THEN** the response `status` is `failed` and includes the lifecycle error code(s) without claiming `flow_a_complete`

### Requirement: Ready-path completion response shape

The endpoint MUST return structured JSON including at least:

- `status`: one of `completed`, `partial`, `failed`, `skipped`
- `campaign_id`
- `source_lifecycle_status` (and lifecycle error codes when failed)
- `calendar_update_status` when calendar update was attempted or skipped
- `errors` array (possibly empty)

Overall `status` MUST be:

- `completed` when lifecycle succeeds or is idempotently skipped-already-complete AND calendar update succeeds or is an allowed skip (`skipped_calendar_absent`, `skipped_already_completed`)
- `partial` when lifecycle succeeds (or skipped-already-complete) but calendar update fails while `update_calendar` was true
- `failed` when lifecycle fails
- `skipped` when campaign is already fully complete and no calendar mutation is required

The endpoint MUST NOT invoke LinkedIn publication endpoints or create LinkedIn API posts.

#### Scenario: Partial when calendar write fails after lifecycle

- **WHEN** lifecycle succeeds and `update_calendar` is true but calendar persistence fails
- **THEN** response `status` is `partial`, source remains processed / `flow_a_complete`, and `calendar_update_status` indicates failure with stable error code(s)

#### Scenario: No LinkedIn publication side effects

- **WHEN** ready-path completion succeeds
- **THEN** no `/queue-linkedin-publication`, `/publish-linkedin-due-variants`, or `/cancel-linkedin-publication` behavior is invoked as part of the completion request

### Requirement: Calendar upsert or reconcile from campaign

When `update_calendar` is true and `editorial-calendar/calendar.json` is present, the worker MUST resolve a calendar item by `campaign_id` or matching normalized source path identity, then complete it with Flow A completion facts derived from the campaign.

When no matching item exists, the worker MUST insert a new calendar item with `status=completed` (or equivalent terminal completed status used by existing calendar completion helpers) populated from campaign identity and completion facts, without inventing LinkedIn API publication as completed.

When the calendar file is absent, the worker MUST set `calendar_update_status` to `skipped_calendar_absent` and MUST NOT fail lifecycle solely for that reason.

When `update_calendar` is false, the worker MUST skip calendar mutation and record `calendar_update_status=skipped_not_requested`.

#### Scenario: Insert completed item for new ready-path campaign

- **WHEN** `update_calendar` is true, calendar.json exists, and no item matches the campaign
- **THEN** a new completed calendar item is persisted with `campaign_id` and `flow_a_completion` facts aligned to the campaign

#### Scenario: Complete existing matching item

- **WHEN** `update_calendar` is true and an item already references the same `campaign_id`
- **THEN** the worker completes that item idempotently without creating a duplicate row

#### Scenario: Calendar absent is allowed skip

- **WHEN** `update_calendar` is true and `editorial-calendar/calendar.json` is missing
- **THEN** lifecycle completion can still yield overall `completed` with `calendar_update_status=skipped_calendar_absent`
