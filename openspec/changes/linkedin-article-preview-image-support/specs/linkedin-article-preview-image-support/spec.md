## ADDED Requirements

### Requirement: Umbrella and dependency references

This change SHALL implement LinkedIn article/link preview image support as a worker capability consumed by Flow A LinkedIn publish-due.

Implementation MUST NOT begin until OpenSpec change `comfyui-blog-image-generation` is implemented, validated, and archived.

Preview behavior MUST assume canonical blog image prerequisites per `comfyui-blog-image-generation`: front matter `image` equals `/assets/images/<public_slug>.png` and public asset exists after blog publish.

LinkedIn publication integration MUST use canonical spec `linkedin-publication-integration` and worker modules `linkedin_publication_flow.py` and `linkedin_client.py`.

Publish-confirmed `source_public_url` MUST come from campaign metadata per `flow-a-automatic-publishing` and `github-pages-blog-publishing`.

Flow B campaigns MUST NOT enter LinkedIn preview image paths.

#### Scenario: Dependency gate blocks premature implementation

- **WHEN** `comfyui-blog-image-generation` is not archived
- **THEN** this capability MUST NOT be implemented in runtime code

#### Scenario: Child change cites publication dependencies

- **WHEN** this capability is documented or implemented
- **THEN** it references `linkedin-publication-integration`, `comfyui-blog-image-generation` (archived), and `github-pages-blog-publishing`

### Requirement: LinkedIn preview image service entry point

The worker SHALL expose a LinkedIn preview planning entry point (for example `plan_linkedin_preview(base_path, *, campaign_metadata, variant_record, config, og_client=None, image_client=None, dry_run=True)`) that resolves preview image URL/path, evaluates strategy, optionally validates OG metadata, and returns a structured `LinkedInPreviewPlan` (or equivalent) serializable to JSON.

The entry point MUST NOT call LinkedIn Posts API.

The entry point MUST NOT mutate variant `publish_state`.

The entry point MUST NOT move editorial source files or run git operations.

When `dry_run` is true, the entry point MUST return planned strategy and image resolution without LinkedIn Images API upload or post creation.

#### Scenario: Dry-run plans OG strategy when metadata sufficient

- **WHEN** preview is enabled, strategy is `og_metadata` or `auto`, `source_public_url` is live with sufficient `og:image`, `og:title`, `og:description`, and dry-run is true
- **THEN** the plan reports `preview_strategy: og_metadata`, `preview_image_url`, and `og_metadata_sufficient: true` without LinkedIn API calls

#### Scenario: Dry-run plans explicit upload when OG insufficient

- **WHEN** preview is enabled, strategy is `auto`, OG metadata is insufficient, public image URL is resolvable, and dry-run is true
- **THEN** the plan reports `preview_strategy: linkedin_explicit` and `preview_image_url` without performing upload

#### Scenario: Preview disabled returns text-only plan

- **WHEN** `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` is false
- **THEN** the plan reports preview disabled and defers to legacy text-only publication semantics

### Requirement: Preview image URL resolution

The worker MUST resolve `preview_image_path` from campaign or processed blog metadata as `/assets/images/<public_slug>.png` (site-root-relative, matching front matter `image`).

The worker MUST resolve `preview_image_url` as `{site_base_url}{preview_image_path}` where `site_base_url` defaults to `https://silverman.pro` or configured publish site URL without trailing slash.

Resolution MUST require publish-confirmed `source_public_url` on the campaign variant context.

When `preview_image_path` or resolvable public image URL is missing, planning MUST fail with stable error `linkedin_preview_image_missing`.

#### Scenario: Resolve image URL from canonical front matter path

- **WHEN** campaign metadata includes `source_public_url` `https://silverman.pro/2026/07/08/my-slug/` and blog image path `/assets/images/my-slug.png`
- **THEN** `preview_image_url` is `https://silverman.pro/assets/images/my-slug.png`

#### Scenario: Missing image path fails planning

- **WHEN** preview is enabled and no canonical image path can be resolved for the campaign
- **THEN** planning fails with `linkedin_preview_image_missing`

### Requirement: Open Graph metadata strategy

When `preview_strategy` is `og_metadata` or selected by `auto`, the worker MUST perform a bounded HTTP fetch of `source_public_url` and evaluate HTML for:

- `og:image` as absolute HTTPS URL
- `og:title` non-empty
- `og:description` non-empty
- page URL consistent with expected blog article URL

When all conditions are met, the worker MUST mark `og_metadata_sufficient: true` and select `og_metadata` strategy.

When `preview_strategy` is `og_metadata` and OG metadata is insufficient, planning MUST fail with `linkedin_preview_og_metadata_insufficient` unless `preview_required` is false and text-only fallback is allowed per `linkedin-publication-integration`.

Fetch failures (timeout, non-2xx) MUST fail with `linkedin_preview_og_fetch_failed`.

#### Scenario: Sufficient OG metadata selects og_metadata strategy

- **WHEN** live blog page includes valid `og:image`, `og:title`, `og:description`, and canonical URL for `source_public_url`
- **THEN** plan selects `og_metadata` with `og_metadata_sufficient: true`

#### Scenario: Insufficient OG blocks og_metadata-only mode

- **WHEN** strategy is `og_metadata` and live page lacks `og:image`
- **THEN** planning fails with `linkedin_preview_og_metadata_insufficient`

#### Scenario: OG fetch timeout fails planning

- **WHEN** OG fetch exceeds configured timeout
- **THEN** planning fails with `linkedin_preview_og_fetch_failed`

### Requirement: LinkedIn explicit image strategy

When `preview_strategy` is `linkedin_explicit` or selected by `auto` fallback, the worker MUST upload image bytes to LinkedIn Images API using an injectable client (initialize upload → transfer bytes → register) and obtain `linkedin_image_urn`.

Image bytes MUST be sourced from resolved `preview_image_url` (preferred) or editorial companion PNG when public fetch is unavailable in test harnesses.

Upload MUST enforce `SILVERMAN_LINKEDIN_PREVIEW_IMAGE_MAX_BYTES`.

Upload failures MUST fail with `linkedin_preview_image_upload_failed`.

The worker MUST NOT persist raw image bytes in campaign metadata or HTTP responses.

#### Scenario: Successful explicit upload returns image URN

- **WHEN** preview is enabled, strategy resolves to `linkedin_explicit`, credentials are valid, and upload succeeds
- **THEN** plan or publish result includes `linkedin_image_urn` and `preview_strategy: linkedin_explicit`

#### Scenario: Upload failure returns stable error

- **WHEN** LinkedIn Images API upload fails during real publish
- **THEN** operation fails with `linkedin_preview_image_upload_failed`

### Requirement: Preview configuration

The worker SHALL support these environment variables:

- `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` — must be `true` to activate preview planning/execution; default `false`
- `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED` — when `true`, publish MUST NOT proceed without successful preview plan/execution; default `false`
- `SILVERMAN_LINKEDIN_PREVIEW_STRATEGY` — `og_metadata`, `linkedin_explicit`, or `auto`; default `auto`
- `SILVERMAN_LINKEDIN_PREVIEW_OG_TIMEOUT_SECONDS` — bounded OG fetch timeout; default `10`
- `SILVERMAN_LINKEDIN_PREVIEW_IMAGE_MAX_BYTES` — maximum image upload size; default `10485760`

When `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` is false, LinkedIn publication MUST behave identically to pre-change text-only publication.

#### Scenario: Preview disabled preserves text-only behavior

- **WHEN** `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` is false
- **THEN** publish-due uses legacy text post path with no preview metadata planning beyond `preview_enabled: false`

#### Scenario: Preview required blocks degraded publish

- **WHEN** `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED` is true and preview planning or execution fails
- **THEN** publish-due MUST NOT call LinkedIn Posts API and MUST return `linkedin_preview_required_blocked_publish` with variant `publish_state` unchanged (`queued`)

### Requirement: Preview publication metadata

For publish-due operations where preview is enabled, campaign metadata and HTTP per-variant results MUST include in `linkedin_publication` (or equivalent):

- `preview_enabled` (boolean)
- `preview_strategy` (`og_metadata`, `linkedin_explicit`, or `text_only_fallback`)
- `preview_image_url` (absolute HTTPS URL when resolved)
- `preview_image_path` (site-root-relative path when resolved)
- `linkedin_image_urn` (when `linkedin_explicit` strategy used)
- `og_metadata_sufficient` (boolean when OG check performed)

Metadata MUST NOT include image bytes, OAuth tokens, or variant body text.

#### Scenario: Publish records preview metadata on success

- **WHEN** real publish succeeds with `og_metadata` strategy
- **THEN** variant `linkedin_publication` records `preview_strategy`, `preview_image_url`, and `preview_image_path` without tokens or body text

#### Scenario: Explicit strategy records image URN

- **WHEN** real publish succeeds with `linkedin_explicit` strategy
- **THEN** variant `linkedin_publication` records `linkedin_image_urn` and `preview_strategy: linkedin_explicit`

### Requirement: Stable error codes

LinkedIn preview support MUST use stable error codes including at minimum:

- `linkedin_preview_image_missing`
- `linkedin_preview_og_metadata_insufficient`
- `linkedin_preview_og_fetch_failed`
- `linkedin_preview_image_upload_failed`
- `linkedin_preview_required_blocked_publish`
- `linkedin_preview_strategy_unresolved`

#### Scenario: Stable preview error codes in response

- **WHEN** a known preview planning or execution failure occurs
- **THEN** `errors[]` contains the documented stable code string

### Requirement: Test coverage

The repository MUST include tests for LinkedIn preview support with fake LinkedIn image/media client and fake OG HTTP client, covering at minimum:

- preview disabled → text-only unchanged
- dry-run reports planned strategy and image URL
- `og_metadata` sufficient path
- `og_metadata` insufficient with `auto` fallback to `linkedin_explicit`
- `preview_required` blocks publish on preview failure without API call
- successful explicit upload records URN in metadata
- no live LinkedIn API in default test runs

#### Scenario: Preview tests pass without live LinkedIn

- **WHEN** `pytest` runs after apply
- **THEN** preview tests pass using injectable fakes without network calls to `api.linkedin.com`

### Requirement: Safety and orchestration boundaries

This change MUST NOT activate n8n workflows, cron jobs, or automatic publication.

This change MUST NOT modify n8n workflow JSON.

This change MUST NOT run `--real-publish` or publish to LinkedIn as part of proposal or default tests.

No LinkedIn Images API or Posts API call MUST occur unless `dry_run` is false, publication is enabled, credentials are valid, and preview is enabled (for image upload path).

#### Scenario: No automatic triggers added

- **WHEN** this change is applied
- **THEN** no background job publishes variants or uploads images without explicit HTTP publish-due invocation
