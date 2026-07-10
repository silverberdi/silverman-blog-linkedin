## MODIFIED Requirements

### Requirement: File location and extension validation

The source file MUST be under `blog-posts/ready/` or `blog-posts/queued/` relative to the editorial base path depending on validation phase:

- Queue intake validation (acceptance boundary) MUST validate paths under `blog-posts/ready/` only.
- Full editorial validation during Flow A processing MUST validate paths under `blog-posts/queued/` when `source_file_status.location` is `queued`.

The source file MUST have extension `.md`.

The filename (without extension) MUST yield a valid `source_slug` safe as a single path segment (lowercase alphanumeric segments separated by hyphens; no path separators or `..`).

A numeric ordering prefix in the filename is allowed in `source_slug` (for example `01-why-i-did-not-start-with-the-database`).

The derived `public_slug` MUST strip a leading numeric prefix matching `^\d+-` when present and MUST match `^[a-z0-9]+(?:-[a-z0-9]+)*$`.

#### Scenario: Valid ready path and slugs

- **WHEN** source file is `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`
- **THEN** `source_slug` is `01-why-i-did-not-start-with-the-database`, `public_slug` is `why-i-did-not-start-with-the-database`, and no `invalid_public_slug` error is recorded

#### Scenario: Valid queued path during processing validation

- **WHEN** `validate_ready_post` is called with `blog-posts/queued/01-why-i-did-not-start-with-the-database.md` during Flow A processing
- **THEN** validation proceeds with the same slug rules and returns structured results without requiring the file to be in `ready/`

#### Scenario: File not under ready or queued folder

- **WHEN** `source_relative_path` is `blog-posts/processed/post.md`
- **THEN** validation fails with error code `ready_post_not_under_ready` or equivalent queued-path error code

#### Scenario: Non-markdown extension

- **WHEN** `source_relative_path` is `blog-posts/ready/post.txt`
- **THEN** validation fails with error code `ready_post_not_markdown`

#### Scenario: Missing source file

- **WHEN** the resolved path does not exist or is not a readable file
- **THEN** validation fails with error code `ready_post_missing`

#### Scenario: Invalid public slug after prefix strip

- **WHEN** filename strips to an invalid `public_slug`
- **THEN** validation fails with error code `invalid_public_slug`
