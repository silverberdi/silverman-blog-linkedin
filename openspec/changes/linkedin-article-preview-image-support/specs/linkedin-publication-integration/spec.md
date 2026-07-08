# linkedin-publication-integration

## MODIFIED Requirements

### Requirement: LinkedIn publication configuration

The worker SHALL support these environment variables:

- `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` — must be `true` for real LinkedIn API calls
- `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` — default safety delay; default value `120` for this phase
- `SILVERMAN_LINKEDIN_API_VERSION` — optional LinkedIn API version header override

For LinkedIn article/link preview image support (canonical spec `linkedin-article-preview-image-support`), the worker SHALL also support:

- `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` — must be `true` to activate visual preview planning/execution; default `false`
- `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED` — when `true`, publish MUST NOT proceed without successful preview; default `false`
- `SILVERMAN_LINKEDIN_PREVIEW_STRATEGY` — `og_metadata`, `linkedin_explicit`, or `auto`; default `auto`
- `SILVERMAN_LINKEDIN_PREVIEW_OG_TIMEOUT_SECONDS` — bounded OG metadata fetch timeout; default `10`
- `SILVERMAN_LINKEDIN_PREVIEW_IMAGE_MAX_BYTES` — maximum image upload size; default `10485760`

For OAuth token lifecycle (canonical spec `linkedin-oauth-token-lifecycle`), the worker SHALL resolve access token and member URN through the token provider using `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` and OAuth configuration. Environment variables `SILVERMAN_LINKEDIN_ACCESS_TOKEN` and `SILVERMAN_LINKEDIN_MEMBER_URN` MAY remain as documented manual fallback only when token store is unavailable.

The worker MUST NOT print, log, or return access tokens, refresh tokens, or client secrets in HTTP responses, smoke scripts, diagnostic output, or error messages.

Missing or action-required OAuth credentials, missing member URN after provider resolution, or publication not enabled MUST fail the HTTP response with stable error codes but MUST NOT set variant `publish_state` to `failed`.

Preview planning failures when `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED` is true MUST fail the HTTP response with stable preview error codes but MUST NOT set variant `publish_state` to `failed`.

#### Scenario: OAuth action-required does not mark failed

- **WHEN** a real publish-due request runs with `dry_run` false and token provider returns `action_required` (for example reauthorization needed)
- **THEN** the operation fails with `linkedin_oauth_reauthorization_required` or related stable code, no LinkedIn publication API call occurs, and variant `publish_state` remains `queued`

#### Scenario: Missing member URN on real publish

- **WHEN** a real publish-due request runs with `dry_run` false and neither token store nor fallback env provides member URN
- **THEN** the operation fails with `linkedin_publish_member_urn_missing`, no LinkedIn API call occurs, and variant `publish_state` is unchanged

#### Scenario: Config error does not mark failed

- **WHEN** a real publish-due request fails because `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not `true`
- **THEN** response includes `linkedin_publish_not_enabled` and variant `publish_state` remains `queued` (not `failed`)

#### Scenario: Preview required failure does not mark failed

- **WHEN** a real publish-due request fails because preview is required but planning fails with `linkedin_preview_required_blocked_publish`
- **THEN** variant `publish_state` remains `queued` (not `failed`)

#### Scenario: Token never in response

- **WHEN** any LinkedIn publication operation completes or fails
- **THEN** HTTP response and campaign metadata do not contain token values

### Requirement: Per-variant publication metadata fields

For queued variants, campaign metadata MUST record at minimum:

- `publish_after_utc`
- `publication_queued_at`
- `publication_mode` (for example `safety_delay`)
- `publication_safety_delay_minutes`

For published variants, metadata MUST record at minimum:

- `linkedin_post_urn` or `linkedin_post_id`
- `published_at`
- `linkedin_publication` (safe provider subset; no tokens)

For published variants when preview is enabled, `linkedin_publication` MUST also record at minimum:

- `preview_enabled`
- `preview_strategy`
- `preview_image_url` (when resolved)
- `preview_image_path` (when resolved)
- `linkedin_image_urn` (when `linkedin_explicit` strategy used)
- `og_metadata_sufficient` (when OG check performed)

For failed variants after real API attempt, metadata MUST record failure context in `linkedin_publication`.

Campaign metadata and HTTP responses MUST NOT include variant body text or image bytes.

#### Scenario: Queue writes publication metadata

- **WHEN** real queue succeeds
- **THEN** variant records `publication_queued_at`, `publish_after_utc`, `publication_mode`, and `publication_safety_delay_minutes`

#### Scenario: Publish writes URN without body text

- **WHEN** real publish succeeds
- **THEN** variant records `linkedin_post_urn`, `published_at`, and `linkedin_publication` without artifact body text in metadata or HTTP response

#### Scenario: Publish with preview writes preview metadata

- **WHEN** real publish succeeds with preview enabled
- **THEN** variant `linkedin_publication` includes `preview_strategy` and `preview_image_url` without tokens or body text

### Requirement: Publish due variants service

The worker SHALL expose a publish-due service entry point (for example `publish_linkedin_due_variants(base_path, *, campaign_id=None, variant=None, dry_run=True, publish_now=False, ...)`) that publishes eligible `queued` variants to LinkedIn when due.

Real LinkedIn API calls MUST require `dry_run` false, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`, and a valid access token and member URN resolved through the token provider (or documented env fallback).

The service MUST read variant text from `artifact_relative_path` and include `source_public_url` in post content.

When `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` is false, the service MUST publish personal-profile text posts whose commentary includes variant text and blog URL (legacy behavior).

When `SILVERMAN_LINKEDIN_PREVIEW_ENABLED` is true, the service MUST invoke canonical spec `linkedin-article-preview-image-support` preview planning before post creation and:

- for `og_metadata` strategy: publish article/link-style post referencing `source_public_url` and relying on live OG metadata for visual preview
- for `linkedin_explicit` strategy: upload/register blog image via LinkedIn Images API and attach image URN to supported post payload
- for `auto` strategy: follow preview spec selection order

When `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED` is true and preview planning or execution fails, the service MUST NOT call LinkedIn Posts API and MUST return `linkedin_preview_required_blocked_publish` with variant `publish_state` unchanged.

When preview is enabled but not required and preview fails, the service MAY fall back to legacy text-only post with warning recorded in response/metadata.

The service MUST NOT publish to company pages.

On real API success, variant MUST become `published`. On real API failure or content rejection, variant MUST become `failed`.

Configuration errors, OAuth `action_required` results from the token provider, and preview-required planning failures MUST NOT mark variant `failed`.

Apply phase MUST verify exact current LinkedIn Posts API and Images API payloads and required headers against official documentation.

#### Scenario: Successful text post publish when preview disabled

- **WHEN** publish-due runs in real mode with preview disabled for a due `queued` variant with valid credentials
- **THEN** LinkedIn receives a personal-profile text post whose commentary includes variant text and blog URL, and variant becomes `published`

#### Scenario: Successful preview publish with OG strategy

- **WHEN** publish-due runs in real mode with preview enabled and `og_metadata` strategy for a due `queued` variant with sufficient live OG metadata
- **THEN** LinkedIn receives an article/link-style post referencing `source_public_url`, variant becomes `published`, and `linkedin_publication` records preview metadata

#### Scenario: Preview required blocks publish on failure

- **WHEN** publish-due runs in real mode with `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED` true and preview planning fails
- **THEN** no LinkedIn Posts API call occurs, response includes `linkedin_preview_required_blocked_publish`, and variant `publish_state` remains `queued`

#### Scenario: API failure marks failed

- **WHEN** publish-due runs in real mode, LinkedIn API is called, and API returns a publish failure
- **THEN** variant `publish_state` becomes `failed` with stable error code in `linkedin_publication`

#### Scenario: Action-required skips LinkedIn API

- **WHEN** publish-due runs in real mode and token provider returns `action_required`
- **THEN** no LinkedIn publication API call occurs and variant `publish_state` remains `queued`

#### Scenario: Dry-run publish-due does not call API

- **WHEN** publish-due runs with `dry_run` true for a due `queued` variant
- **THEN** no LinkedIn API call occurs, variant remains `queued`, and response MAY include planned `preview_strategy` and `preview_image_url`

### Requirement: Stable error codes

LinkedIn publication MUST use stable error codes including at minimum:

- `linkedin_publish_campaign_not_found`
- `linkedin_publish_flow_not_allowed`
- `linkedin_publish_invalid_campaign_state`
- `linkedin_publish_variant_not_found`
- `linkedin_publish_variant_not_pending`
- `linkedin_publish_variant_not_queued`
- `linkedin_publish_variant_not_due`
- `linkedin_publish_artifact_missing`
- `linkedin_publish_artifact_hash_changed`
- `linkedin_publish_missing_source_public_url`
- `linkedin_publish_token_missing`
- `linkedin_publish_member_urn_missing`
- `linkedin_publish_token_invalid`
- `linkedin_publish_token_expired`
- `linkedin_publish_insufficient_permission`
- `linkedin_publish_not_enabled`
- `linkedin_publish_api_error`
- `linkedin_publish_content_invalid`
- `linkedin_publish_metadata_write_failed`
- `linkedin_publish_cancel_not_allowed`
- `linkedin_oauth_token_missing`
- `linkedin_oauth_refresh_failed`
- `linkedin_oauth_reauthorization_required`
- `linkedin_preview_image_missing`
- `linkedin_preview_og_metadata_insufficient`
- `linkedin_preview_og_fetch_failed`
- `linkedin_preview_image_upload_failed`
- `linkedin_preview_required_blocked_publish`
- `linkedin_preview_strategy_unresolved`

#### Scenario: Stable error codes in response

- **WHEN** a known eligibility or configuration failure occurs
- **THEN** `errors[]` contains the documented stable code string

### Requirement: Test coverage

The repository MUST include `tests/test_linkedin_publication.py` covering at minimum:

- successful queue `pending` → `queued` with `publish_after_utc`
- successful publish-due with mocked LinkedIn client → `published`
- cancel `queued` → `cancelled`
- missing token / missing member URN / not enabled — response fails, variant NOT `failed`
- OAuth token provider `action_required` — response fails, variant NOT `failed`, no LinkedIn API call
- invalid/expired token / insufficient permission on real API attempt → variant `failed`
- publish-due skips not-yet-due variant unless `publish_now`
- idempotent behavior for already `published`
- dry-run defaults and no mutation on queue/publish/cancel dry-run
- wrong campaign state, missing artifact, hash mismatch
- HTTP auth and 422 validation for all three endpoints
- no n8n workflow JSON changed
- preview disabled → text-only unchanged
- dry-run publish-due reports planned preview strategy when preview enabled
- preview required blocks publish without API call on preview failure
- explicit image upload path with fake image client records URN

OAuth lifecycle tests belong to `linkedin-oauth-token-lifecycle` but publication integration tests MUST cover provider `action_required` behavior.

Preview-focused unit tests MAY live in a dedicated module but MUST run in default `pytest` without live LinkedIn API.

#### Scenario: Test module passes

- **WHEN** `pytest` runs after apply
- **THEN** `tests/test_linkedin_publication.py` and preview tests pass

### Requirement: Operator documentation

Documentation MUST describe:

- LinkedIn Developer App, OAuth authorization flow, and token store (primary production path per `linkedin-oauth-token-lifecycle`)
- Required scopes `openid`, `profile`, `w_member_social` and member URN from OAuth/OIDC
- Manual env/Postman token as fallback only
- Queue → safety delay → publish-due two-step workflow; cancel before publish
- Default safety delay 120 minutes; future immediate mode via config `0` or `publish_now`
- Personal-profile posts with variant text and blog URL; preview image support when `SILVERMAN_LINKEDIN_PREVIEW_ENABLED=true` per `linkedin-article-preview-image-support`
- Preview strategies: `og_metadata` (live blog OG tags), `linkedin_explicit` (Images API upload), `auto` (OG first, explicit fallback)
- Dependency on archived `comfyui-blog-image-generation` for canonical blog images
- `SILVERMAN_LINKEDIN_PREVIEW_REQUIRED` fail-closed semantics
- Separation from Flow A Core; worker-side scheduling only
- Future operator UI need (out of scope v1)

#### Scenario: Two-step workflow documented

- **WHEN** operator reads LinkedIn publication docs
- **THEN** they find queue and publish-due as separate steps with safety delay and cancel guidance, OAuth as primary credential path, and preview configuration when enabled

#### Scenario: Preview dependency documented

- **WHEN** operator reads LinkedIn preview documentation
- **THEN** they find that preview support requires archived `comfyui-blog-image-generation` and canonical public blog images
