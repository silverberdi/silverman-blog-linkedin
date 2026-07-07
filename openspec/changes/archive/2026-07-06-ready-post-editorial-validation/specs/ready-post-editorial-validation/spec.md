## ADDED Requirements

### Requirement: Umbrella and policy references

This child change SHALL implement Flow A ready-post editorial validation under active umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 3).

Validation rules MUST align with Flow A policy in canonical spec `editorial-canon` and artifact `content-strategy/silverman-editorial-system.md`.

Campaign metadata integration MUST use canonical spec `flow-a-lifecycle` and worker module `campaign_lifecycle.py`.

Slug and public URL derivation MUST align with `github-pages-blog-publishing` rules via existing publish bridge helpers.

For Flow A user-provided ready posts, anti-AI editorial heuristics MUST be warnings by default and MUST NOT alone block validation.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, editorial canon, and lifecycle child `flow-a-lifecycle-and-duplicate-prevention`

#### Scenario: Flow A anti-AI checks are non-blocking alone

- **WHEN** a ready post passes all structural and content blocking checks but triggers anti-AI heuristics
- **THEN** validation returns `ok: true` with non-empty `warnings[]` and does not transition to `validation_failed` solely for warnings

### Requirement: Validation entry point

The worker SHALL expose a pure validation entry point (for example `validate_ready_post(base_path, source_relative_path)`) that validates one ready blog post without publishing or moving files.

The entry point MUST return a structured `ReadyPostValidationResult` (or equivalent dataclass) serializable to JSON for future HTTP and n8n consumers.

#### Scenario: Validate by relative path

- **WHEN** `validate_ready_post` is called with `source_relative_path` `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` and a valid editorial base path
- **THEN** the function returns a result including `source_relative_path`, slug fields, and validation outcome without modifying file locations on disk

#### Scenario: No HTTP endpoint in this change

- **WHEN** this child change is applied
- **THEN** no new FastAPI route is required; validation is callable as a library module and covered by unit tests

### Requirement: File location and extension validation

The source file MUST be under `blog-posts/ready/` relative to the editorial base path.

The source file MUST have extension `.md`.

The filename (without extension) MUST yield a valid `source_slug` safe as a single path segment (lowercase alphanumeric segments separated by hyphens; no path separators or `..`).

A numeric ordering prefix in the filename is allowed in `source_slug` (for example `01-why-i-did-not-start-with-the-database`).

The derived `public_slug` MUST strip a leading numeric prefix matching `^\d+-` when present and MUST match `^[a-z0-9]+(?:-[a-z0-9]+)*$`.

#### Scenario: Valid ready path and slugs

- **WHEN** source file is `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`
- **THEN** `source_slug` is `01-why-i-did-not-start-with-the-database`, `public_slug` is `why-i-did-not-start-with-the-database`, and no `invalid_public_slug` error is recorded

#### Scenario: File not under ready folder

- **WHEN** `source_relative_path` is `blog-posts/processed/post.md`
- **THEN** validation fails with error code `ready_post_not_under_ready`

#### Scenario: Non-markdown extension

- **WHEN** `source_relative_path` is `blog-posts/ready/post.txt`
- **THEN** validation fails with error code `ready_post_not_markdown`

#### Scenario: Missing source file

- **WHEN** the resolved path does not exist or is not a readable file
- **THEN** validation fails with error code `ready_post_missing`

#### Scenario: Invalid public slug after prefix strip

- **WHEN** filename produces a `public_slug` that fails `^[a-z0-9]+(?:-[a-z0-9]+)*$`
- **THEN** validation fails with error code `invalid_public_slug`

### Requirement: Image validation

The expected companion image MUST be exactly `blog-posts/ready/<source_slug>.png` — same basename as the Markdown file with `.png` extension.

Example: `blog-posts/ready/01-why-i-did-not-start-with-the-database.png` for source `01-why-i-did-not-start-with-the-database.md`.

Image extension MUST be `.png` for Flow A (current publishing bridge expects PNG).

When the expected `.png` is missing:

- If a same-basename file with a non-`.png` extension exists (for example `.jpg`, `.webp`), validation MUST fail with error code `ready_post_image_invalid_extension`.
- If no same-basename image file exists at all, validation MUST fail with error code `ready_post_image_missing`.

#### Scenario: Matching PNG present

- **WHEN** both `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` and `blog-posts/ready/01-why-i-did-not-start-with-the-database.png` exist
- **THEN** `image_relative_path` is `blog-posts/ready/01-why-i-did-not-start-with-the-database.png` and no image error is recorded

#### Scenario: Missing PNG with no same-basename image

- **WHEN** the Markdown file exists but no file with the same basename exists in `blog-posts/ready/` (neither `.png` nor any other extension)
- **THEN** validation fails with error code `ready_post_image_missing`

#### Scenario: Non-PNG same-basename image only

- **WHEN** the Markdown file exists, the expected `.png` is absent, but a same-basename `.jpg` or other non-`.png` image exists (for example `blog-posts/ready/01-why-i-did-not-start-with-the-database.jpg`)
- **THEN** validation fails with error code `ready_post_image_invalid_extension` and NOT `ready_post_image_missing`

### Requirement: Frontmatter validation

The Markdown file MUST contain parseable YAML frontmatter.

Required fields MUST be present and valid:

| Field | Rule |
|-------|------|
| `title` | Non-empty string |
| `audience` | Non-empty string |
| `type` | Must be `blog-post` |
| `language` | Must be `en` |
| `layout` | Must be `post` |
| `date` | Parseable; MUST yield `YYYY-MM-DD` publication date |
| `categories` | Non-empty array |
| `tags` | Non-empty array |
| `description` | Non-empty string |
| `image` | Must equal `/assets/images/<public_slug>.png` |

#### Scenario: Valid frontmatter

- **WHEN** frontmatter includes all required fields with expected values and `image` `/assets/images/why-i-did-not-start-with-the-database.png` for `public_slug` `why-i-did-not-start-with-the-database`
- **THEN** no `frontmatter_required_field_missing` or `frontmatter_invalid` errors are recorded and `publication_date` is extracted as `YYYY-MM-DD`

#### Scenario: Missing frontmatter block

- **WHEN** the file has no YAML frontmatter delimiters
- **THEN** validation fails with error code `frontmatter_missing`

#### Scenario: Unparseable frontmatter

- **WHEN** frontmatter YAML is invalid
- **THEN** validation fails with error code `frontmatter_invalid`

#### Scenario: Missing required field

- **WHEN** a required field such as `audience` or `tags` is absent or empty
- **THEN** validation fails with error code `frontmatter_required_field_missing`

#### Scenario: Invalid date

- **WHEN** `date` cannot be parsed to a valid `YYYY-MM-DD`
- **THEN** validation fails with error code `frontmatter_invalid_date`

#### Scenario: Invalid image path

- **WHEN** `image` does not match `/assets/images/<public_slug>.png`
- **THEN** validation fails with error code `frontmatter_invalid_image`

### Requirement: Content validation blocking rules

The following content issues MUST block validation (`ok: false`):

- Empty body after frontmatter (`ready_post_empty`)
- Missing H1 title in body (`content_missing_h1`)
- H1 title does not reasonably match frontmatter `title` (`content_title_mismatch`)
- Placeholder or TODO markers in body or frontmatter (`content_contains_todo`)
- Raw secrets or API key patterns (`content_contains_secret_marker`)
- Unsupported local image references in body (for example `![](...)` pointing to non-canonical paths) (`content_unsupported_local_image` or equivalent stable code documented in module)
- Direct instruction to publish to a non-Silverman URL (`content_non_silverman_publish_target`)
- Full generated LinkedIn draft embedded in metadata or content artifacts (`content_embedded_linkedin_draft`)

#### Scenario: Empty body blocks

- **WHEN** frontmatter is valid but body after frontmatter is empty or whitespace only
- **THEN** validation fails with error code `ready_post_empty`

#### Scenario: Missing H1 blocks

- **WHEN** body has content but no line starting with `# ` H1 heading
- **THEN** validation fails with error code `content_missing_h1`

#### Scenario: Title mismatch blocks

- **WHEN** H1 text is substantially different from frontmatter `title`
- **THEN** validation fails with error code `content_title_mismatch`

#### Scenario: TODO marker blocks

- **WHEN** body or frontmatter contains `TODO`, `FIXME`, or project-defined placeholder markers
- **THEN** validation fails with error code `content_contains_todo`

### Requirement: Content validation warning rules for Flow A

The following editorial patterns MUST produce warning codes in `warnings[]` without alone failing validation for Flow A user-provided posts when detected:

- AI-sounding opening patterns (for example "In today's fast-paced world")
- Generic engagement-bait endings (for example "What are your thoughts?")
- Excessive generic transitions (for example repeated "Moreover", "Furthermore")
- Weak or missing CTA relative to editorial canon
- Overly polished influencer tone indicators
- Minor style drift from Silverio writing style heuristics

Warning codes MUST be stable strings recorded in the validation result and campaign metadata `warnings[]` on success.

#### Scenario: AI-sounding opening yields warning only

- **WHEN** post is otherwise valid but opens with a forbidden AI-sounding pattern from editorial canon
- **THEN** `ok` is `true`, `warnings` contains an appropriate warning code, and `state` becomes `validated` when metadata is written

#### Scenario: Warnings recorded in campaign metadata on success

- **WHEN** validation succeeds with one or more warnings
- **THEN** campaign metadata `warnings[]` includes those warning codes after transition to `validated`

### Requirement: Campaign metadata integration

On validation when `publication_date` and `public_slug` are derivable, the worker MUST create or update `metadata/campaigns/<campaign-id>.json` using lifecycle helpers.

Campaign ID MUST follow `flow-a-YYYY-MM-DD-<public-slug>`.

Campaign `flow` MUST be `flow_a`.

Campaign MUST include `source_content_sha256` computed via `compute_source_content_sha256` from lifecycle module.

Metadata-only state transitions:

- Success: `ready` → `validated`
- Failure: `ready` → `validation_failed`

Validation failure MUST append blocking error codes to campaign metadata `errors[]` via lifecycle transition rules.

Validation MUST NOT physically move source files in this child.

On `validation_failed`, lifecycle helpers MUST mark metadata-only error state (`source_file_status.location` = `error`).

**Existing campaign metadata behavior:**

- When campaign metadata already exists in `ready` state, validation MAY transition to `validated` or `validation_failed` per outcome.
- When campaign metadata already exists in `validated` state and `source_content_sha256` matches the stored hash, validation MUST be idempotent: return `ok: true` without appending duplicate state history entries.
- When campaign metadata already exists with a different `source_content_sha256` than the current ready post content, validation MUST fail with error code `campaign_content_hash_changed` and MUST NOT silently overwrite metadata; reset/revalidation behavior is deferred to a later child.
- When campaign metadata already exists in a state beyond `validated` (for example `blog_published`, `derivatives_generated`), validation MUST NOT silently overwrite or regress the campaign; return blocking error `campaign_invalid_existing_state`.

Future `worker-blog-publishing-endpoint` depends on idempotent re-validation when campaign is already `validated` with unchanged content.

#### Scenario: Successful validation transitions campaign

- **WHEN** all blocking checks pass for a new ready post with `publication_date` `2026-07-06` and `public_slug` `why-i-did-not-start-with-the-database`
- **THEN** campaign ID `flow-a-2026-07-06-why-i-did-not-start-with-the-database` is created or updated, `state` becomes `validated`, and `metadata_written` is `true`

#### Scenario: Failed validation transitions campaign from ready

- **WHEN** a blocking check fails after campaign metadata exists in `ready` state
- **THEN** campaign transitions to `validation_failed` with `errors[]` containing stable error codes and `metadata_written` is `true` when persistence succeeds

#### Scenario: Idempotent re-validation when already validated with same content hash

- **WHEN** campaign metadata exists in `validated` state and `source_content_sha256` matches the current ready post content
- **THEN** validation returns `ok: true`, `state` remains `validated`, and no duplicate state history entry is appended

#### Scenario: Content hash changed on existing campaign

- **WHEN** campaign metadata exists and stored `source_content_sha256` differs from the hash computed for the current ready post
- **THEN** validation fails with error code `campaign_content_hash_changed`, does not overwrite progressed metadata, and `metadata_written` is `false` or records explicit metadata error per lifecycle rules

#### Scenario: Campaign already progressed beyond validated

- **WHEN** campaign metadata exists in a state beyond `validated` (for example `blog_published`)
- **THEN** validation fails with error code `campaign_invalid_existing_state` and does not modify campaign state or history

#### Scenario: Metadata write failure surfaces in result

- **WHEN** `metadata/campaigns/` is not writable
- **THEN** result includes `metadata_written: false` and `metadata_error_code` from lifecycle write result (for example `metadata_campaigns_not_writable` or `campaign_metadata_write_failed`)

### Requirement: Validation result shape

The validation result MUST include at minimum:

- `ok` (boolean)
- `campaign_id` (string or null)
- `state` (string or null)
- `source_slug` (string or null)
- `public_slug` (string or null)
- `publication_date` (string or null, `YYYY-MM-DD`)
- `source_relative_path` (string)
- `image_relative_path` (string or null)
- `source_content_sha256` (string or null)
- `source_public_url` (string or null when derivable)
- `errors` (list of stable error code strings)
- `warnings` (list of stable warning code strings)
- `metadata_written` (boolean)
- `metadata_error_code` (string or null)

When `publication_date` and `public_slug` are valid, `source_public_url` MUST follow the site URL pattern used by the GitHub Pages publishing bridge (for example `https://silverman.pro/YYYY/MM/DD/<public_slug>/`).

#### Scenario: Full success result fields

- **WHEN** validation passes for the canonical slug example with date `2026-07-06`
- **THEN** result has `ok: true`, populated slug fields, `source_public_url` ending in `/why-i-did-not-start-with-the-database/`, empty `errors`, and `metadata_written: true` when campaigns folder is writable

#### Scenario: Failure result includes error codes

- **WHEN** validation fails due to missing image
- **THEN** result has `ok: false`, `errors` containing `ready_post_image_missing`, and `state` `validation_failed` when metadata transition completes

### Requirement: Stable blocking error codes

The implementation MUST use stable machine-readable blocking error codes including at minimum:

- `ready_post_not_under_ready`
- `ready_post_not_markdown`
- `ready_post_missing`
- `ready_post_empty`
- `frontmatter_missing`
- `frontmatter_invalid`
- `frontmatter_required_field_missing`
- `frontmatter_invalid_date`
- `frontmatter_invalid_image`
- `invalid_public_slug`
- `ready_post_image_missing`
- `ready_post_image_invalid_extension`
- `content_missing_h1`
- `content_title_mismatch`
- `content_contains_todo`
- `content_contains_secret_marker`
- `campaign_content_hash_changed`
- `campaign_invalid_existing_state`
- `campaign_metadata_write_failed`

Additional blocking codes for content rules (local images, non-Silverman publish targets, embedded LinkedIn drafts) MUST be documented in the worker module and covered by tests.

#### Scenario: Error codes are stable strings

- **WHEN** the same validation failure is triggered twice
- **THEN** the same error code string appears in `errors[]` both times

### Requirement: Worker module and tests

The worker MUST implement validation in a module such as `src/silverman_blog_linkedin/ready_post_validation.py`.

The repository MUST include tests such as `tests/test_ready_post_validation.py` covering:

- Canonical slug example pass path
- Each major blocking error category
- Warning-only anti-AI path
- Campaign metadata success and failure transitions
- Metadata write failure handling

#### Scenario: Tests run in CI/local pytest

- **WHEN** `pytest tests/test_ready_post_validation.py` runs
- **THEN** scenarios for blocking errors, warnings, and metadata integration pass without network access
