## MODIFIED Requirements

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
