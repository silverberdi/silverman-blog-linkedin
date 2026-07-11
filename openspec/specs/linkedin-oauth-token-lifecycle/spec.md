# linkedin-oauth-token-lifecycle

## Purpose

Production-oriented OAuth 2.0 token lifecycle for Silverio Bernal's personal LinkedIn profile on the `silverman-blog-linkedin` HTTP worker: authorization URL generation, callback handling, secure file-based token storage, automatic refresh-before-publish, safe diagnostics, and operator documentation. Depends on `linkedin-publication-integration` for publication flow integration points but does not execute real LinkedIn publication in this change.

## Requirements

### Requirement: Dependency on linkedin-publication-integration

This change SHALL depend on the active `linkedin-publication-integration` change providing queue/publish/cancel endpoints, `linkedin_client.py`, `linkedin_publication_flow.py`, and `linkedin_config.py`.

This change MUST NOT alter n8n workflow JSON, cron triggers, or campaign scheduling semantics.

This change MUST NOT execute real LinkedIn publication or `--real-publish` validation.

#### Scenario: Publication modules exist before apply

- **WHEN** this capability is implemented
- **THEN** token provider integrates with existing publication flow without changing queue/due/cancel scheduling rules

### Requirement: OAuth configuration

The worker SHALL support these environment variables for OAuth:

- `SILVERMAN_LINKEDIN_CLIENT_ID` — LinkedIn Developer App client id
- `SILVERMAN_LINKEDIN_CLIENT_SECRET` — client secret; server-side only; never in HTTP responses or logs
- `SILVERMAN_LINKEDIN_REDIRECT_URI` — registered callback URL (production: `https://api.silverman.pro/linkedin/oauth/callback`)
- `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` — absolute path to file-based token store outside repository/workspace
- `SILVERMAN_LINKEDIN_OAUTH_STATE_TTL_SECONDS` — optional; default `600`
- `SILVERMAN_LINKEDIN_TOKEN_REFRESH_SKEW_SECONDS` — optional; default `300` (refresh before expiry)

The worker MUST NOT expose `client_secret` in any HTTP response, diagnostic output, or smoke script.

#### Scenario: Client secret not in authorize response

- **WHEN** authorization URL is generated
- **THEN** response contains only `authorization_url` (and optional metadata) without `client_secret`

### Requirement: Authorization URL generation

The worker SHALL provide a mechanism to generate the LinkedIn OAuth authorization URL with:

- `response_type=code`
- `client_id` from environment
- `redirect_uri` from environment
- `scope` value `openid profile w_member_social` (space-delimited)
- cryptographically secure random `state`

The worker MUST store `state` server-side with expiration before returning the URL.

The mechanism MUST be available as an API-key-protected HTTP endpoint (for example `GET /linkedin/oauth/authorize`) and MAY be available as a CLI-safe script that prints the URL without exposing secrets.

#### Scenario: Authorization URL includes required parameters

- **WHEN** operator requests authorization URL with valid OAuth configuration
- **THEN** returned URL includes `response_type=code`, `client_id`, `redirect_uri`, `scope=openid%20profile%20w_member_social`, and `state`

#### Scenario: State stored with expiration

- **WHEN** authorization URL is generated
- **THEN** `state` is persisted server-side with TTL and is single-use on successful callback validation

### Requirement: OAuth callback endpoint

The worker SHALL expose public endpoint `GET /linkedin/oauth/callback` receiving query parameters `code`, `state`, and optional `error`, `error_description`.

The callback MUST validate `state` against server-side store and reject unknown or expired state.

On LinkedIn `error` response, the callback MUST return a human-readable failure page without secrets and MUST NOT persist tokens.

On valid `code` and `state`, the worker MUST exchange the authorization code with LinkedIn token endpoint using `client_id`, `client_secret`, `redirect_uri`, and `grant_type=authorization_code`.

On successful exchange, the worker MUST persist token metadata to the token store and return a human-readable success page without token values.

The worker MUST NOT log or print `access_token`, `refresh_token`, `client_secret`, or the full authorization `code`.

#### Scenario: Successful callback persists tokens

- **WHEN** callback receives valid `code` and `state` and LinkedIn token exchange succeeds
- **THEN** token store is updated with access token, refresh token if returned, scope, timestamps, and member URN, and browser receives success message without secrets

#### Scenario: Invalid state rejected

- **WHEN** callback receives `state` not found or expired
- **THEN** callback returns failure message, no token store update, and no secrets in response or logs

#### Scenario: LinkedIn error parameter handled

- **WHEN** callback receives `error` from LinkedIn
- **THEN** callback returns human-readable failure without token exchange and without logging secrets

### Requirement: File-based token store

The worker SHALL persist OAuth token data at `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH`.

The store MUST record at minimum:

- `access_token`
- `refresh_token` when LinkedIn returns it
- `scope`
- `created_at`
- `expires_at`
- `refresh_expires_at` when available
- `member_urn`

Writes MUST be atomic and SHOULD set file permissions to `0600` or equivalent on supported platforms.

Diagnostics and string representations MUST redact `access_token` and `refresh_token` values.

Documentation MUST state chmod `600` expectation for the token store file.

#### Scenario: Token store redaction in diagnostics

- **WHEN** token record is serialized for logs or safe diagnostics
- **THEN** `access_token` and `refresh_token` are not present as cleartext

#### Scenario: Atomic write with restrictive permissions

- **WHEN** token store is updated after successful exchange or refresh
- **THEN** file is written atomically and permissions are set to owner-read/write only where supported

### Requirement: Token provider and refresh

The worker SHALL expose a token provider that resolves a valid access token and member URN before real LinkedIn API publication.

If access token is expired or within refresh skew of expiry, the provider MUST attempt refresh using stored refresh token and LinkedIn refresh grant.

On successful refresh, the provider MUST update the token store.

If refresh token is missing, expired, revoked, or unsupported, the provider MUST return `action_required` with stable error code (for example `linkedin_oauth_reauthorization_required`) and MUST NOT call LinkedIn publication APIs.

Manual environment fallback (`SILVERMAN_LINKEDIN_ACCESS_TOKEN`, `SILVERMAN_LINKEDIN_MEMBER_URN`) MAY be used when documented as fallback only and token store is unavailable.

#### Scenario: Valid token returned without refresh

- **WHEN** access token in store is not expired beyond skew
- **THEN** provider returns `ok` with access token and member URN

#### Scenario: Expired token refreshed

- **WHEN** access token is expired or within skew and valid refresh token exists
- **THEN** provider refreshes, updates store, and returns `ok`

#### Scenario: Missing refresh token fails safe

- **WHEN** access token is expired and no refresh token is stored
- **THEN** provider returns `action_required` without calling LinkedIn publication API

### Requirement: Safe OAuth diagnostics

The worker SHALL expose an API-key-protected diagnostic endpoint or script (for example `GET /linkedin/oauth/status`) reporting at minimum:

- token store configured yes/no
- token present yes/no
- access token `expires_at`
- refresh token present yes/no
- `refresh_expires_at` if known
- scopes
- member URN
- publication enabled yes/no

The diagnostic MUST NOT include `access_token`, `refresh_token`, or `client_secret`.

#### Scenario: Status shows metadata without secrets

- **WHEN** diagnostic endpoint is called with valid API key and tokens are stored
- **THEN** response includes expiry metadata and member URN but no token cleartext values

#### Scenario: Diagnostic without API key rejected

- **WHEN** diagnostic endpoint is called without valid API key
- **THEN** request is rejected unauthorized

### Requirement: Operator documentation

Documentation MUST describe:

- LinkedIn Developer App prerequisites and required products/scopes (`w_member_social`, `openid`, `profile`)
- redirect URL `https://api.silverman.pro/linkedin/oauth/callback`
- Cloudflare Tunnel prerequisite mapping `api.silverman.pro` to worker `localhost:8010`
- initial browser authorization flow
- automatic refresh behavior before publication
- reauthorization when refresh is unavailable
- manual Postman/env token as fallback only, not primary production path
- rotate Cloudflare tunnel connector token if exposed in logs or chat
- avoid exposing unnecessary worker routes publicly
- token store path and chmod `600` expectation

Public site prerequisites (`https://silverman.pro/privacy-policy/`, `https://silverman.pro/terms/`) MUST be referenced where LinkedIn app configuration requires them.

#### Scenario: OAuth flow documented end-to-end

- **WHEN** operator reads deployment documentation
- **THEN** they find steps from authorize URL through callback to status check without instructions to use Postman as primary path

### Requirement: OAuth preflight for US-003 controlled validation

The US-003 controlled validation script (`deploy/server/run-us003-linkedin-publication-validation-smoke.sh`) MUST invoke the safe OAuth diagnostic (`GET /linkedin/oauth/status` or documented equivalent) before any real LinkedIn publication HTTP call.

The preflight step MUST verify token store presence, member URN, expiry/action-required state, and publication enablement flag without printing or persisting token cleartext.

Preflight failure MUST block real queue and publish-due steps.

#### Scenario: US-003 aborts on missing member URN

- **WHEN** diagnostic reports member URN absent before validation window publish
- **THEN** US-003 script exits fail closed and variant `publish_state` remains unchanged

#### Scenario: US-003 records safe preflight summary

- **WHEN** preflight succeeds
- **THEN** script logs member URN, expiry metadata, and publication-enabled state suitable for Phase 3 report without token values

### Requirement: Operator documentation for validation-window OAuth

Operator documentation MUST state that US-003 real publish validation requires a valid OAuth token store (primary path) and that manual env token fallback is acceptable only when documented and operator-approved for the validation window.

Documentation MUST include reauthorization steps when diagnostic reports `action_required` before attempting real publish.

#### Scenario: Reauthorization guidance before US-003

- **WHEN** operator prepares US-003 validation and diagnostic shows expired token without refresh
- **THEN** documentation directs operator through authorize URL → callback → status recheck before enabling real publish

### Requirement: Test coverage for OAuth lifecycle

The repository MUST include tests (for example `tests/test_linkedin_oauth_token_lifecycle.py`) covering at minimum:

- authorization URL generation with required query parameters
- secure state generation, storage, expiration, and single-use validation
- callback error handling for LinkedIn `error` and invalid `state`
- token exchange mocked success and failure
- token store redaction in string/diagnostic output
- refresh decision logic (valid, near expiry, expired with/without refresh token)
- publication flow does not call LinkedIn when provider reports `action_required`
- diagnostic responses contain no token or secret values

Existing test suite MUST continue passing.

#### Scenario: OAuth test module passes

- **WHEN** `pytest` runs after apply
- **THEN** OAuth lifecycle tests pass and existing LinkedIn publication tests pass
