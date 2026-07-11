## MODIFIED Requirements

### Requirement: Flow A calendar completion after lifecycle success

When `dry_run` is `false` and a due Flow A item completes the full execution contract — queue acceptance, processing claim, `publish_blog_post` (including image remediation, hash reconciliation, full validation, public handoff, and blog publication), `generate_linkedin_package`, `schedule_linkedin_distribution`, and `complete_flow_a_source_lifecycle` with campaign `state=flow_a_complete` and `source_file_status.location=processed` — the connector MUST persist terminal calendar state for that item.

Calendar completion MUST occur only after lifecycle completion succeeds. It MUST NOT run after scheduling alone, after publish alone, or when `source_lifecycle_status` is `failed`.

The connector MUST call `complete_flow_a_calendar_item` followed by `save_calendar_atomic` only when `complete_flow_a_calendar_item` indicates a persistable mutation.

The persisted item MUST have canonical fields `status=completed`, preserved original `source_relative_path`, resolved `campaign_id`, `completed_at_utc`, `processed_source_relative_path`, and `flow_a_completion` summary evidence. `notes` MUST remain byte-for-byte unchanged.

The `flow_a_completion` summary MUST record `campaign_state`, `execution_status`, `source_lifecycle_status`, `blog_publish_status`, `public_url` when available, `linkedin_package_status`, and `linkedin_distribution_status`. It MUST NOT duplicate parent-item canonical fields. It MUST NOT claim LinkedIn was published.

The connector MUST derive `linkedin_package_status` and `linkedin_distribution_status` from authoritative campaign metadata using shared derivation rules: `linkedin_package.package_status` and lifecycle state for package evidence; lifecycle state at or beyond `distribution_scheduled`, `linkedin_distribution` metadata, and top-level `variants[]` schedule evidence for scheduling. It MUST NOT read `linkedin_package.status` or `linkedin_distribution.status`.

For `flow_a_complete` campaigns with valid package and distribution evidence, derived LinkedIn summary statuses MUST be `completed`.

#### Scenario: Successful Flow A closes calendar item

- **WHEN** real execution completes lifecycle with campaign `flow_a_complete` and source under `blog-posts/processed/`
- **THEN** the matching calendar item becomes `status=completed` with completion fields persisted, `notes` unchanged, and original ready `source_relative_path` preserved

#### Scenario: Lifecycle failure does not complete calendar

- **WHEN** scheduling succeeds but `complete_flow_a_source_lifecycle` fails
- **THEN** the calendar item remains `scheduled` or `due` and is not marked `completed`

#### Scenario: Publish failure does not complete calendar

- **WHEN** `publish_blog_post` fails before lifecycle completion
- **THEN** the calendar item is not marked `completed`

#### Scenario: LinkedIn summary fields populated from campaign metadata

- **WHEN** real execution completes lifecycle for a campaign whose metadata includes `linkedin_package.package_status` `generated` and `linkedin_distribution` with `distribution_id`
- **THEN** persisted `flow_a_completion.linkedin_package_status` is `completed` and `flow_a_completion.linkedin_distribution_status` is `completed`

### Requirement: Authoritative campaign_id reconciliation

When reconciling a Flow A calendar item to terminal `completed`, the connector MUST use `campaign_id` as the authoritative reconciliation identity when the calendar item contains `campaign_id`.

The connector MUST:

1. Load exactly that campaign.
2. Verify the campaign exists, its ID matches exactly, its source/public identity is consistent with the calendar item, its state is `flow_a_complete`, its final source location is `processed`, and its lifecycle is complete.
3. Reconcile the calendar item to `status=completed` only after all checks pass.

The connector MUST NOT use `source_relative_path` as the normal reconciliation identity.

Reconciliation MUST set `calendar_update_status=reconciled`.

Reconciliation MUST populate canonical completion fields and `flow_a_completion` summary evidence from campaign metadata and persisted step results using the same LinkedIn summary derivation rules as post-execution completion.

When reconciling a **`scheduled` or `due`** calendar item to `completed`, persisted `flow_a_completion.linkedin_package_status` and `flow_a_completion.linkedin_distribution_status` MUST be non-null when the resolved `flow_a_complete` campaign has valid package and distribution metadata.

Reconciliation MUST NOT mutate `notes`.

Automatic HTTP reconciliation via `execute_due_editorial_calendar_flow_a` MUST NOT be required to repair calendar items already `status=completed` with null LinkedIn summaries; those items are excluded from due-item planning.

#### Scenario: Reconciliation by exact campaign_id without ready source

- **WHEN** a calendar item contains `campaign_id=flow-a-2026-07-10-a-bounded-context-is-not-a-folder`, the ready source no longer exists, and that campaign is `flow_a_complete` with processed lifecycle evidence
- **THEN** the executor reconciles the calendar item to `completed` using `campaign_id` alone

#### Scenario: Already completed calendar with equivalent facts is idempotent no-op

- **WHEN** campaign is `flow_a_complete` and the calendar item is already `status=completed` with equivalent canonical completion facts
- **THEN** the executor performs no Flow A side effects, performs no calendar-file write, preserves `completed_at_utc`, leaves `notes` unchanged, and reports `calendar_update_status=skipped_already_completed`

#### Scenario: Reconcile-close populates LinkedIn summary fields from realistic campaign metadata

- **WHEN** a calendar item is `status=scheduled` or `status=due`, reconciliation resolves a `flow_a_complete` campaign with `linkedin_package.package_status` `generated` and `linkedin_distribution.distribution_id` present, and `execute_due_editorial_calendar_flow_a` runs with `dry_run=false`
- **THEN** the executor performs no publish/package/schedule/lifecycle side effects, closes the item to `status=completed`, persists non-null `flow_a_completion.linkedin_package_status` and `flow_a_completion.linkedin_distribution_status` both `completed`, preserves `notes`, and reports `calendar_update_status=reconciled`
