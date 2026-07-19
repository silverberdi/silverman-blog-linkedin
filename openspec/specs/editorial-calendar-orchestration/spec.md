# editorial-calendar-orchestration

## Purpose

Master editorial calendar planning for the `silverman-blog-linkedin` HTTP worker: PostgreSQL-backed master calendar (capability `editorial-calendar-database`, database `silverman_linkedin_db`), due-item discovery, deterministic source document selection, Flow A vs Flow B planning policy, read-only `plan_editorial_calendar_due()` entry point, and API-key-protected `POST /editorial-calendar/plan-due` / `GET /editorial-calendar/status` endpoints. Staged rollout step 1 only—no n8n activation, cron, or automatic publish/package/schedule/LinkedIn publication.

## Requirements

### Requirement: Editorial calendar artifact location and shape

The worker SHALL treat a PostgreSQL-backed master editorial calendar (see capability `editorial-calendar-database`) as the canonical master editorial calendar. The editorial filesystem path `{editorial_base}/editorial-calendar/calendar.json` MUST NOT be the durable source of truth after cutover. The `editorial-calendar/` directory under `editorial_base` MAY remain for layout/health compatibility and MAY hold a non-authoritative legacy file used only for operator-gated import.

The calendar document MUST include:

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

- **WHEN** the calendar database contains a document with `schema_version`, `updated_at_utc`, and a valid `items` set
- **THEN** the planner loads and validates the document without error

#### Scenario: Empty database calendar is loadable

- **WHEN** the calendar database is reachable and contains zero items
- **THEN** planning treats the calendar as present and empty rather than as a missing filesystem file SoT failure

#### Scenario: Invalid calendar shape rejected

- **WHEN** stored calendar data is corrupt or an item is missing required fields
- **THEN** planning returns `status` `calendar_invalid` with error code `calendar_schema_invalid`

### Requirement: Editorial calendar distinct from campaign distribution scheduling

Editorial calendar scheduling MUST answer when editorial processing should start for a content item.

Campaign LinkedIn distribution scheduling (`metadata/campaigns/`, `linkedin_distribution.scheduled_at_utc`) MUST remain the authority for when individual LinkedIn variants publish within a campaign.

This capability MUST NOT modify campaign distribution scheduling metadata.

#### Scenario: Planner does not write linkedin_distribution

- **WHEN** `plan_editorial_calendar_due` succeeds
- **THEN** no campaign metadata files are created or updated and no `linkedin_distribution` fields are written

### Requirement: Calendar atomic persistence

The worker SHALL provide `save_calendar_atomic` (name stable for callers) that persists the master editorial calendar to the calendar database using a transaction.

Before commit, the function MUST validate the full calendar document using the same rules as `load_calendar`.

The function MUST set `updated_at_utc` to the write timestamp in canonical UTC `Z` format.

The function MUST enforce optimistic concurrency via a document version (or equivalent). When the caller's expected version does not match the stored version, the function MUST NOT commit changes, MUST leave stored calendar rows intact, and MUST return `calendar_completion_concurrent_update`.

Database write failures MUST return `calendar_completion_write_failed` (or equivalent structured write failure) and MUST leave the prior committed calendar intact.

The durable calendar store MUST be the database defined by `editorial-calendar-database`. Filesystem write of `calendar.json` MUST NOT be required for a successful save after cutover.

#### Scenario: Successful atomic save updates timestamp

- **WHEN** `save_calendar_atomic` is called with a valid calendar document and matching expected version
- **THEN** the database calendar is updated transactionally and `updated_at_utc` reflects the write instant

#### Scenario: Failed save leaves original calendar intact

- **WHEN** `save_calendar_atomic` fails during validation or before commit
- **THEN** the previously committed database calendar remains valid and unchanged

#### Scenario: Concurrent calendar modification is not overwritten

- **WHEN** `save_calendar_atomic` is called with an expected version that no longer matches the database
- **THEN** the function returns `calendar_completion_concurrent_update`, does not commit, and leaves concurrent changes intact

### Requirement: Flow A calendar item completion optional fields

The calendar schema SHALL accept the following optional fields on calendar items after Flow A terminal completion:

- `completed_at_utc` — canonical UTC `Z` timestamp when the item was first closed; set once and stable across idempotent retries
- `processed_source_relative_path` — canonical final processed Markdown path under `blog-posts/processed/`
- `flow_a_completion` — summary evidence object for terminal Flow A facts at close or reconciliation time

When `completed_at_utc` is present, it MUST validate as canonical UTC `Z`.

When `processed_source_relative_path` is present, it MUST be a relative path under the editorial base ending in `.md`.

When `flow_a_completion` is present, it MUST be an object whose optional keys include at minimum `campaign_state`, `execution_status`, `source_lifecycle_status`, `blog_publish_status`, `public_url`, `linkedin_package_status`, and `linkedin_distribution_status`. It MUST NOT duplicate parent-item canonical fields `campaign_id`, `processed_source_relative_path`, or `completed_at_utc`. It MUST NOT claim LinkedIn content was published; it MAY state only that package generation and distribution scheduling completed.

`linkedin_package_status` and `linkedin_distribution_status` MUST use operational outcome vocabulary aligned with Flow A step results (for example `completed`, `failed`) and MUST NOT read non-existent campaign metadata keys such as `linkedin_package.status` or `linkedin_distribution.status`.

When populated from campaign metadata, `linkedin_package_status` MUST be derived from authoritative package evidence including `linkedin_package.package_status` and campaign lifecycle state. When populated from campaign metadata, `linkedin_distribution_status` MUST be derived from authoritative scheduling evidence including campaign lifecycle state at or beyond `distribution_scheduled`, the presence of `linkedin_distribution` metadata, and top-level `variants[]` schedule fields when applicable.

`load_calendar` MUST accept calendar items with or without these optional fields.

#### Scenario: Completed item with optional fields loads successfully

- **WHEN** `calendar.json` contains an item with `status` `completed` and valid optional completion fields
- **THEN** `load_calendar` succeeds without schema errors

#### Scenario: Invalid completed_at_utc rejected

- **WHEN** a calendar item includes `completed_at_utc` that is not canonical UTC `Z`
- **THEN** `load_calendar` returns `calendar_schema_invalid`

#### Scenario: LinkedIn summary statuses derived from campaign metadata shape

- **WHEN** completion facts are built from a `flow_a_complete` campaign with `linkedin_package.package_status` `generated` and `linkedin_distribution.distribution_id` present
- **THEN** `flow_a_completion.linkedin_package_status` is `completed` and `flow_a_completion.linkedin_distribution_status` is `completed`

### Requirement: Flow A calendar item completion mutation

The worker SHALL provide `complete_flow_a_calendar_item(calendar, *, item_id, completion_facts)` that returns an updated calendar document and a mutation indicator without persisting.

The function MUST locate the item by stable `item_id`.

The function MUST set `status` to `completed`.

The function MUST preserve `item_id`, `title`, `due_at_utc`, `flow_type`, `content_mode`, `source_folder`, `target_audience`, `topic_theme`, the original `source_relative_path` when present, and `notes` byte-for-byte unchanged.

The function MUST set or update canonical fields `campaign_id`, `completed_at_utc`, `processed_source_relative_path`, and `flow_a_completion` from `completion_facts` when provided.

The function MUST NOT modify unrelated calendar items.

When the target item is already `status=completed` with equivalent canonical completion facts and equivalent `flow_a_completion` summary evidence, the function MUST return an idempotent no-op indicator without producing a persistable mutation, without rewriting `completed_at_utc`, and without mutating `notes`.

When the target item is already `status=completed` with equivalent canonical completion facts except that stored `flow_a_completion.linkedin_package_status` and/or `flow_a_completion.linkedin_distribution_status` are `null` or missing while `completion_facts` supply non-null derived values and all other compared summary keys and canonical parent fields match, the function MUST treat the update as a persistable repair mutation rather than `calendar_completion_facts_conflict`.

When the target item is already `status=completed` but canonical completion facts or `flow_a_completion` summary evidence conflict with `completion_facts`, the function MUST fail with error code `calendar_completion_facts_conflict` and MUST NOT silently overwrite terminal facts.

When stored LinkedIn summary values are non-null and differ from derived values in `completion_facts`, the function MUST fail with `calendar_completion_facts_conflict`.

When the target `item_id` is not found, the function MUST fail with error code `calendar_item_not_found`.

#### Scenario: Completion updates only matching item

- **WHEN** `complete_flow_a_calendar_item` is called for one `item_id` in a multi-item calendar
- **THEN** only that item is mutated and other items remain structurally unchanged

#### Scenario: Missing item returns not found

- **WHEN** `complete_flow_a_calendar_item` is called for an `item_id` not present in `items`
- **THEN** the operation fails with `calendar_item_not_found` and does not produce a persistable calendar document

#### Scenario: Notes preserved on completion

- **WHEN** `complete_flow_a_calendar_item` closes a calendar item
- **THEN** `notes` is unchanged byte-for-byte from its pre-completion value

#### Scenario: Equivalent completed item is no-write no-op

- **WHEN** `complete_flow_a_calendar_item` is called for an item already `status=completed` with equivalent canonical completion facts
- **THEN** the function returns a no-op indicator, does not change `completed_at_utc`, and does not mutate `notes`

#### Scenario: Conflicting completed item returns conflict error

- **WHEN** `complete_flow_a_calendar_item` is called for an item already `status=completed` with conflicting terminal completion facts
- **THEN** the operation fails with `calendar_completion_facts_conflict` and performs no mutation

#### Scenario: Null LinkedIn summaries repaired on already-completed item

- **WHEN** `complete_flow_a_calendar_item` is called for an item already `status=completed` whose stored `flow_a_completion` has null LinkedIn summary fields and `completion_facts` supply `linkedin_package_status` and `linkedin_distribution_status` both `completed` with all other compared fields matching
- **THEN** the function returns a persistable mutation with repaired LinkedIn summary fields and does not return `calendar_completion_facts_conflict`

#### Scenario: Conflicting non-null LinkedIn summaries fail closed

- **WHEN** `complete_flow_a_calendar_item` is called for an item already `status=completed` whose stored `flow_a_completion.linkedin_package_status` is a non-null value that differs from `completion_facts`
- **THEN** the function fails with `calendar_completion_facts_conflict` and does not produce a persistable mutation

### Requirement: Due-item discovery

The planning service SHALL accept an optional `now_utc` timestamp (ISO-8601 UTC `Z`); when omitted, the worker MUST use current UTC time.

An item is due for planning when:

- `due_at_utc <= now_utc`, AND
- `status` is `scheduled` or `due`

Items with `status` `planned` and `due_at_utc <= now_utc` MUST NOT be selected; the planner MUST emit warning `calendar_item_overdue_but_planned`.

Items with `status` in `in_progress`, `completed`, `skipped`, or `failed` MUST NOT be selected.

Items with `due_at_utc > now_utc` MUST NOT be selected.

Terminal `status=completed` items MUST be excluded before source existence validation; they MUST NOT invoke `resolve_source_document`.

#### Scenario: No due items

- **WHEN** no items match due selection rules for the supplied `now_utc`
- **THEN** planning returns `status` `no_due_items` and empty `due_items`

#### Scenario: One due Flow A item selected

- **WHEN** exactly one item has `status` `scheduled`, `due_at_utc` on or before `now_utc`, `flow_type` `flow_a_ready_blog_post`, and resolvable source document
- **THEN** `due_items` contains one entry with resolved `source_relative_path` and Flow A planned steps

#### Scenario: Future item not selected

- **WHEN** an item has `due_at_utc` after `now_utc`
- **THEN** that item is not included in `due_items`

#### Scenario: Completed Flow A item not selected

- **WHEN** an item has `status` `completed` and `due_at_utc` on or before `now_utc`
- **THEN** that item is not included in `due_items`, does not invoke source existence validation, and does not produce `calendar_source_not_found`

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

Flow A calendar completion persistence is performed only by the execution connector after successful lifecycle completion or by the connector reconciliation path; the planner MUST remain read-only.

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

Documentation MUST state that terminal Flow A calendar items use `status` `completed`, that completion is written by the execution connector after full Flow A lifecycle success or reconciliation of an already-complete campaign, that `campaign_id` is the authoritative reconciliation identity, that `notes` is never mutated by completion or reconciliation, and that completed items are excluded from due planning before source existence validation.

#### Scenario: Operator doc states non-activation

- **WHEN** an operator reads the editorial calendar orchestration workflow doc
- **THEN** it explicitly states n8n, cron, and automatic publish are out of scope for this change

#### Scenario: Operator doc explains completed item exclusion

- **WHEN** an operator reads editorial calendar workflow documentation
- **THEN** it explains that `status=completed` items are not due, are excluded before source validation, and are closed by the Flow A execution connector after campaign `flow_a_complete` or reconciliation

### Requirement: Staged rollout alignment

This change SHALL implement staged rollout step 1 only: calendar artifact, validation, and read-only due-item planner endpoint.

Execution connector (step 2), n8n/manual trigger wiring (step 3), and LinkedIn due-publication orchestration (step 4) MUST remain out of scope.

#### Scenario: Scope limited to planning foundation

- **WHEN** this change is implemented and validated
- **THEN** no code path automatically invokes publish, package, schedule, or LinkedIn publication endpoints

### Requirement: Authenticated HTTP schedule update for editorial calendar items

The worker SHALL expose `POST /editorial-calendar/update-item-schedule` protected by API-key authentication (`Depends(require_api_key)`).

The endpoint MUST update the scheduled due time of an existing item in the canonical `{editorial_base}/editorial-calendar/calendar.json` through worker logic only. The browser and n8n MUST NOT write `calendar.json` directly.

Request body MUST include:

- `item_id` (string, required)
- `new_due_at_utc` (ISO-8601 UTC with `Z` suffix, required)
- optional `dry_run` (boolean, default `true`)
- optional `reason` (string)
- optional `idempotency_key` (string)
- optional `actor` (string)
- optional `source` (string)
- optional `expected_calendar_fingerprint` (SHA-256 hex of the current raw calendar file)

The endpoint MUST NOT call LinkedIn publication APIs, DeepSeek, ComfyUI, or Git, and MUST NOT publish blog content or perform blog handoff as part of the schedule update.

#### Scenario: Authenticated schedule update accepts dry-run default

- **WHEN** a client with a valid API key calls `POST /editorial-calendar/update-item-schedule` omitting `dry_run`
- **THEN** the worker validates without mutating `calendar.json`

#### Scenario: Unauthenticated schedule update is rejected

- **WHEN** a client calls `POST /editorial-calendar/update-item-schedule` without a valid API key
- **THEN** the worker rejects the request with existing unauthorized semantics and does not mutate `calendar.json`

#### Scenario: Schedule update does not publish

- **WHEN** `POST /editorial-calendar/update-item-schedule` runs with `dry_run` false for an eligible item
- **THEN** the worker does not call LinkedIn publication APIs and does not publish blog content as part of the request

### Requirement: Calendar schedule-update eligibility and validation

`POST /editorial-calendar/update-item-schedule` MUST locate the target by `item_id` and MUST reject missing items with `calendar_item_not_found`.

The endpoint MUST allow schedule changes only for future unpublished editorial items. Items with terminal or historical statuses `completed`, `skipped`, or `failed` MUST be rejected as unsupported for schedule mutation.

`new_due_at_utc` MUST be canonical UTC `Z` and MUST be strictly after current worker UTC time; otherwise the worker MUST fail with a stable code such as `calendar_schedule_time_invalid` and MUST NOT mutate the calendar.

The endpoint MUST validate interim cadence/rescheduling rules (until superseded by an approved BL-021 definition), including at least:

- duplicate blog slot on the same UTC day as another blog item (`calendar_schedule_duplicate_slot`)
- blog-day saturation when the target UTC day already meets the interim maximum Flow A blog items per day (default 1) (`calendar_schedule_saturation`)
- unsupported publication/calendar states (`calendar_schedule_unsupported_state`)

When `editorial-calendar/calendar.json` is missing or invalid, the endpoint MUST fail with the existing calendar missing/invalid semantics and MUST NOT create a calendar file solely to accept a schedule edit.

#### Scenario: Past due time is rejected

- **WHEN** `new_due_at_utc` is not strictly in the future
- **THEN** the worker returns `calendar_schedule_time_invalid` (or equivalent stable code) and `calendar.json` is unchanged

#### Scenario: Completed item is read-only for schedule

- **WHEN** the target item has `status` `completed`
- **THEN** the worker rejects the update with `calendar_schedule_unsupported_state` (or equivalent) and does not change `due_at_utc`

#### Scenario: Duplicate blog day slot is rejected

- **WHEN** another blog calendar item already occupies the UTC day of `new_due_at_utc` under interim one-blog-per-day rules
- **THEN** the worker returns `calendar_schedule_duplicate_slot` or `calendar_schedule_saturation` and does not mutate the calendar

### Requirement: Calendar schedule-update persistence, conflict protection, and dry-run

When `dry_run` is `true`, the worker MUST validate eligibility and rules and MUST return previous and proposed `due_at_utc` without writing `calendar.json`.

When `dry_run` is `false` and validation succeeds, the worker MUST set the item’s `due_at_utc` to `new_due_at_utc`, update calendar `updated_at_utc`, and persist via existing `save_calendar_atomic` semantics.

When `expected_calendar_fingerprint` is supplied, the worker MUST enforce the same concurrent-update protection as `save_calendar_atomic` and MUST return `calendar_completion_concurrent_update` without overwriting concurrent changes when the fingerprint no longer matches.

Successful real updates MUST NOT claim LinkedIn API published and MUST NOT equate calendar status changes with LinkedIn publication.

#### Scenario: Dry-run does not write calendar.json

- **WHEN** `POST /editorial-calendar/update-item-schedule` runs with `dry_run` true for an eligible item
- **THEN** `calendar.json` bytes remain unchanged and the response includes previous and proposed due times

#### Scenario: Real update persists new due_at_utc atomically

- **WHEN** `POST /editorial-calendar/update-item-schedule` runs with `dry_run` false for an eligible item and a matching fingerprint
- **THEN** the item’s `due_at_utc` becomes `new_due_at_utc` and the calendar is replaced atomically

#### Scenario: Concurrent calendar modification is not overwritten

- **WHEN** a real schedule update supplies an `expected_calendar_fingerprint` that no longer matches on-disk `calendar.json`
- **THEN** the worker returns `calendar_completion_concurrent_update`, does not replace the calendar, and leaves concurrent changes intact

### Requirement: Calendar schedule-change audit and idempotency

Real successful schedule updates MUST persist a traceable audit record for the change including at least:

- actor and/or source when supplied (console SHOULD supply `source=linkedin_variant_supervision_console`)
- timestamp UTC
- previous `due_at_utc`
- new `due_at_utc`
- reason when supplied
- idempotency key when supplied
- worker result status

When `idempotency_key` is provided and a prior successful non-dry-run operation used the same key with an identical payload fingerprint, replay MUST return completed success without appending a duplicate audit entry and without a second divergent write.

When `idempotency_key` is provided but the payload differs from the stored proof, the operation MUST fail with a stable idempotency conflict code and MUST NOT mutate the calendar.

#### Scenario: Audit record captures previous and new due times

- **WHEN** a real schedule update succeeds
- **THEN** the persisted audit includes previous `due_at_utc`, new `due_at_utc`, timestamp, and any supplied reason/actor/source/idempotency key

#### Scenario: Idempotent replay does not duplicate audit

- **WHEN** the same `idempotency_key` and identical payload are submitted twice with `dry_run` false
- **THEN** the second call returns completed without a second audit entry for that key
