## MODIFIED Requirements

### Requirement: Campaign metadata required fields

Each campaign metadata document MUST include at minimum:

- `campaign_id`, `flow`, `state`, `created_at`, `updated_at`
- `source_slug`, `public_slug`, `source_relative_path`, `image_relative_path`
- `source_content_sha256`, `publication_date`
- `source_public_url` (nullable until publish-confirmed)
- `blog_publish` (object with idempotency key and publish status)
- `variants` (array of derivative variant records)
- `state_history` (array of transition records)
- `errors` and `warnings` (arrays)

After successful Flow A source lifecycle completion, the document MUST also include:

- `original_source_relative_path` (immutable ready-folder path once set)
- `processed_source_relative_path` (processed-folder path after move)
- `original_image_relative_path` and `processed_image_relative_path` when a companion image was moved

The document MAY include `source_file_status` for ready/processed/error marking and physical-move state.

#### Scenario: Initial campaign document shape

- **WHEN** a Flow A campaign is created for a ready post
- **THEN** all required top-level fields are present, `state` is `ready`, `variants` is an array (possibly empty), and `state_history` contains the initial transition

#### Scenario: Source fingerprint recorded without body

- **WHEN** campaign metadata is created from source Markdown bytes
- **THEN** `source_content_sha256` is a hex SHA-256 digest of the source content and no Markdown body field is stored in the campaign document

#### Scenario: Lifecycle completion adds path traceability fields

- **WHEN** Flow A source lifecycle completes successfully
- **THEN** campaign metadata includes `original_source_relative_path`, `processed_source_relative_path`, and optional image path fields while retaining `source_content_sha256`

### Requirement: Source file marking policy

Flow A source files SHALL be marked via `source_file_status`:

- `location` values: `ready`, `processed`, `error`
- `marked_processed_at` and `marked_error_at` timestamps
- `physical_move_completed_at` when physical move to `processed/` succeeds
- `physical_move_state` values: `none`, `completed`, `partial`, `failed` (when applicable)

Physical moves from `blog-posts/ready/` to `blog-posts/processed/` are performed by canonical spec `flow-a-source-lifecycle-completion` after successful distribution scheduling. Metadata marking and physical move MUST occur together on successful lifecycle completion.

Moves to `blog-posts/error/` remain metadata-first unless a future validation change adds physical error moves.

#### Scenario: Validation failure marks error in metadata

- **WHEN** validation fails for a Flow A campaign
- **THEN** `source_file_status.location` becomes `error` and `marked_error_at` is set without requiring physical move to `blog-posts/error/`

#### Scenario: Lifecycle completion marks processed in metadata and on disk

- **WHEN** Flow A source lifecycle completes successfully
- **THEN** `source_file_status.location` becomes `processed`, `marked_processed_at` and `physical_move_completed_at` are set, source files exist under `blog-posts/processed/`, and campaign `state` is `flow_a_complete`
