# linkedin-article-preview-verification Delta Specification

Scope: BL-009 / US-023 — verify title, description, and image availability for the article preview inputs of one Flow A campaign. Confirming actual LinkedIn rendering and cache/metadata diagnosis is US-024 and out of scope.

## ADDED Requirements

### Requirement: Verification endpoint and boundaries

The worker SHALL expose an authenticated HTTP endpoint `POST /validate-linkedin-article-preview` that verifies article preview inputs for exactly one campaign identified by `campaign_id`, using the same API-key auth dependency as other LinkedIn endpoints (ADR-0001: worker HTTP only).

The endpoint MUST NOT call LinkedIn API endpoints (`api.linkedin.com`), read LinkedIn OAuth tokens, or make any claim about how LinkedIn renders the preview.

The endpoint MUST NOT mutate variant `publish_state`, scheduling metadata, editorial lifecycle folders, the public blog checkout, or the live public site.

The endpoint MUST NOT include secrets, image bytes, or variant body text in responses or persisted metadata.

Outbound HTTP requests MUST be limited to the campaign's recorded `public_url` and `public_image_url`, MUST use HTTPS, and MUST apply a bounded timeout.

#### Scenario: No LinkedIn API involvement

- **WHEN** `POST /validate-linkedin-article-preview` runs for a campaign
- **THEN** no request is made to `api.linkedin.com` and no LinkedIn access token is read

#### Scenario: Read-only toward lifecycle state

- **WHEN** verification runs for a campaign in any state
- **THEN** variant `publish_state`, scheduling metadata, and editorial source files are unchanged

#### Scenario: Authentication required

- **WHEN** the endpoint is called without a valid API key
- **THEN** the request is rejected by the shared auth dependency without executing any check

### Requirement: Package preview metadata check

The endpoint SHALL execute a `package_metadata` check that verifies the campaign's `linkedin_package.article_preview` block exists and contains non-empty `article_title`, `article_description`, `public_image_url`, and `public_url`.

Missing block or missing `public_url` MUST fail with stable code `linkedin_preview_validation_metadata_missing`. Missing individual fields MUST fail with stable codes `linkedin_preview_validation_title_missing`, `linkedin_preview_validation_description_missing`, or `linkedin_preview_validation_image_url_missing` respectively.

#### Scenario: Complete preview metadata passes

- **WHEN** `linkedin_package.article_preview` contains non-empty title, description, `public_image_url`, and `public_url`
- **THEN** the `package_metadata` check reports `passed` with no codes

#### Scenario: Missing description fails with stable code

- **WHEN** `article_preview` exists but `article_description` is absent or empty
- **THEN** the `package_metadata` check reports `failed` and `codes[]` includes `linkedin_preview_validation_description_missing`

### Requirement: Checkout front matter consistency check

When `SILVERMAN_GITHUB_PAGES_REPO_PATH` is configured, the endpoint SHALL execute a `checkout_consistency` check that compares the recorded `article_title` and `article_description` against the `title` and `description` front matter of the campaign's post file in the public checkout, using exact comparison after whitespace normalization.

Title mismatch MUST fail with stable code `linkedin_preview_validation_title_mismatch`; description mismatch with `linkedin_preview_validation_description_mismatch`; a missing checkout post file with `linkedin_preview_validation_checkout_post_missing`.

When the public repo path is not configured, the check status MUST be `skipped` with informational code `linkedin_preview_validation_checkout_not_configured`, and the overall verdict MUST NOT fail on that account alone.

#### Scenario: Matching checkout front matter passes

- **WHEN** the checkout post front matter `title` and `description` equal the recorded `article_title` and `article_description`
- **THEN** the `checkout_consistency` check reports `passed`

#### Scenario: Mismatched title fails with stable code

- **WHEN** the checkout post front matter `title` differs from the recorded `article_title`
- **THEN** the check reports `failed` and `codes[]` includes `linkedin_preview_validation_title_mismatch`

#### Scenario: Skipped when checkout not configured

- **WHEN** `SILVERMAN_GITHUB_PAGES_REPO_PATH` is not configured
- **THEN** the check reports `skipped` with `linkedin_preview_validation_checkout_not_configured` and does not fail the run

### Requirement: Live Open Graph metadata check

The endpoint SHALL execute a `live_og_metadata` check that performs an HTTP GET of the recorded `public_url` and parses `og:title`, `og:description`, and `og:image` meta tags from the response document.

A non-2xx response, transport error, or timeout MUST fail with stable code `linkedin_preview_validation_public_url_unreachable`, and unreachable MUST be distinguishable from mismatch codes.

When the page is reachable, absent OG tags MUST fail with `linkedin_preview_validation_og_tags_missing`; `og:title` differing from recorded `article_title` MUST fail with `linkedin_preview_validation_og_title_mismatch`; `og:description` differing from recorded `article_description` MUST fail with `linkedin_preview_validation_og_description_mismatch`; `og:image` differing from recorded `public_image_url` MUST fail with `linkedin_preview_validation_og_image_mismatch`. Comparisons MUST use exact matching after whitespace normalization.

#### Scenario: Live OG tags match recorded metadata

- **WHEN** the live page returns 2xx and its `og:title`, `og:description`, and `og:image` equal the recorded metadata
- **THEN** the `live_og_metadata` check reports `passed`

#### Scenario: Unreachable public URL is not reported as mismatch

- **WHEN** the GET of `public_url` times out or returns a non-2xx status
- **THEN** the check reports `failed` with `linkedin_preview_validation_public_url_unreachable` and no mismatch code

#### Scenario: OG description mismatch

- **WHEN** the live page serves an `og:description` different from the recorded `article_description`
- **THEN** the check reports `failed` and `codes[]` includes `linkedin_preview_validation_og_description_mismatch`

### Requirement: Public image availability check

The endpoint SHALL execute a `public_image_availability` check that verifies the recorded `public_image_url` responds over HTTPS with a 2xx status and an `image/*` content type.

A non-2xx response, transport error, or timeout MUST fail with stable code `linkedin_preview_validation_public_image_unreachable`. A 2xx response with a non-image content type MUST fail with `linkedin_preview_validation_public_image_not_image`.

The check MUST NOT download or persist image bytes beyond what is needed to evaluate status and content type.

#### Scenario: Reachable public image passes

- **WHEN** `public_image_url` returns 2xx with `Content-Type: image/png`
- **THEN** the `public_image_availability` check reports `passed`

#### Scenario: Unreachable public image fails with stable code

- **WHEN** `public_image_url` returns 404 or the request times out
- **THEN** the check reports `failed` and `codes[]` includes `linkedin_preview_validation_public_image_unreachable`

### Requirement: Blocked prerequisites and overall verdict

The response SHALL carry an overall `status` of `passed`, `failed`, or `blocked`, plus `campaign_id`, `dry_run`, per-check results under `checks{}`, and a flat `codes[]` list.

When the campaign does not exist, the run MUST be `blocked` with stable code `linkedin_preview_validation_campaign_not_found`. When the campaign has no generated LinkedIn package, the run MUST be `blocked` with `linkedin_preview_validation_package_not_generated`. Blocked runs MUST NOT execute network checks.

The overall verdict MUST be `passed` only when every executed check passes; `skipped` checks MUST NOT cause failure. When any check fails, the verdict MUST be `failed`, and remaining independent checks MUST still execute so a single run reports all detectable problems. A dependent check whose required input is missing from package metadata MUST report `skipped` (the corresponding missing-metadata code is already recorded by `package_metadata`).

Structurally invalid request bodies MUST be rejected with HTTP 422 per existing worker validation conventions.

#### Scenario: Blocked when package not generated

- **WHEN** the campaign exists but has no `linkedin_package`
- **THEN** overall `status` is `blocked` with `linkedin_preview_validation_package_not_generated` and no outbound HTTP request is made

#### Scenario: Failed run reports all detected problems

- **WHEN** the live page serves a mismatched `og:title` and the public image is also unreachable
- **THEN** overall `status` is `failed` and `codes[]` includes both `linkedin_preview_validation_og_title_mismatch` and `linkedin_preview_validation_public_image_unreachable`

#### Scenario: Passed verdict with skipped checkout check

- **WHEN** all executed checks pass and only `checkout_consistency` is `skipped` because the repo path is unset
- **THEN** overall `status` is `passed`

### Requirement: Dry-run safety and evidence persistence

The endpoint SHALL accept a `dry_run` boolean defaulting to `true`. Dry-run executes the same checks and returns the same response shape, and MUST NOT mutate campaign metadata or any other persisted state.

Real runs (`dry_run: false`) MUST persist an additive `linkedin_article_preview_validation` block on the campaign metadata containing at minimum `status`, `checks`, `codes`, `validated_at_utc` (UTC ISO-8601), `public_url`, and `public_image_url`, written atomically. The block is a last-run snapshot; persisting it MUST NOT modify any existing campaign field, including `linkedin_package` and `variants[]`.

Blocked runs MUST NOT persist evidence.

#### Scenario: Dry-run leaves campaign metadata unchanged

- **WHEN** verification runs with `dry_run: true`
- **THEN** the campaign document is byte-identical to its pre-run state and the response reports `dry_run: true`

#### Scenario: Real run persists validation evidence

- **WHEN** verification runs with `dry_run: false` and the campaign has a generated package
- **THEN** campaign metadata contains `linkedin_article_preview_validation` with `status`, `checks`, `codes`, and `validated_at_utc`, and no other field changes

### Requirement: Test coverage without live network

The repository MUST include tests for preview verification with all outbound HTTP mocked and no live network calls in default `pytest` runs, covering at minimum: passing verification, each stable failure code class (missing metadata, checkout mismatch, unreachable public URL, OG tag mismatch, unreachable public image, non-image content type), blocked prerequisites, skipped checkout check, dry-run non-mutation, and real-run evidence persistence.

#### Scenario: Verification tests pass offline

- **WHEN** `pytest` runs after implementation
- **THEN** preview verification tests pass with mocked HTTP and no requests to the live site or `api.linkedin.com`

### Requirement: Existing capabilities unchanged

This capability MUST NOT modify the behavior of `POST /generate-linkedin-package` (canonical spec `linkedin-article-preview-image-support` and `linkedin-derivative-package-generation`), `POST /publish-linkedin-due-variants`, queue/cancel/correct/defer endpoints, retry/recovery evidence semantics (US-022), or the `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` guard.

This capability MUST NOT introduce new environment variables, n8n workflow changes, or deploy script changes.

#### Scenario: Package generation behavior unchanged

- **WHEN** this change is applied
- **THEN** `POST /generate-linkedin-package` responses and package-time preview resolution semantics are unchanged from the pre-change contract

#### Scenario: No new configuration surface

- **WHEN** the worker starts after this change
- **THEN** no new environment variable is required; verification reuses `SILVERMAN_GITHUB_PAGES_REPO_PATH` and existing site URL configuration
