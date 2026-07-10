## ADDED Requirements

### Requirement: Processed source resolution for idempotent publish

When campaign metadata indicates `source_file_status.location` is `processed` and `state` is `distribution_scheduled`, `distribution_complete`, or `flow_a_complete`, `publish_blog_post` MUST resolve the source Markdown path from `processed_source_relative_path` (falling back to `source_relative_path` when processed path is absent on legacy campaigns).

Campaign lookup by `source_relative_path` MUST match `original_source_relative_path`, `processed_source_relative_path`, or active `source_relative_path`.

Idempotent publish for post-schedule campaigns MUST NOT fail with `blog_publish_source_not_ready` solely because the Markdown file is absent from `blog-posts/ready/`.

`publish_blog_post` MUST continue to NOT perform physical source file moves; moves remain owned by `flow-a-source-lifecycle-completion`.

#### Scenario: Idempotent publish with processed source only

- **WHEN** `publish_blog_post` is called by `campaign_id` or original ready `source_relative_path` for a campaign in `distribution_scheduled` with source file only under `blog-posts/processed/`
- **THEN** the operation returns `status: completed` with `blog_publish.status` `already_published` without requiring the file in `blog-posts/ready/`

#### Scenario: Campaign lookup by original ready path after move

- **WHEN** `publish_blog_post` is called with `source_relative_path` equal to a campaign's `original_source_relative_path` after lifecycle completion
- **THEN** the campaign is resolved and idempotent behavior applies without `blog_publish_source_not_ready`
