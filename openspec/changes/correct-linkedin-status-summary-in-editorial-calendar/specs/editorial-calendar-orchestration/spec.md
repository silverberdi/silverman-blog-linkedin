## MODIFIED Requirements

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

When the target item is already `status=completed` with equivalent canonical completion facts except that stored `flow_a_completion.linkedin_package_status` and/or `flow_a_completion.linkedin_distribution_status` are `null` or missing while `completion_facts` supply non-null derived values and all other compared summary keys and canonical parent fields match, `complete_flow_a_calendar_item` MUST treat the update as a persistable repair mutation rather than `calendar_completion_facts_conflict`.

When stored LinkedIn summary values are non-null and differ from derived values in `completion_facts`, the function MUST fail with `calendar_completion_facts_conflict`.

#### Scenario: Null LinkedIn summaries repaired on already-completed item

- **WHEN** `complete_flow_a_calendar_item` is called for an item already `status=completed` whose stored `flow_a_completion` has null LinkedIn summary fields and `completion_facts` supply `linkedin_package_status` and `linkedin_distribution_status` both `completed` with all other compared fields matching
- **THEN** the function returns a persistable mutation with repaired LinkedIn summary fields and does not return `calendar_completion_facts_conflict`

#### Scenario: Conflicting non-null LinkedIn summaries fail closed

- **WHEN** `complete_flow_a_calendar_item` is called for an item already `status=completed` whose stored `flow_a_completion.linkedin_package_status` is a non-null value that differs from `completion_facts`
- **THEN** the function fails with `calendar_completion_facts_conflict` and does not produce a persistable mutation
