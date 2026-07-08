# linkedin-publication-integration

## MODIFIED Requirements

### Requirement: LinkedIn publication configuration

The worker SHALL support these environment variables:

- `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` — must be `true` for real LinkedIn API calls
- `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` — default safety delay; default value `120` for this phase
- `SILVERMAN_LINKEDIN_API_VERSION` — optional LinkedIn API version header override

For OAuth token lifecycle (canonical spec `linkedin-oauth-token-lifecycle`), the worker SHALL resolve access token and member URN through the token provider using `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` and OAuth configuration. Environment variables `SILVERMAN_LINKEDIN_ACCESS_TOKEN` and `SILVERMAN_LINKEDIN_MEMBER_URN` MAY remain as documented manual fallback only when token store is unavailable.

The worker MUST NOT print, log, or return access tokens, refresh tokens, or client secrets in HTTP responses, smoke scripts, diagnostic output, or error messages.

Missing or action-required OAuth credentials, missing member URN after provider resolution, or publication not enabled MUST fail the HTTP response with stable error codes but MUST NOT set variant `publish_state` to `failed`.

#### Scenario: OAuth action-required does not mark failed

- **WHEN** a real publish-due request runs with `dry_run` false and token provider returns `action_required` (for example reauthorization needed)
- **THEN** the operation fails with `linkedin_oauth_reauthorization_required` or related stable code, no LinkedIn publication API call occurs, and variant `publish_state` remains `queued`

#### Scenario: Missing member URN on real publish

- **WHEN** a real publish-due request runs with `dry_run` false and neither token store nor fallback env provides member URN
- **THEN** the operation fails with `linkedin_publish_member_urn_missing`, no LinkedIn API call occurs, and variant `publish_state` is unchanged

#### Scenario: Config error does not mark failed

- **WHEN** a real publish-due request fails because `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not `true`
- **THEN** response includes `linkedin_publish_not_enabled` and variant `publish_state` remains `queued` (not `failed`)

#### Scenario: Token never in response

- **WHEN** any LinkedIn publication operation completes or fails
- **THEN** HTTP response and campaign metadata do not contain token values

### Requirement: Publish due variants service

The worker SHALL expose a publish-due service entry point (for example `publish_linkedin_due_variants(base_path, *, campaign_id=None, variant=None, dry_run=True, publish_now=False, ...)`) that publishes eligible `queued` variants to LinkedIn when due.

Real LinkedIn API calls MUST require `dry_run` false, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`, and a valid access token and member URN resolved through the token provider (or documented env fallback).

The service MUST read variant text from `artifact_relative_path` and include `source_public_url` in commentary (text post format).

The service MUST NOT upload images or publish to company pages.

On real API success, variant MUST become `published`. On real API failure or content rejection, variant MUST become `failed`.

Configuration errors and OAuth `action_required` results from the token provider MUST NOT mark variant `failed`.

Apply phase MUST verify exact current LinkedIn Posts API payload and required headers against official documentation.

#### Scenario: Successful text post publish

- **WHEN** publish-due runs in real mode for a due `queued` variant with valid credentials from token provider
- **THEN** LinkedIn receives a personal-profile text post whose commentary includes variant text and blog URL, and variant becomes `published`

#### Scenario: API failure marks failed

- **WHEN** publish-due runs in real mode, LinkedIn API is called, and API returns a publish failure
- **THEN** variant `publish_state` becomes `failed` with stable error code in `linkedin_publication`

#### Scenario: Action-required skips LinkedIn API

- **WHEN** publish-due runs in real mode and token provider returns `action_required`
- **THEN** no LinkedIn publication API call occurs and variant `publish_state` remains `queued`

#### Scenario: Dry-run publish-due does not call API

- **WHEN** publish-due runs with `dry_run` true for a due `queued` variant
- **THEN** no LinkedIn API call occurs and variant remains `queued`

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

OAuth lifecycle tests belong to `linkedin-oauth-token-lifecycle` but publication integration tests MUST cover provider `action_required` behavior.

#### Scenario: Test module passes

- **WHEN** `pytest` runs after apply
- **THEN** `tests/test_linkedin_publication.py` passes

### Requirement: Operator documentation

Documentation MUST describe:

- LinkedIn Developer App, OAuth authorization flow, and token store (primary production path per `linkedin-oauth-token-lifecycle`)
- Required scopes `openid`, `profile`, `w_member_social` and member URN from OAuth/OIDC
- Manual env/Postman token as fallback only
- Queue → safety delay → publish-due two-step workflow; cancel before publish
- Default safety delay 120 minutes; future immediate mode via config `0` or `publish_now`
- Personal-profile text post only (commentary with variant text + URL); no image or company page
- Separation from Flow A Core; worker-side scheduling only
- Future operator UI need (out of scope v1)

#### Scenario: Two-step workflow documented

- **WHEN** operator reads LinkedIn publication docs
- **THEN** they find queue and publish-due as separate steps with safety delay and cancel guidance, and OAuth as primary credential path

## ADDED Requirements

### Requirement: Token provider integration for publication

Before any real LinkedIn API publication call, the publish-due service MUST resolve credentials through the token provider defined in `linkedin-oauth-token-lifecycle`.

Dry-run publish-due MUST NOT invoke token refresh or LinkedIn OAuth endpoints.

#### Scenario: Dry-run does not refresh tokens

- **WHEN** publish-due runs with `dry_run` true
- **THEN** token provider refresh and LinkedIn OAuth token endpoint are not called
