# linkedin-article-preview-image-support Specification

## Purpose
TBD - created by archiving change linkedin-article-preview-image-support. Update Purpose after archive.
## Requirements
### Requirement: Umbrella and dependency references

This change SHALL implement LinkedIn article preview **metadata** support as a worker capability consumed during Flow A package generation (`POST /generate-linkedin-package`).

Implementation MUST integrate with canonical spec `linkedin-derivative-package-generation` and worker module `linkedin_package_flow.py`.

Preview metadata MUST derive from blog front matter `image`, publish-confirmed `source_public_url`, and public blog path conventions per `github-pages-blog-publishing`.

Optional public image existence validation MUST use configured `SILVERMAN_GITHUB_PAGES_REPO_PATH` when set.

This capability MUST NOT call LinkedIn API endpoints, require LinkedIn OAuth tokens, or upload media to LinkedIn.

Flow B campaigns MUST NOT enter this preview metadata path.

#### Scenario: Child change cites package generation dependencies

- **WHEN** this capability is documented or implemented
- **THEN** it references `linkedin-derivative-package-generation`, `github-pages-blog-publishing`, and `flow-a-automatic-publishing`

#### Scenario: No LinkedIn API boundary

- **WHEN** article preview metadata is resolved during package generation
- **THEN** no request is made to `api.linkedin.com` and no LinkedIn access token is read

### Requirement: Article preview metadata entry point

The worker SHALL expose an article preview metadata entry point (for example `resolve_linkedin_article_preview(base_path, *, campaign_metadata, source_relative_path, site_base_url=None, public_repo_path=None)`) that returns a structured `LinkedInArticlePreviewMetadata` (or equivalent) serializable to JSON.

The entry point MUST NOT call LinkedIn Posts API or LinkedIn Images API.

The entry point MUST NOT mutate variant `publish_state` or scheduling metadata.

The entry point MUST NOT move editorial source files or run git operations.

The entry point MUST NOT perform OG metadata HTTP fetch of the live blog page.

#### Scenario: Resolve preview metadata without LinkedIn API

- **WHEN** package generation invokes the entry point for a Flow A campaign with valid front matter `image` and `source_public_url`
- **THEN** the result includes `public_image_path`, `public_image_url`, `public_url`, and `status` without LinkedIn API calls

#### Scenario: Entry point is read-only for lifecycle

- **WHEN** preview resolution runs during package generation
- **THEN** campaign `state` and variant `publish_state` are unchanged by preview resolution alone

### Requirement: Preview image path and URL resolution

The worker MUST resolve `public_image_path` from blog front matter `image` when it is a site-root-relative path matching `/assets/images/<public_slug>.png` (lowercase slug segments, `.png` extension).

The worker MUST resolve `public_image_url` as `{site_base_url}{public_image_path}` where `site_base_url` defaults to `https://silverman.pro` or configured publish site URL without trailing slash.

The worker MUST copy publish-confirmed `source_public_url` into preview metadata as `public_url`.

The worker SHOULD copy blog `title` and `description` (or excerpt equivalent) into `article_title` and `article_description` when present in front matter.

When front matter `image` is missing or cannot be parsed into the canonical path pattern, status MUST be `missing` with stable code `linkedin_article_preview_image_missing`.

When front matter `image` is present but fails canonical path validation, status MUST be `invalid` with stable code `linkedin_article_preview_image_invalid`.

#### Scenario: Resolve absolute URL from canonical front matter path

- **WHEN** front matter `image` is `/assets/images/my-slug.png` and site base is `https://silverman.pro`
- **THEN** `public_image_url` is `https://silverman.pro/assets/images/my-slug.png` and `public_image_path` is `/assets/images/my-slug.png`

#### Scenario: Missing image path

- **WHEN** blog front matter has no `image` field or empty `image`
- **THEN** status is `missing` and stable code `linkedin_article_preview_image_missing` applies

#### Scenario: Invalid image path pattern

- **WHEN** front matter `image` is `/images/wrong.png` or an absolute external URL
- **THEN** status is `invalid` and stable code `linkedin_article_preview_image_invalid` applies

### Requirement: Public repo image existence validation

When `SILVERMAN_GITHUB_PAGES_REPO_PATH` (or equivalent configured public blog repo checkout path) is set, the worker MUST verify that `{public_repo_path}/assets/images/<public_slug>.png` exists and is a readable file before setting status `available`.

When the path is configured and the file is missing or not readable, status MUST be `missing` with stable code `linkedin_article_preview_public_image_missing`.

When the public repo path is not configured, status MUST be `skipped` and the worker MUST still resolve `public_image_path` and `public_image_url` from front matter when valid.

#### Scenario: Available when public file exists

- **WHEN** front matter path is valid, public repo path is configured, and matching PNG exists under `assets/images/`
- **THEN** status is `available`

#### Scenario: Missing public file when repo configured

- **WHEN** front matter path is valid, public repo path is configured, and matching PNG does not exist
- **THEN** status is `missing` with `linkedin_article_preview_public_image_missing`

#### Scenario: Skipped when repo not configured

- **WHEN** public repo path is not configured and front matter path is valid
- **THEN** status is `skipped` and `public_image_url` is still populated

### Requirement: Preview status values

Article preview metadata MUST use exactly these `status` values:

| Status | Meaning |
|--------|---------|
| `available` | Valid front matter path and public repo file exists when repo path configured |
| `missing` | Image path missing, or public repo file missing when repo path configured |
| `skipped` | Public repo path not configured; URL/path metadata still resolved when valid |
| `invalid` | Front matter `image` present but fails canonical path validation |

#### Scenario: Status available

- **WHEN** validation preconditions for `available` are met
- **THEN** `status` is `available`

#### Scenario: Status skipped without repo

- **WHEN** public repo path is unset and front matter path is valid
- **THEN** `status` is `skipped`

### Requirement: Package and variant preview metadata

For successful package generation, campaign metadata `linkedin_package` MUST include an `article_preview` object with at minimum:

- `status`
- `public_image_url` (when resolved)
- `public_image_path` (when resolved)
- `public_url` (publish-confirmed blog URL)
- `article_title` (when available)
- `article_description` (when available)
- `error_code` (when status is not `available` and a stable code applies)

Each generated `variants[]` entry SHOULD include per-variant preview summary fields at minimum:

- `article_preview_status` (same values as package `status`)
- `public_image_url` (when resolved)
- `public_image_path` (when resolved)
- `public_url`
- `article_title` and `article_description` (when available)

Metadata MUST NOT include image bytes, OAuth tokens, or variant body text.

HTTP `POST /generate-linkedin-package` responses MUST include top-level `article_preview` and per-variant preview summary fields consistent with campaign metadata.

Incomplete preview metadata MUST NOT cause package generation `status` `failed` when variant generation otherwise succeeds; warnings MUST carry stable codes instead.

#### Scenario: Package records article_preview on success

- **WHEN** package generation completes with `status` `completed`
- **THEN** campaign `linkedin_package.article_preview` and HTTP response `article_preview` are populated

#### Scenario: Incomplete preview warns but completes

- **WHEN** preview status is `missing` and variant artifacts are generated successfully
- **THEN** package `status` is `completed`, `warnings[]` includes the stable preview code, and variant `publish_state` is not written

### Requirement: Stable warning codes

Article preview metadata support MUST use stable warning/error codes including at minimum:

- `linkedin_article_preview_image_missing`
- `linkedin_article_preview_image_invalid`
- `linkedin_article_preview_public_image_missing`
- `linkedin_article_preview_public_repo_not_configured` (informational when documenting skipped validation only in logs/docs; MAY appear in warnings when useful)

#### Scenario: Stable codes in warnings

- **WHEN** preview status is `missing` because public file is absent
- **THEN** `warnings[]` contains `linkedin_article_preview_public_image_missing`

### Requirement: Test coverage

The repository MUST include tests for article preview metadata with no LinkedIn API, covering at minimum:

- `available` when front matter and public file exist
- `missing` when public file absent with repo configured
- `skipped` when repo path unset
- `invalid` for non-canonical front matter paths
- absolute `public_image_url` normalization
- package generation still `completed` with preview warnings
- no live LinkedIn API in default `pytest` runs

#### Scenario: Preview metadata tests pass without LinkedIn

- **WHEN** `pytest` runs after apply
- **THEN** preview metadata tests pass without network calls to `api.linkedin.com`

### Requirement: Safety and orchestration boundaries

This change MUST NOT activate n8n workflows, cron jobs, or automatic LinkedIn publication.

This change MUST NOT modify `publish_linkedin_due_variants()` behavior.

This change MUST NOT add `SILVERMAN_LINKEDIN_PREVIEW_*` publication configuration.

This change MUST NOT upload image bytes to LinkedIn.

#### Scenario: No publish-due side effects

- **WHEN** this change is applied
- **THEN** `POST /publish-linkedin-due-variants` behavior is unchanged from pre-change text-only publication semantics

