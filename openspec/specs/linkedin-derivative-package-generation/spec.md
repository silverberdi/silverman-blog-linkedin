# linkedin-derivative-package-generation

## Purpose

Flow A multi-variant LinkedIn derivative package generation for the `silverman-blog-linkedin` HTTP worker: campaign eligibility, lifecycle transitions (`blog_published` → `derivatives_pending` → `derivatives_generated`), per-variant DeepSeek generation reuse, artifact persistence under `linkedin-posts/generated/`, package idempotency, and `POST /generate-linkedin-package`. Implements child slice 5 under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`.
## Requirements
### Requirement: Umbrella and dependency references

This child change SHALL implement Flow A LinkedIn derivative package generation under active umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 5).

Package generation behavior MUST align with Flow A policy in canonical spec `editorial-canon` and artifact `content-strategy/silverman-editorial-system.md`.

Campaign metadata, state transitions, variant IDs, and idempotency keys MUST use canonical spec `flow-a-lifecycle` and worker module `campaign_lifecycle.py`.

Package generation MUST require a publish-confirmed `source_public_url` recorded by canonical spec `worker-blog-publishing-endpoint` and worker module `blog_publish_flow.py`.

Variant text generation MUST reuse prompt and provider behavior from canonical spec `deepseek-linkedin-draft-generation` and modules `linkedin_prompt.py`, `deepseek_client.py`, and draft-writing utilities without duplicating DeepSeek client logic.

Flow B campaigns MUST NOT enter this package generation path.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, editorial canon child `editorial-canon-and-linkedin-distribution-strategy`, lifecycle child `flow-a-lifecycle-and-duplicate-prevention`, validation child `ready-post-editorial-validation`, blog publish child `worker-blog-publishing-endpoint`, and single-draft generation spec `deepseek-linkedin-draft-generation`

#### Scenario: Flow B blocked

- **WHEN** `generate_linkedin_package` is invoked for a campaign with `flow` `flow_b`
- **THEN** the operation fails with error code `linkedin_package_flow_not_allowed` and does not generate derivative artifacts

### Requirement: LinkedIn package service entry point

The worker SHALL expose a package generation service entry point (for example `generate_linkedin_package(base_path, *, campaign_id=None, source_relative_path=None, variants=None, topic_theme=None, ...)`) that orchestrates campaign eligibility, lifecycle transitions, multi-variant generation, artifact persistence, and campaign metadata updates for one Flow A campaign.

The entry point MUST return a structured `LinkedInPackageResult` (or equivalent dataclass) serializable to JSON for HTTP and n8n consumers.

The entry point MUST NOT move editorial source files between `ready`, `processed`, or `error` folders.

The entry point MUST NOT run `git commit` or `git push`.

The entry point MUST NOT create scheduling metadata (`schedule_at`, `publish_state`, schedule idempotency keys).

The entry point MUST NOT call LinkedIn API publish endpoints.

#### Scenario: Generate package by campaign_id

- **WHEN** `generate_linkedin_package` is called with `campaign_id` for a `flow_a` campaign in state `blog_published` with confirmed `source_public_url` and matching source file hash
- **THEN** the function generates all default canonical variants, writes artifact files, updates campaign metadata, transitions to `derivatives_generated`, and returns a structured result without relocating the source Markdown file

#### Scenario: Generate package by source_relative_path

- **WHEN** `generate_linkedin_package` is called with `source_relative_path` and campaign metadata exists for that path
- **THEN** the function resolves `campaign_id` from campaign metadata and proceeds with package generation

#### Scenario: No scheduling or LinkedIn API side effects

- **WHEN** this child change is applied and package generation succeeds
- **THEN** no `schedule_at` or `publish_state` fields are written and no LinkedIn API publish is attempted

### Requirement: Campaign eligibility for package generation

Package generation MUST require an existing campaign metadata document at `metadata/campaigns/<campaign-id>.json`.

The campaign MUST have `flow` `flow_a`.

The campaign `state` MUST be `blog_published`, `derivatives_pending`, or `derivatives_generated` (idempotent re-run only when idempotency rules below match).

The campaign MUST have a non-null, non-empty `source_public_url` that was publish-confirmed by blog publish flow.

The source Markdown file MUST exist on disk at the campaign's active source path: `processed_source_relative_path` when `source_file_status.location` is `processed`, otherwise `source_relative_path` under `blog-posts/ready/`.

Campaign lookup by `source_relative_path` MUST match `original_source_relative_path`, `processed_source_relative_path`, or active `source_relative_path`.

The current source file SHA-256 MUST match stored `source_content_sha256` in campaign metadata.

Package generation MUST be rejected when:

- campaign metadata does not exist (`linkedin_package_campaign_not_found`)
- `flow` is not `flow_a` (`linkedin_package_flow_not_allowed`)
- `state` is before `blog_published` (`linkedin_package_invalid_campaign_state`)
- `state` is beyond `derivatives_generated` in a way that would regress lifecycle (`distribution_scheduled`, `distribution_complete`, `flow_a_complete`) unless idempotent rules explicitly allow (`linkedin_package_invalid_campaign_state`)
- `source_public_url` is missing (`linkedin_package_missing_source_public_url`)
- source file is missing at resolved active path (`linkedin_package_source_missing`)
- source content hash differs from stored hash (`linkedin_package_source_hash_changed`)
- stored `source_public_url` differs from request-supplied override without metadata proof of same campaign/package (`linkedin_package_public_url_changed`)

#### Scenario: Campaign not found

- **WHEN** package generation is requested for a `campaign_id` with no metadata file
- **THEN** the operation fails with `linkedin_package_campaign_not_found`

#### Scenario: State before blog_published rejected

- **WHEN** package generation is requested for a campaign in state `validated`
- **THEN** the operation fails with `linkedin_package_invalid_campaign_state`

#### Scenario: Missing source_public_url rejected

- **WHEN** package generation is requested for a `blog_published` campaign with `source_public_url` null
- **THEN** the operation fails with `linkedin_package_missing_source_public_url`

#### Scenario: Source hash changed rejected

- **WHEN** the on-disk source Markdown hash differs from campaign `source_content_sha256`
- **THEN** the operation fails with `linkedin_package_source_hash_changed`

#### Scenario: Idempotent package with processed source only

- **WHEN** package generation is requested by `campaign_id` for a campaign in `derivatives_generated` with source Markdown only under `blog-posts/processed/` per metadata
- **THEN** idempotent completion succeeds without `linkedin_package_source_missing` solely due to absent ready copy

### Requirement: Canonical default variants

Unless the request supplies a non-empty `variants` array, package generation MUST generate all canonical variant IDs from editorial canon:

- `executive-recruiter`
- `technical-architect`
- `engineering-leadership`
- `short-provocative`

When `variants` is provided, each entry MUST be a canonical variant ID from `campaign_lifecycle.CANONICAL_VARIANT_IDS`.

An empty `variants` array MUST fail with `linkedin_package_no_variants`.

A non-canonical variant ID MUST fail with `linkedin_package_invalid_variant`.

Each variant MUST be generated as a separate artifact file. The worker MUST NOT concatenate multiple variants into one file.

#### Scenario: All default variants generated

- **WHEN** package generation succeeds without a `variants` request override
- **THEN** exactly four artifact files exist, one per canonical variant ID

#### Scenario: Narrowed variant list

- **WHEN** package generation is requested with `variants` `["executive-recruiter", "short-provocative"]`
- **THEN** only those two variants are generated and recorded in package metadata

#### Scenario: Invalid variant rejected

- **WHEN** package generation is requested with `variants` containing `executive` or `short_provocative`
- **THEN** the operation fails with `linkedin_package_invalid_variant`

### Requirement: Variant artifact layout

Each generated variant artifact MUST be written to a deterministic path relative to the editorial base path:

`linkedin-posts/generated/<campaign_id>/<variant_id>.md`

The worker MAY create `linkedin-posts/generated/` and the per-campaign subfolder when the editorial base path is otherwise valid.

Before calling DeepSeek or writing variant files, the worker MUST verify `linkedin-posts/generated/` readiness:

- if the path exists but is not a directory, fail with `linkedin_package_generated_dir_not_ready`
- if the path is not writable, fail with `linkedin_package_generated_dir_not_writable`

Artifact files MAY contain the full generated LinkedIn post body. Campaign metadata and HTTP responses MUST NOT store the generated body.

Each variant artifact write MUST use exclusive creation. The worker MUST NOT overwrite an existing artifact file unless idempotency rules prove the same package generation intent.

#### Scenario: Generated directory not a directory

- **WHEN** `linkedin-posts/generated/` exists but is not a directory
- **THEN** the operation fails with `linkedin_package_generated_dir_not_ready` before DeepSeek is called

#### Scenario: Generated directory not writable

- **WHEN** `linkedin-posts/generated/` is not writable
- **THEN** the operation fails with `linkedin_package_generated_dir_not_writable` before DeepSeek is called

#### Scenario: Deterministic artifact path

- **WHEN** package generation succeeds for campaign `flow-a-2026-07-06-why-i-did-not-start-with-the-database` and variant `technical-architect`
- **THEN** the artifact path is `linkedin-posts/generated/flow-a-2026-07-06-why-i-did-not-start-with-the-database/technical-architect.md`

#### Scenario: Target exists without metadata proof

- **WHEN** the target artifact file already exists on disk but campaign metadata does not prove a matching package idempotency key and variant hash
- **THEN** the operation fails with `linkedin_package_target_exists` and does not overwrite the file

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

### Requirement: Package idempotency

Package generation MUST define a package-level idempotency key with format:

`package:{campaign_id}:{source_content_sha256}:{variant_list}:{flow}`

Where `{variant_list}` is a comma-separated sorted list of canonical variant IDs included in the package, and `{flow}` is `flow_a`.

Per-variant idempotency MUST continue to use `build_derivative_idempotency_key(campaign_id, source_content_sha256, variant, flow)` from `campaign_lifecycle.py`.

When campaign `state` is `derivatives_generated`, stored `linkedin_package.idempotency_key` matches the expected package key, `source_content_sha256` matches, and all requested variant artifacts exist with matching `derivative_content_sha256` in metadata:

- the operation MUST return `status` `completed`
- the operation MUST return existing package metadata
- the operation MUST NOT regenerate files
- the operation MUST NOT append duplicate `state_history` entries

When target derivative files exist on disk but campaign metadata does not prove matching package idempotency, the operation MUST fail with `linkedin_package_target_exists` and MUST NOT overwrite files.

When `source_content_sha256` changes, the operation MUST fail with `linkedin_package_source_hash_changed`.

When `source_public_url` changes unexpectedly relative to stored campaign metadata without proof of same campaign/package intent, the operation MUST fail with `linkedin_package_public_url_changed`.

#### Scenario: Idempotent rerun after derivatives_generated

- **WHEN** package generation is requested again for a campaign already `derivatives_generated` with matching package idempotency key and variant hashes
- **THEN** response `status` is `completed`, no files are regenerated, and no duplicate state history is appended

#### Scenario: Content hash change blocks idempotent reuse

- **WHEN** source content changes after a prior successful package generation
- **THEN** the operation fails with `linkedin_package_source_hash_changed`

### Requirement: Campaign state transitions for package generation

For Flow A package generation, the worker MUST support these transitions on successful first-time generation:

- `blog_published` → `derivatives_pending` → `derivatives_generated`

All requested variants MUST succeed before transitioning to `derivatives_generated`. If any variant fails, the package operation MUST return `status` `failed` with `linkedin_package_generation_failed`. Partial variant retry is out of scope for this slice.

Idempotent re-runs from `derivatives_generated` with matching package idempotency MUST NOT perform additional state transitions.

Invalid state attempts MUST fail with `linkedin_package_invalid_campaign_state`.

State transitions MUST use `transition_state(..., actor="worker")` and append `state_history` per `flow-a-lifecycle` spec.

#### Scenario: Happy-path state progression

- **WHEN** package generation succeeds from `blog_published`
- **THEN** campaign `state` progresses `blog_published` → `derivatives_pending` → `derivatives_generated` with `state_history` entries

#### Scenario: Idempotent state unchanged

- **WHEN** package generation is requested for an already `derivatives_generated` campaign with matching idempotency
- **THEN** `state` remains `derivatives_generated` and no new `state_history` entry is appended

### Requirement: Variant generation behavior

For each variant in the resolved package list, the worker MUST:

1. Read source Markdown from the campaign `source_relative_path` (not from client-supplied body).
2. Build chat messages via `linkedin_prompt.build_chat_messages()` with campaign `source_public_url`, variant editorial hints, and optional `topic_theme`.
3. Call DeepSeek via `deepseek_client.generate_linkedin_draft_content()` or an injected test double with the same contract.
4. Verify generated content is non-empty.
5. Verify `source_public_url` appears exactly once in generated content. If generated content contains the URL zero times or more than once, treat that variant as generation failure with `linkedin_package_generation_failed` and fail the whole package. Validate URL occurrence before writing the artifact or before finalizing variant metadata.
6. Write the artifact exclusively to the deterministic generated path.
7. Record per-variant metadata with `derivative_content_sha256` computed from written bytes.

The worker MUST NOT duplicate DeepSeek HTTP logic outside `deepseek_client.py`.

The worker MUST NOT store prompt text in campaign metadata or HTTP responses.

If any variant generation, URL validation, or write fails, the package operation MUST return `status` `failed` with `linkedin_package_generation_failed` (and MAY include per-variant error context in `errors`). Partial variant retry is not implemented in this slice.

#### Scenario: source_public_url exactly once per variant

- **WHEN** package generation succeeds for all default variants
- **THEN** each artifact file contains the campaign `source_public_url` exactly once

#### Scenario: URL occurrence mismatch fails variant

- **WHEN** mocked or runtime generation returns content with the campaign `source_public_url` zero times or more than once
- **THEN** the package operation returns `status` `failed` with `linkedin_package_generation_failed`

#### Scenario: Reuses linkedin_prompt

- **WHEN** package generation builds prompts for a variant with confirmed `source_public_url`
- **THEN** `linkedin_prompt.build_chat_messages()` is used and includes URL CTA instructions

#### Scenario: Generation failure

- **WHEN** DeepSeek returns an error or empty content for any requested variant
- **THEN** the package operation returns `status` `failed` with `linkedin_package_generation_failed` in `errors`

### Requirement: API key authentication for generate-linkedin-package

The worker SHALL require valid API key authentication for `POST /generate-linkedin-package` using the configured `SILVERMAN_BLOG_LINKEDIN_API_KEY`.

The client MUST send the key in the `Authorization` header as a Bearer token: `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`.

#### Scenario: Valid API key

- **WHEN** a client sends `POST /generate-linkedin-package` with a correct Bearer token
- **THEN** the worker proceeds with request body validation and package generation checks

#### Scenario: Missing Authorization header

- **WHEN** a client sends `POST /generate-linkedin-package` without an `Authorization` header
- **THEN** the worker responds with HTTP `401`

#### Scenario: Invalid API key

- **WHEN** a client sends `POST /generate-linkedin-package` with an incorrect Bearer token
- **THEN** the worker responds with HTTP `401` and does not expose secret values

### Requirement: Generate-linkedin-package request body

The worker SHALL accept a JSON request body on `POST /generate-linkedin-package` with:

- exactly one of `campaign_id` or `source_relative_path` (both MUST NOT be omitted; both MUST NOT be sent as empty strings)
- optional `variants` array of canonical variant ID strings
- optional `topic_theme` string
- optional `site_url` string (discouraged when campaign metadata already has `source_public_url`)

The worker MUST reject requests with missing both identifiers, empty identifiers, invalid types, invalid `variants` entries, whitespace-only `topic_theme`, invalid `site_url` when provided, or any unexpected extra field with HTTP `422`.

The request body MUST use Pydantic `extra="forbid"` or equivalent.

Before validation, the worker SHALL normalize `source_relative_path` by stripping leading `./` and trailing slashes when provided.

#### Scenario: Valid request with campaign_id

- **WHEN** a client sends an authenticated request with `campaign_id` `flow-a-2026-07-06-why-i-did-not-start-with-the-database`
- **THEN** the worker accepts the body and proceeds with eligibility checks

#### Scenario: Valid request with source_relative_path

- **WHEN** a client sends an authenticated request with `source_relative_path` `blog-posts/ready/01-why-i-did-not-start-with-the-database.md`
- **THEN** the worker accepts the body and resolves campaign metadata

#### Scenario: Both identifiers missing

- **WHEN** a client sends a body omitting both `campaign_id` and `source_relative_path`
- **THEN** the worker responds with HTTP `422`

#### Scenario: Extra fields rejected

- **WHEN** a client sends unexpected fields such as `markdown_content` or `output_path`
- **THEN** the worker responds with HTTP `422`

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

### Requirement: Stable error codes

Package generation MUST use these stable machine-readable error codes:

| Code | Meaning |
|------|---------|
| `linkedin_package_campaign_not_found` | No campaign metadata for resolved identifier |
| `linkedin_package_flow_not_allowed` | Campaign `flow` is not `flow_a` |
| `linkedin_package_invalid_campaign_state` | Campaign state not eligible for package generation |
| `linkedin_package_missing_source_public_url` | Publish-confirmed URL missing |
| `linkedin_package_source_missing` | Source Markdown file not found |
| `linkedin_package_source_hash_changed` | On-disk source hash differs from metadata |
| `linkedin_package_public_url_changed` | Unexpected `source_public_url` change |
| `linkedin_package_target_exists` | Artifact exists without matching idempotency proof |
| `linkedin_package_generation_failed` | Variant generation or write failed |
| `linkedin_package_metadata_write_failed` | Campaign metadata write failed |
| `linkedin_package_invalid_variant` | Non-canonical variant ID requested |
| `linkedin_package_no_variants` | Empty `variants` array requested |
| `linkedin_package_generated_dir_not_ready` | `linkedin-posts/generated/` missing or not a directory |
| `linkedin_package_generated_dir_not_writable` | `linkedin-posts/generated/` not writable |
| `deepseek_api_key_missing` | DeepSeek not configured (reused from draft generation) |
| `deepseek_config_invalid` | Invalid DeepSeek optional settings |

#### Scenario: Error codes are stable strings

- **WHEN** package generation fails for a known eligibility violation
- **THEN** `errors[]` contains the documented stable code string exactly

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

