## MODIFIED Requirements

### Requirement: Campaign preconditions for package generation

The campaign MUST have a non-null, non-empty `source_public_url` that was publish-confirmed by blog publish flow.

The source Markdown file MUST exist on disk at the campaign's active source path: `processed_source_relative_path` when `source_file_status.location` is `processed`; `queued_source_relative_path` when `location` is `queued` or `execution_state` is `processing` or `stale`; otherwise `source_relative_path` under `blog-posts/ready/` for legacy paths.

Campaign lookup by `source_relative_path` MUST match `original_source_relative_path`, `queued_source_relative_path`, `processed_source_relative_path`, or active `source_relative_path`.

The current source file SHA-256 MUST match stored `source_content_sha256` in campaign metadata.

Package generation MUST be rejected when:

- campaign metadata does not exist (`linkedin_package_campaign_not_found`)
- `flow` is not `flow_a` (`linkedin_package_flow_not_allowed`)
- `state` is before `blog_published` (`linkedin_package_invalid_campaign_state`)
- `state` is beyond `derivatives_generated` in a way that would regress lifecycle (`distribution_scheduled`, `distribution_complete`, `flow_a_complete`) unless idempotent rules explicitly allow (`linkedin_package_invalid_campaign_state`)
- `source_public_url` is missing (`linkedin_package_missing_source_public_url`)

#### Scenario: Package generation resolves queued source path

- **WHEN** package generation is requested by `campaign_id` for a campaign in `blog_published` with source Markdown only under `blog-posts/queued/` per metadata
- **THEN** generation proceeds using the queued path without requiring a `ready/` copy

#### Scenario: Package generation resolves processed source on idempotent re-run

- **WHEN** package generation is requested by `campaign_id` for a campaign in `derivatives_generated` with source Markdown only under `blog-posts/processed/` per metadata
- **THEN** idempotent behavior applies without requiring a `ready/` copy
