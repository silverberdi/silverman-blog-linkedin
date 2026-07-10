## MODIFIED Requirements

### Requirement: Campaign eligibility for package generation

Package generation MUST require an existing campaign metadata document at `metadata/campaigns/<campaign-id>.json`.

The campaign MUST have `flow` `flow_a`.

The campaign `state` MUST be `blog_published`, `derivatives_pending`, or `derivatives_generated` (idempotent re-run only when idempotency rules below match).

The campaign MUST have a non-null, non-empty `source_public_url` that was publish-confirmed by blog publish flow.

The source Markdown file MUST exist on disk at the campaign's active source path: `processed_source_relative_path` when `source_file_status.location` is `processed`, otherwise `source_relative_path` under `blog-posts/ready/`.

Campaign lookup by `source_relative_path` MUST match `original_source_relative_path`, `processed_source_relative_path`, or active `source_relative_path`.

The current source file SHA-256 MUST match stored `source_content_sha256` in campaign metadata.

Package generation MUST be rejected when:

- campaign metadata does not exist (`linkedin_package_campaign_not_found`)
- `flow` is not `flow_a` (`linkedin_package_flow_not_allowed`)
- `state` is before `blog_published` (`linkedin_package_invalid_campaign_state`)
- `state` is beyond `derivatives_generated` in a way that would regress lifecycle (`distribution_scheduled`, `distribution_complete`, `flow_a_complete`) unless idempotent rules explicitly allow (`linkedin_package_invalid_campaign_state`)
- `source_public_url` is missing (`linkedin_package_missing_source_public_url`)
- source file is missing at resolved active path (`linkedin_package_source_missing`)
- source content hash differs from stored hash (`linkedin_package_source_hash_changed`)
- stored `source_public_url` differs from request-supplied override without metadata proof of same campaign/package (`linkedin_package_public_url_changed`)

#### Scenario: Campaign not found

- **WHEN** package generation is requested for a `campaign_id` with no metadata file
- **THEN** the operation fails with `linkedin_package_campaign_not_found`

#### Scenario: State before blog_published rejected

- **WHEN** package generation is requested for a campaign in state `validated`
- **THEN** the operation fails with `linkedin_package_invalid_campaign_state`

#### Scenario: Missing source_public_url rejected

- **WHEN** package generation is requested for a `blog_published` campaign with `source_public_url` null
- **THEN** the operation fails with `linkedin_package_missing_source_public_url`

#### Scenario: Source hash changed rejected

- **WHEN** the on-disk source Markdown hash differs from campaign `source_content_sha256`
- **THEN** the operation fails with `linkedin_package_source_hash_changed`

#### Scenario: Idempotent package with processed source only

- **WHEN** package generation is requested by `campaign_id` for a campaign in `derivatives_generated` with source Markdown only under `blog-posts/processed/` per metadata
- **THEN** idempotent completion succeeds without `linkedin_package_source_missing` solely due to absent ready copy
