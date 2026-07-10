## MODIFIED Requirements

### Requirement: Processed source path resolution for scheduling idempotency

When resolving a campaign by `source_relative_path`, `schedule_linkedin_distribution` MUST match `original_source_relative_path`, `queued_source_relative_path`, `processed_source_relative_path`, or active `source_relative_path` on the campaign document.

Idempotent re-run for campaigns in `distribution_scheduled` or later MUST NOT fail campaign resolution solely because the source Markdown is absent from `blog-posts/ready/` when `processed_source_relative_path` exists on disk.

Idempotent scheduling for active Flow A campaigns MUST NOT fail campaign resolution solely because the source Markdown is absent from `blog-posts/ready/` when `queued_source_relative_path` exists on disk.

Scheduling MUST continue to NOT relocate editorial source files; physical moves remain owned by `flow-a-operational-queue-lifecycle` and `flow-a-source-lifecycle-completion`.

#### Scenario: Schedule idempotency by original ready path after move

- **WHEN** `schedule_linkedin_distribution` is called with `source_relative_path` equal to a campaign's `original_source_relative_path` after lifecycle completion
- **THEN** the campaign is resolved and idempotent already-scheduled behavior applies

#### Scenario: Schedule idempotency by campaign_id without ready copy

- **WHEN** `schedule_linkedin_distribution` is called with `campaign_id` for a campaign in `distribution_scheduled` whose source exists only under `blog-posts/processed/`
- **THEN** the campaign is resolved and idempotent already-scheduled behavior applies without requiring `blog-posts/ready/`

#### Scenario: Schedule resolves queued source during active Flow A

- **WHEN** `schedule_linkedin_distribution` is called for a campaign whose source exists only under `blog-posts/queued/` during an in-progress Flow A execution
- **THEN** scheduling proceeds without campaign resolution failure due to missing `ready/` copy
