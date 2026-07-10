# linkedin-derivative-package-generation

## MODIFIED Requirements

### Requirement: Variant and package metadata

Campaign metadata MUST be extended with a `linkedin_package` object and updated `variants[]` entries containing references and hashes only.

The `linkedin_package` object MUST include at minimum:

- `package_id` (stable identifier, for example `<campaign_id>-pkg`)
- `idempotency_key` (package-level key; see idempotency requirement)
- `package_status` (for example `generated`)
- `generated_at` (UTC ISO8601)
- `source_public_url` (publish-confirmed URL)
- `source_relative_path`
- `source_content_sha256`
- `variant_ids` (ordered or sorted list of variant IDs in this package)
- `article_preview` (object per canonical spec `linkedin-article-preview-image-support` when package generation runs after that change is applied)

The `linkedin_package.article_preview` object MUST include at minimum:

- `status` (`available`, `missing`, `skipped`, or `invalid`)
- `public_image_url` (when resolved)
- `public_image_path` (when resolved)
- `public_url` (publish-confirmed blog URL)
- `article_title` (when available)
- `article_description` (when available)
- `error_code` (when status is not `available` and a stable code applies)

Each `variants[]` entry for a generated variant MUST include at minimum:

- `variant` (canonical variant ID)
- `audience`
- `tone`
- `source_public_url`
- `source_relative_path`
- `campaign_id`
- `source_content_sha256`
- `derivative_content_sha256`
- `artifact_relative_path`
- `idempotency_key` (per-variant derivative key from `build_derivative_idempotency_key`)
- `generated_at`
- `provider` and `model` when available from generation
- `article_preview_status` (same status values as package `article_preview.status`)
- `public_image_url`, `public_image_path`, `public_url`, `article_title`, and `article_description` when resolved by article preview metadata support

Campaign metadata MUST NOT include `markdown_content`, `generated_draft_content`, or draft body text.

HTTP responses for `POST /generate-linkedin-package` MUST NOT include `generated_draft_content`, `markdown_content`, or variant body text.

Incomplete article preview metadata MUST NOT prevent writing successful package metadata when variant generation otherwise succeeds.

#### Scenario: Metadata stores paths not bodies

- **WHEN** package generation succeeds and campaign metadata is written
- **THEN** the campaign JSON contains `artifact_relative_path` and `derivative_content_sha256` per variant and does not contain generated LinkedIn post body text

#### Scenario: HTTP response excludes generated bodies

- **WHEN** package generation succeeds for an authenticated valid request
- **THEN** the HTTP response includes paths, hashes, variant IDs, provider/model, and status fields only and does not include `generated_draft_content` or variant body text

#### Scenario: Package object recorded

- **WHEN** package generation succeeds
- **THEN** campaign metadata includes `linkedin_package` with `package_id`, `idempotency_key`, `package_status`, `generated_at`, `variant_ids`, and `article_preview`

#### Scenario: Variant preview summary recorded

- **WHEN** package generation succeeds and article preview metadata is resolved
- **THEN** each generated variant entry includes `article_preview_status` and `public_image_url` when available without variant body text

### Requirement: Generate-linkedin-package HTTP response

The worker SHALL expose `POST /generate-linkedin-package` returning structured JSON suitable for n8n branching when the request is authenticated and body validation passes.

The response MUST include at minimum:

- `status` (`completed` or `failed`)
- `campaign_id`
- `state`
- `package_id`
- `source_relative_path`
- `source_public_url`
- `source_content_sha256`
- `variants` (array of per-variant summaries with paths and hashes, not full bodies)
- `package` (package metadata object or null on failure before package creation)
- `article_preview` (object per `linkedin-article-preview-image-support`, or null on failure before preview resolution)
- `errors` (array)
- `warnings` (array)
- `metadata_written` (boolean)
- `metadata_error_code` (string or null)

On `status` `completed`, `package_id`, `variants`, and `article_preview` MUST be populated.

Per-variant entries in `variants` SHOULD include article preview summary fields (`article_preview_status`, `public_image_url`, `public_image_path`, `public_url`, `article_title`, `article_description` as applicable).

On failure after valid body validation, `status` MUST be `failed` and `errors` MUST contain applicable stable error codes.

Incomplete article preview metadata MUST surface in `warnings[]` with stable preview codes but MUST NOT change `status` to `failed` when package generation otherwise succeeds.

The response MUST NOT include `markdown_content`, `generated_draft_content`, variant body text, `DEEPSEEK_API_KEY`, `SILVERMAN_BLOG_LINKEDIN_API_KEY`, prompt text, image bytes, or OAuth tokens.

The endpoint MUST NOT move or modify source blog post files.

The endpoint MUST NOT modify n8n workflow JSON.

The endpoint MUST NOT call LinkedIn API publish or image upload endpoints.

#### Scenario: Completed package response

- **WHEN** package generation succeeds for an authenticated valid request
- **THEN** the response is JSON with `status` `completed`, populated `package_id`, `variants`, `package`, `article_preview`, `metadata_written` true, and HTTP `200`

#### Scenario: Failed eligibility response

- **WHEN** package generation fails because campaign is not `blog_published`
- **THEN** the response is JSON with `status` `failed`, `errors` containing `linkedin_package_invalid_campaign_state`, and HTTP `200`

#### Scenario: Metadata write failure

- **WHEN** variant artifacts are written but campaign metadata persistence fails
- **THEN** the response is JSON with `status` `failed`, `metadata_written` false, `metadata_error_code` `linkedin_package_metadata_write_failed`, and HTTP `200`

#### Scenario: Preview warning does not fail package

- **WHEN** package generation succeeds but article preview status is `missing`
- **THEN** response `status` is `completed`, `article_preview.status` is `missing`, and `warnings[]` includes a stable preview code

### Requirement: Generate-linkedin-package tests

The worker SHALL include automated tests in `tests/test_linkedin_package_generation.py` (and HTTP endpoint tests as applicable) covering:

- campaign not found
- Flow B rejection
- campaign before `blog_published` rejection
- missing `source_public_url` rejection
- source hash changed rejection
- successful package generation from `blog_published`
- campaign transitions to `derivatives_generated`
- all default variants generated
- each variant contains `source_public_url` exactly once
- variant with zero or more than one URL occurrence fails with `linkedin_package_generation_failed`
- campaign metadata and HTTP response store paths/hashes only, not generated bodies
- idempotent rerun after `derivatives_generated` returns completed without regeneration
- target exists without matching metadata fails safely
- invalid requested variant fails
- `linkedin-posts/generated/` exists but is not a directory fails with `linkedin_package_generated_dir_not_ready`
- `linkedin-posts/generated/` not writable fails with `linkedin_package_generated_dir_not_writable`
- HTTP endpoint requires auth consistently with existing worker endpoints
- no n8n workflow JSON changed
- no scheduling metadata created
- no LinkedIn API publication attempted
- article preview metadata `available` when front matter and public repo image exist
- article preview `missing` with warning when public repo configured but image file absent (package still `completed`)
- article preview `skipped` when public repo path not configured
- article preview `invalid` for non-canonical front matter image paths
- absolute `public_image_url` normalization from `/assets/images/<slug>.png`
- no LinkedIn API, OAuth, or OG HTTP fetch in default preview metadata tests

Tests MUST inject or mock the generation function for deterministic behavior. Tests MUST use a mocked generator that returns `source_public_url` exactly once per variant when testing successful generation.

During implementation (`/opsx-apply`), the worker MUST inspect real signatures and existing contracts in `campaign_lifecycle.py`, `linkedin_prompt.py`, `deepseek_client.py`, `draft_writer.py`, `main.py`, and `run_metadata.py`. Use actual signatures — do not invent APIs. Especially verify `CANONICAL_VARIANT_IDS`, `build_derivative_idempotency_key`, `transition_state`, `write_campaign_metadata`, `build_chat_messages`, and `generate_linkedin_draft_content`. If an existing helper is too single-draft-specific, add a thin package-specific wrapper without changing the `POST /generate-linkedin-draft` contract.

#### Scenario: Test module exists

- **WHEN** this child change is applied
- **THEN** `tests/test_linkedin_package_generation.py` exists and covers the scenarios listed in this requirement

#### Scenario: Existing generate-linkedin-draft tests still pass

- **WHEN** the full test suite runs after apply
- **THEN** existing `tests/test_generate_linkedin_draft.py` and related tests pass without contract changes to `POST /generate-linkedin-draft`

#### Scenario: Preview metadata tests pass without LinkedIn

- **WHEN** `pytest` runs after apply
- **THEN** article preview metadata tests pass without calls to LinkedIn APIs
