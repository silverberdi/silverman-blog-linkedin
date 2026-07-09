# editorial-calendar-orchestration

## Purpose

Master editorial calendar planning for the `silverman-blog-linkedin` HTTP worker: canonical `editorial-calendar/calendar.json` artifact, due-item discovery, deterministic source document selection, Flow A vs Flow B planning policy, read-only `plan_editorial_calendar_due()` entry point, and API-key-protected `POST /editorial-calendar/plan-due` / `GET /editorial-calendar/status` endpoints. Staged rollout step 1 only—no n8n activation, cron, or automatic publish/package/schedule/LinkedIn publication.

## Requirements

### Requirement: Editorial calendar artifact location and shape

The worker SHALL treat `{editorial_base}/editorial-calendar/calendar.json` as the canonical master editorial calendar, where `editorial_base` is `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`.

The calendar JSON document MUST include:

- `schema_version` (string, for example `"1"`)
- `updated_at_utc` (ISO-8601 UTC with `Z` suffix)
- `items` (array of calendar item objects)

Each calendar item MUST include:

- `item_id` (unique string within the calendar)
- `title` (string)
- `status` (one of allowed calendar statuses)
- `due_at_utc` (ISO-8601 UTC with `Z` suffix)
- `source_folder` (relative path under editorial base, for example `blog-posts/ready`)
- `flow_type` (for example `flow_a_ready_blog_post`, `flow_b_source_material`)
- `content_mode` (for example `user_provided_approved_blog`, `system_generated_source_material`)
- `target_audience` (string)
- `topic_theme` (string)

Each calendar item MUST specify document resolution via:

- `source_relative_path` (relative to editorial base), OR
- `source_selection_mode` with value `explicit_path` or `single_markdown_in_folder`

Each calendar item MAY include:

- `public_slug`, `site_url`, `campaign_id`, `strategy`, `notes`

Allowed calendar item statuses MUST be:

`planned`, `scheduled`, `due`, `in_progress`, `completed`, `skipped`, `failed`

Calendar item statuses are distinct from campaign lifecycle states in `flow-a-lifecycle`.

#### Scenario: Valid calendar loads successfully

- **WHEN** `editorial-calendar/calendar.json` exists with `schema_version`, `updated_at_utc`, and a valid `items` array
- **THEN** the planner loads and validates the document without error

#### Scenario: Missing calendar reported by planner

- **WHEN** `editorial-calendar/` exists but `editorial-calendar/calendar.json` does not exist
- **THEN** planning returns `status` `calendar_missing` and error code `calendar_file_not_found`

#### Scenario: Invalid calendar shape rejected

- **WHEN** the calendar file is not valid JSON or an item is missing required fields
- **THEN** planning returns `status` `calendar_invalid` with error code `calendar_schema_invalid`

### Requirement: Editorial calendar distinct from campaign distribution scheduling

Editorial calendar scheduling MUST answer when editorial processing should start for a content item.

Campaign LinkedIn distribution scheduling (`metadata/campaigns/`, `linkedin_distribution.scheduled_at_utc`) MUST remain the authority for when individual LinkedIn variants publish within a campaign.

This capability MUST NOT modify campaign distribution scheduling metadata.

#### Scenario: Planner does not write linkedin_distribution

- **WHEN** `plan_editorial_calendar_due` succeeds
- **THEN** no campaign metadata files are created or updated and no `linkedin_distribution` fields are written

### Requirement: Due-item discovery

The planning service SHALL accept an optional `now_utc` timestamp (ISO-8601 UTC `Z`); when omitted, the worker MUST use current UTC time.

An item is due for planning when:

- `due_at_utc <= now_utc`, AND
- `status` is `scheduled` or `due`

Items with `status` `planned` and `due_at_utc <= now_utc` MUST NOT be selected; the planner MUST emit warning `calendar_item_overdue_but_planned`.

Items with `status` in `in_progress`, `completed`, `skipped`, or `failed` MUST NOT be selected.

Items with `due_at_utc > now_utc` MUST NOT be selected.

#### Scenario: No due items

- **WHEN** no items match due selection rules for the supplied `now_utc`
- **THEN** planning returns `status` `no_due_items` and empty `due_items`

#### Scenario: One due Flow A item selected

- **WHEN** exactly one item has `status` `scheduled`, `due_at_utc` on or before `now_utc`, `flow_type` `flow_a_ready_blog_post`, and resolvable source document
- **THEN** `due_items` contains one entry with resolved `source_relative_path` and Flow A planned steps

#### Scenario: Future item not selected

- **WHEN** an item has `due_at_utc` after `now_utc`
- **THEN** that item is not included in `due_items`

### Requirement: Deterministic source document selection

Source folder paths MUST be validated relative to the editorial base; path traversal (`..`) and absolute paths MUST be rejected.

When `source_relative_path` is provided, the planner MUST verify the file exists, is a regular file, has extension `.md`, and lies under the item's `source_folder`.

When `source_selection_mode` is `single_markdown_in_folder`, the planner MUST list `*.md` files directly in `source_folder` (non-recursive) and select the document only when exactly one match exists.

When zero or more than one markdown file matches without explicit `source_relative_path`, the item plan MUST have `selection_status` `rejected` and error code `calendar_ambiguous_source_selection`.

#### Scenario: Explicit path resolves

- **WHEN** a due item specifies `source_relative_path` pointing to an existing markdown file under `source_folder`
- **THEN** the plan includes that path with `selection_status` `selected`

#### Scenario: Ambiguous folder rejected

- **WHEN** a due item uses `single_markdown_in_folder` and the folder contains zero or multiple `.md` files
- **THEN** the item plan has `selection_status` `rejected` and error `calendar_ambiguous_source_selection`

### Requirement: Flow A vs Flow B planning policy

When `flow_type` is `flow_a_ready_blog_post` and `content_mode` is `user_provided_approved_blog`, the item plan MUST set `review_required` `false` and `planned_flow_steps` to labels only: `validate_ready`, `publish_blog`, `generate_linkedin_package`, `schedule_linkedin_distribution`.

When `content_mode` is `system_generated_source_material`, the item plan MUST set `review_required` `true` and `planned_flow_steps` to `queue_for_review` only.

System-generated content plans MUST NOT include `publish_blog`, `generate_linkedin_package`, or `schedule_linkedin_distribution` steps.

Unknown `flow_type` or `content_mode` combinations MUST be rejected with `calendar_invalid_flow_policy`.

#### Scenario: Generated content requires review

- **WHEN** a due item has `content_mode` `system_generated_source_material`
- **THEN** the plan sets `review_required` `true` and does not include direct publish steps

#### Scenario: User-approved Flow A eligible for future auto execution

- **WHEN** a due item has `flow_type` `flow_a_ready_blog_post` and `content_mode` `user_provided_approved_blog`
- **THEN** the plan sets `review_required` `false` and lists Flow A downstream step labels without executing them

### Requirement: Read-only planning service entry point

The worker SHALL expose `plan_editorial_calendar_due(base_path, *, now_utc=None)` returning a structured `EditorialCalendarPlanResult` serializable to JSON.

The entry point MUST NOT call `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, or `/publish-linkedin-due-variants`.

The entry point MUST NOT write `calendar.json`, campaign metadata, or run metadata.

The entry point MUST NOT move files between editorial folders.

The entry point MUST NOT access the public blog repository.

The entry point MUST NOT call LinkedIn APIs.

The result MUST include `read_only: true`.

Repeated invocations with the same `now_utc`, calendar content, and folder contents MUST return identical plans.

#### Scenario: Idempotent read-only behavior

- **WHEN** `plan_editorial_calendar_due` is called twice with the same inputs and no filesystem changes
- **THEN** both results are identical and no files or metadata are modified

#### Scenario: No downstream endpoint side effects

- **WHEN** planning succeeds for a Flow A item
- **THEN** no blog publish, package generation, distribution scheduling, or LinkedIn publication occurs

### Requirement: HTTP planning endpoint

The worker SHALL expose `POST /editorial-calendar/plan-due` protected by API-key authentication (`Depends(require_api_key)`).

The request body MUST accept optional `now_utc` and MUST use `extra="forbid"`.

The response MUST serialize `EditorialCalendarPlanResult` with fields suitable for n8n branching: `status`, `now_utc`, `due_items`, `errors`, `warnings`, `read_only`.

The worker MAY expose `GET /editorial-calendar/status` with API-key authentication returning calendar presence, `schema_version`, and item counts by status without performing due-item planning. When `calendar.json` is absent, the response MUST use `status` `calendar_missing`.

#### Scenario: Authenticated plan-due succeeds

- **WHEN** a client with valid API key calls `POST /editorial-calendar/plan-due`
- **THEN** the worker returns HTTP 200 with structured planning JSON

#### Scenario: Unauthenticated plan-due rejected

- **WHEN** a client calls `POST /editorial-calendar/plan-due` without valid API key
- **THEN** the worker returns HTTP 401

### Requirement: Expected folder validation and bootstrap

`paths.py` expected folders MUST include `editorial-calendar`.

The implementation MUST create or document creation of `{editorial_base}/editorial-calendar/` for local dev and server deployments. Deployment and bootstrap scripts or docs that enumerate expected editorial folders MUST include `editorial-calendar/` so existing server deployments remain healthy after rollout.

`GET /health` folder validation MUST report `editorial-calendar` status.

Missing `{editorial_base}/editorial-calendar/` MUST be treated as a folder readiness issue: `folders_ready` false and `status` degraded, consistent with other expected folders.

Missing `{editorial_base}/editorial-calendar/calendar.json` MUST NOT affect `/health`. The calendar file absence MUST be reported by `POST /editorial-calendar/plan-due` or `GET /editorial-calendar/status` with `status` `calendar_missing` and error code `calendar_file_not_found`.

#### Scenario: Health reports editorial-calendar folder

- **WHEN** `GET /health` is called and `editorial-calendar/` exists under the editorial base
- **THEN** the folders map includes `editorial-calendar` with `exists` and `is_directory` true

#### Scenario: Missing editorial-calendar folder degrades health

- **WHEN** `GET /health` is called and `editorial-calendar/` does not exist or is not a directory under the editorial base
- **THEN** the folders map reports `editorial-calendar` as not ready and aggregate `folders_ready` is false

#### Scenario: Health healthy without calendar.json

- **WHEN** `GET /health` is called, all expected folders including `editorial-calendar/` exist as directories, and `editorial-calendar/calendar.json` does not exist
- **THEN** the response has `status` healthy and `folders_ready` true

#### Scenario: Missing calendar.json reported by planning endpoints

- **WHEN** `editorial-calendar/` exists, `calendar.json` is absent, and a client with valid API key calls `POST /editorial-calendar/plan-due` or `GET /editorial-calendar/status`
- **THEN** the response has `status` `calendar_missing` and error code `calendar_file_not_found`

### Requirement: Operator documentation

The repository MUST document that this capability:

- Creates calendar planning foundation only
- Does not activate n8n workflows
- Does not enable cron or automatic production triggers
- Does not publish blog posts or LinkedIn content automatically
- Prepares a future execution connector slice for Flow A due items

Documentation MUST explain the distinction between editorial calendar due dates and per-campaign LinkedIn `scheduled_at_utc`.

#### Scenario: Operator doc states non-activation

- **WHEN** an operator reads the editorial calendar orchestration workflow doc
- **THEN** it explicitly states n8n, cron, and automatic publish are out of scope for this change

### Requirement: Staged rollout alignment

This change SHALL implement staged rollout step 1 only: calendar artifact, validation, and read-only due-item planner endpoint.

Execution connector (step 2), n8n/manual trigger wiring (step 3), and LinkedIn due-publication orchestration (step 4) MUST remain out of scope.

#### Scenario: Scope limited to planning foundation

- **WHEN** this change is implemented and validated
- **THEN** no code path automatically invokes publish, package, schedule, or LinkedIn publication endpoints
