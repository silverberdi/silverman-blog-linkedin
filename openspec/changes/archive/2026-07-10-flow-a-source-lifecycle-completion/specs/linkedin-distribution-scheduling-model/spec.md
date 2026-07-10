## ADDED Requirements

### Requirement: Processed source path resolution for scheduling idempotency

When resolving a campaign by `source_relative_path`, `schedule_linkedin_distribution` MUST match `original_source_relative_path`, `processed_source_relative_path`, or active `source_relative_path` on the campaign document.

Idempotent re-run for campaigns in `distribution_scheduled` or later MUST NOT fail campaign resolution solely because the source Markdown is absent from `blog-posts/ready/` when `processed_source_relative_path` exists on disk.

Scheduling MUST continue to NOT relocate editorial source files; physical moves remain owned by `flow-a-source-lifecycle-completion`.

#### Scenario: Schedule idempotency by original ready path after move

- **WHEN** `schedule_linkedin_distribution` is called with `source_relative_path` equal to a campaign's `original_source_relative_path` after lifecycle completion
- **THEN** the campaign is resolved and idempotent already-scheduled behavior applies

#### Scenario: Schedule idempotency by campaign_id without ready copy

- **WHEN** `schedule_linkedin_distribution` is called with `campaign_id` for a campaign in `distribution_scheduled` whose source exists only under `blog-posts/processed/`
- **THEN** the operation returns idempotent completed/skipped outcome without campaign-not-found or source-missing errors attributable to ready-folder absence
