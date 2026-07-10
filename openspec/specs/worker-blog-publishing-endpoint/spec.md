# worker-blog-publishing-endpoint

## Purpose

Flow A worker blog publishing for the `silverman-blog-linkedin` HTTP worker: validation-first publish orchestration, campaign lifecycle transitions, GitHub Pages bridge integration, idempotent `already_published` handling, and `POST /publish-blog-post`. Implements child slice 4 under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`.
## Requirements
### Requirement: Umbrella and dependency references

This child change SHALL implement Flow A worker blog publishing under active umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 4).

Blog publish behavior MUST align with Flow A policy in canonical spec `editorial-canon` and artifact `content-strategy/silverman-editorial-system.md`.

Ready-post validation MUST use canonical spec `ready-post-editorial-validation` and worker module `ready_post_validation.py` via `validate_ready_post()` before any publish side effect.

Campaign metadata and state transitions MUST use canonical spec `flow-a-lifecycle` and worker module `campaign_lifecycle.py`.

File preparation and public URL derivation MUST use canonical spec `github-pages-blog-publishing` and worker module `github_pages_publish.py` without duplicating publish logic.

Flow B campaigns MUST NOT enter this publish path.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, validation child `ready-post-editorial-validation`, lifecycle child `flow-a-lifecycle-and-duplicate-prevention`, and publishing bridge `github-pages-blog-publishing`

#### Scenario: Flow B blocked

- **WHEN** `publish_blog_post` is invoked for a campaign with `flow` `flow_b`
- **THEN** the operation fails with error code `blog_publish_flow_b_not_allowed` and does not write public repo files

### Requirement: Blog publish service entry point

The worker SHALL expose a publish service entry point (for example `publish_blog_post(base_path, source_relative_path, ...)`) that orchestrates validation, campaign lifecycle transitions, and GitHub Pages bridge application for one ready blog post.

The entry point MUST return a structured `BlogPublishResult` (or equivalent dataclass) serializable to JSON for HTTP and n8n consumers.

The entry point MUST NOT move editorial source files between `ready`, `processed`, or `error` folders.

The entry point MUST NOT run `git commit` or `git push` in the public GitHub Pages repository.

#### Scenario: Publish by relative path

- **WHEN** `publish_blog_post` is called with `source_relative_path` `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` and a valid editorial base path
- **THEN** the function validates the post, may write `_posts/` and `assets/images/` targets in the configured public repo checkout, updates campaign metadata, and returns a structured result without relocating the source Markdown file

#### Scenario: No LinkedIn derivatives

- **WHEN** this child change is applied
- **THEN** no LinkedIn draft files are generated and no `derivatives_*` campaign state transitions occur

### Requirement: Publish flow sequence

The publish flow MUST perform safe preflight path/source inspection sufficient to derive `source_slug`, `public_slug`, `publication_date` (when possible), `source_content_sha256`, `campaign_id`, and the expected blog idempotency key before any publish side effect.

If campaign metadata exists and `state` is `blog_published`, and `flow` is `flow_a`, and stored `source_content_sha256` matches the current source hash, and stored `blog_publish.idempotency_key` matches the expected key, and stored `source_public_url` exists, the publish flow MUST return `status: completed` with `blog_publish.status` `already_published` without calling `validate_ready_post()` and without writing public repo files.

For all other non-published campaigns, before calling `validate_ready_post()`, the publish flow MUST invoke canonical spec `comfyui-blog-image-generation` entry point `ensure_blog_image()` when the ready post lacks canonical image prerequisites per `comfyui-blog-image-generation` missing-image detection (including public asset handoff per `blog-image-public-asset-handoff`) and ComfyUI generation is enabled per worker configuration.

Canonical image prerequisites are satisfied when front matter `image` equals `/assets/images/<public_slug>.png` and public repo `assets/images/<public_slug>.png` exists or is successfully handed off. Companion PNG `blog-posts/ready/<source_slug>.png` is required for validation when downstream validation cannot proceed without it; when a readable public asset exists, optional ready sibling backfill per `blog-image-public-asset-handoff` may satisfy the companion requirement without ComfyUI. When front matter `image` points to a non-canonical path, `ensure_blog_image()` MUST NOT be invoked for remediation; validation or operator remediation MUST handle the mismatch.

If `ensure_blog_image()` is required and returns failure, the publish flow MUST return `status: failed` with the stable error code from the image step (including `blog_image_public_asset_handoff_failed` when applicable), MUST NOT call `validate_ready_post()`, MUST NOT transition to `blog_publish_pending`, and MUST NOT write public repo post files via the bridge.

If `ensure_blog_image()` updates the source Markdown front matter, the publish flow MUST recompute `source_content_sha256` from the updated source file before validation and idempotency checks.

For all other non-published campaigns after the optional image generation and public asset handoff step, the publish flow MUST call `validate_ready_post()` before transitioning to `blog_publish_pending` or writing public repo files.

If validation returns `ok: false`, the publish flow MUST return `status: failed` with error code `blog_publish_validation_failed` and MUST include validation errors in the response.

If validation succeeds and campaign state is `validated` with matching content hash, the publish flow MUST transition `validated` → `blog_publish_pending`, invoke the GitHub Pages bridge apply, then transition `blog_publish_pending` → `blog_published`.

#### Scenario: Idempotent already-published short-circuit before validation

- **WHEN** publish is requested for a campaign already `blog_published` with `flow` `flow_a`, matching idempotency key, matching content hash, and stored `source_public_url`
- **THEN** response `status` is `completed`, `blog_publish.status` is `already_published`, `validate_ready_post()` is not called, `ensure_blog_image()` is not called, and no public repo files are written

#### Scenario: Image generation and handoff before validation when enabled

- **WHEN** publish is requested for a non-published campaign, the ready post lacks canonical image prerequisites (including missing public asset when editorial prerequisites otherwise exist), and ComfyUI generation is enabled
- **THEN** `ensure_blog_image()` runs before `validate_ready_post()`, performs public asset handoff when applicable, and validation runs only after the image step succeeds or is skipped

#### Scenario: Ready sibling adoption before validation

- **WHEN** publish is requested for a non-published campaign, canonical front matter and ready sibling PNG exist, and public `assets/images/<public_slug>.png` is missing
- **THEN** `ensure_blog_image()` adopts the sibling into public assets without ComfyUI before `validate_ready_post()`

#### Scenario: Public asset reuse with failed backfill may still proceed

- **WHEN** publish is requested for a non-published campaign, readable public `assets/images/<public_slug>.png` exists, ready sibling PNG is missing, ready sibling backfill fails, and downstream validation/publish can proceed using the public asset
- **THEN** `ensure_blog_image()` does not call ComfyUI, records a non-blocking backfill warning, does not return `blog_image_public_asset_handoff_failed`, and publish may continue to validation when prerequisites are otherwise satisfied

#### Scenario: Non-canonical image path skips generation before validation

- **WHEN** publish is requested for a non-published campaign and front matter `image` points to a non-canonical path
- **THEN** `ensure_blog_image()` is not invoked for remediation, the post remains unchanged, and validation or operator remediation handles the mismatch

#### Scenario: Public asset handoff failure prevents publish

- **WHEN** publish is requested, image remediation is required, and public asset handoff fails
- **THEN** `publish_blog_post` returns `status: failed` with `blog_image_public_asset_handoff_failed` in `errors[]`, does not call `validate_ready_post()`, does not transition to `blog_publish_pending`, and does not write public repo post files via the bridge

#### Scenario: Image generation failure prevents publish

- **WHEN** publish is requested, ComfyUI generation is enabled, the ready post lacks canonical image prerequisites with no reusable assets, and `ensure_blog_image()` fails at ComfyUI
- **THEN** `publish_blog_post` returns `status: failed` with a blog image generation error code, does not call `validate_ready_post()`, does not transition to `blog_publish_pending`, and does not write public repo post files via the bridge

#### Scenario: Validation failure prevents publish

- **WHEN** `validate_ready_post` returns `ok: false` for a ready post
- **THEN** `publish_blog_post` returns `status: failed`, includes `blog_publish_validation_failed` in `errors[]`, embeds a `validation` summary, does not transition to `blog_publish_pending`, and does not write public repo files via the bridge

#### Scenario: Validation success allows publish attempt

- **WHEN** `validate_ready_post` returns `ok: true` and campaign is in state `validated` with matching content hash
- **THEN** the publish flow transitions to `blog_publish_pending` and attempts GitHub Pages bridge apply

### Requirement: Campaign state transitions for blog publish

For Flow A blog publish, the worker MUST support these transitions:

- `validated` → `blog_publish_pending` → `blog_published` on success

A raw `ready` post MAY be submitted to `POST /publish-blog-post`. The publish flow MUST run `validate_ready_post()` first; if validation succeeds, campaign state becomes `validated` and publish may proceed. Publishing MUST be rejected only if, after validation, the campaign is not eligible for `validated` → `blog_publish_pending`.

The worker MUST reject publish attempts when campaign state is:

- `validation_failed`
- `error`
- a state beyond `blog_published` that would regress lifecycle: `derivatives_pending`, `derivatives_generated`, `distribution_scheduled`, `distribution_complete`, `flow_a_complete`

State `blog_published` is NOT invalid when it satisfies the idempotent `already_published` checks in the publish flow sequence requirement.

State `ready` MUST be handled by validation, not rejected upfront.

Invalid state attempts MUST fail with error code `blog_publish_invalid_campaign_state`.

#### Scenario: Happy-path state progression

- **WHEN** a validated campaign publishes successfully
- **THEN** campaign `state` progresses `validated` → `blog_publish_pending` → `blog_published` with `state_history` entries for each transition

#### Scenario: Ready post validated then published

- **WHEN** campaign `state` is `ready` and `publish_blog_post` is invoked for a valid ready post
- **THEN** `validate_ready_post()` runs first, campaign transitions to `validated` on validation success, and publish proceeds to `blog_publish_pending` without upfront `blog_publish_invalid_campaign_state` rejection

#### Scenario: Validation failed state rejected

- **WHEN** campaign `state` is `validation_failed`
- **THEN** the operation fails with `blog_publish_invalid_campaign_state`

#### Scenario: Error state rejected

- **WHEN** campaign `state` is `error`
- **THEN** the operation fails with `blog_publish_invalid_campaign_state`

#### Scenario: Regressive state rejected

- **WHEN** campaign `state` is `derivatives_pending`, `derivatives_generated`, `distribution_scheduled`, `distribution_complete`, or `flow_a_complete`
- **THEN** the operation fails with `blog_publish_invalid_campaign_state` without regressing `state`

### Requirement: Content hash guard

If stored campaign `source_content_sha256` differs from the current source file digest at publish time, the publish flow MUST fail with error code `blog_publish_content_hash_changed` and MUST NOT overwrite public repo files or campaign publish metadata.

#### Scenario: Changed content after validation

- **WHEN** campaign is `validated` but source file bytes differ from stored `source_content_sha256`
- **THEN** publish fails with `blog_publish_content_hash_changed`

### Requirement: Blog publish idempotency

Blog publish MUST use the idempotency key from `build_blog_publish_idempotency_key()` in `campaign_lifecycle.py`.

If campaign `state` is `blog_published`, `flow` is `flow_a`, stored `blog_publish.idempotency_key` matches the computed key, `source_content_sha256` matches, and stored `source_public_url` exists, the publish flow MUST return `status: completed` with `blog_publish.status` `already_published` without calling `validate_ready_post()` and without overwriting existing public repo files.

If public repo targets already exist but campaign metadata does not prove the same idempotency key, the publish flow MUST fail with `blog_publish_target_exists` and MUST NOT overwrite.

#### Scenario: Idempotent re-run after published

- **WHEN** publish is requested again for a campaign already `blog_published` with `flow` `flow_a`, matching idempotency key, matching content hash, and stored `source_public_url`
- **THEN** response `status` is `completed`, `blog_publish.status` is `already_published`, `validate_ready_post()` is not called, and no duplicate files are written

#### Scenario: Target exists without matching metadata

- **WHEN** `_posts/` or `assets/images/` targets exist but campaign metadata does not prove the same blog idempotency key
- **THEN** publish fails with `blog_publish_target_exists` without overwriting files

#### Scenario: Content change produces different idempotency key

- **WHEN** `source_content_sha256` changes
- **THEN** the computed blog publish idempotency key differs from any prior `blog_publish.idempotency_key` on the campaign

### Requirement: GitHub Pages bridge integration

The publish flow MUST invoke the existing `github_pages_publish.py` bridge (for example `run_publish` with `apply=True`) to write prepared Markdown and PNG into the configured public repo checkout.

During implementation (`/opsx-apply`), the worker MUST inspect `src/silverman_blog_linkedin/github_pages_publish.py` and use the actual existing function signatures (`build_plan`, `apply_plan`, `run_publish`). The worker MUST NOT invent bridge APIs. If the existing bridge surface is CLI-oriented or awkward for service use, the worker MAY add a thin internal wrapper around those functions without duplicating publish logic.

The publish flow MUST pass an injectable `execution_time` (default current UTC) into the bridge so publish date safety resolves Jekyll-safe timestamps for immediate publication.

The publish flow MUST NOT duplicate frontmatter normalization, slug derivation, target path logic, or publish date resolution outside the bridge.

The publish flow MUST NOT invoke git operations.

Public repo path MUST come from configuration (`SILVERMAN_GITHUB_PAGES_REPO_PATH`). When missing or layout-invalid, publish MUST fail with `blog_publish_public_repo_not_configured`.

#### Scenario: Files written via bridge

- **WHEN** publish succeeds for a valid ready post pair
- **THEN** `_posts/YYYY-MM-DD-<public-slug>.md` and `assets/images/<public-slug>.png` exist in the configured public repo checkout with content prepared by the bridge using intended URL date in the filename

#### Scenario: Public repo not configured

- **WHEN** `SILVERMAN_GITHUB_PAGES_REPO_PATH` is unset or the checkout lacks required layout
- **THEN** publish fails with `blog_publish_public_repo_not_configured` before apply

#### Scenario: Future editorial date published safely

- **WHEN** Flow A immediate publish runs with intended URL date `2026-07-10`, execution time before that Jekyll datetime, and public slug `deferring-is-not-avoiding-it-can-be-architecture`
- **THEN** the bridge writes `_posts/2026-07-10-deferring-is-not-avoiding-it-can-be-architecture.md` with safe frontmatter `date`, explicit `permalink`, and publish result `source_public_url` `https://silverman.pro/2026/07/10/deferring-is-not-avoiding-it-can-be-architecture/`

#### Scenario: Bridge apply failure

- **WHEN** the bridge raises an error during apply (for example missing PNG)
- **THEN** publish returns `status: failed` with `blog_publish_failed` and records failure in `blog_publish.error_code` when metadata is written

### Requirement: Campaign metadata blog_publish updates

On publish attempt, the worker MUST update campaign `blog_publish` with:

- `idempotency_key`
- `status`: one of `pending`, `published`, `already_published`, or `failed`
- `source_public_url` when known
- `published_at` when publish completes
- `public_repo_path` or safe relative published paths when available
- `error_code` when failed

Campaign metadata MUST NOT store full Markdown content, generated draft bodies, or secrets.

#### Scenario: Successful publish metadata

- **WHEN** blog publish completes successfully
- **THEN** `blog_publish.status` is `published`, `source_public_url` is set, `published_at` is a UTC ISO8601 timestamp, and `source_public_url` is also set at campaign top level

#### Scenario: Failed publish metadata

- **WHEN** blog publish fails after `blog_publish_pending` transition
- **THEN** `blog_publish.status` is `failed` and `blog_publish.error_code` records the stable failure code

#### Scenario: Metadata excludes body content

- **WHEN** campaign metadata is written after publish
- **THEN** the persisted JSON does not include `markdown_content` or `generated_draft_content`

### Requirement: Blog publish result shape

`BlogPublishResult` (or equivalent) MUST include fields sufficient for n8n branching and operator review, including at minimum:

- `status`: `completed` or `failed`
- `campaign_id`, `state`, `source_slug`, `public_slug`, `publication_date`
- `source_relative_path`, `image_relative_path`
- `source_public_url`
- `errors`, `warnings`
- `validation` (summary object)
- `blog_publish` (object)
- `blog_image_generation` (object summary when generation was evaluated)
- `metadata_written`, `metadata_error_code`

When publish date adjustment occurs, `blog_publish` (or equivalent summary) SHOULD include `date_adjusted` and `publish_timestamp` metadata.

`publication_date` in the result MUST remain the editorial intended `YYYY-MM-DD` from source frontmatter even when the written Jekyll `date` differs.

#### Scenario: Successful publish response

- **WHEN** publish completes successfully
- **THEN** response includes `source_public_url` matching the bridge-computed intended public URL for the post

#### Scenario: Date adjustment metadata in response

- **WHEN** publish adjusts Jekyll `date` for future-post safety
- **THEN** response includes `date_adjusted` true and `source_public_url` using the intended URL date path

#### Scenario: Blog image generation summary in response

- **WHEN** publish evaluates blog image generation for a ready post
- **THEN** response includes `blog_image_generation` with at minimum `status` and, when applicable, `public_image_path` and `error_code`

### Requirement: HTTP endpoint POST /publish-blog-post

The worker SHALL expose `POST /publish-blog-post` protected by the same API-key authentication as other mutating worker endpoints.

Request body MUST accept:

- `source_relative_path` (required)
- `site_url` (optional; default `https://silverman.pro`)
- `public_slug` (optional; only when bridge safely supports override)

Response body MUST include at minimum:

- `status`: `completed` or `failed`
- `campaign_id`, `state`, `source_slug`, `public_slug`, `publication_date`
- `source_relative_path`, `image_relative_path`
- `source_public_url`
- `errors`, `warnings`
- `validation` (summary object)
- `blog_publish` (object)
- `blog_image_generation` (object summary when generation was evaluated)
- `metadata_written`, `metadata_error_code`

#### Scenario: Authenticated publish request

- **WHEN** a client sends `POST /publish-blog-post` with valid API key and `source_relative_path`
- **THEN** the worker returns HTTP 200 with the structured publish result JSON

#### Scenario: Missing API key rejected

- **WHEN** a client sends `POST /publish-blog-post` without valid API key
- **THEN** the worker rejects the request with the same unauthorized behavior as other protected endpoints

#### Scenario: Source public URL in response

- **WHEN** publish completes successfully
- **THEN** response includes `source_public_url` matching the bridge-computed public URL for the post

#### Scenario: Blog image generation summary in response

- **WHEN** publish evaluates blog image generation for a ready post
- **THEN** response includes `blog_image_generation` with at minimum `status` and, when applicable, `public_image_path` and `error_code`

### Requirement: ComfyUI blog image generation integration reference

Blog publish MUST integrate pre-validation blog image generation and public asset handoff per canonical specs `comfyui-blog-image-generation` and `blog-image-public-asset-handoff`, using worker modules `blog_image_generation.py` and `comfyui_client.py`.

`publish_blog_post()` MUST pass the configured public GitHub Pages repository path into `ensure_blog_image()` (or equivalent resolution from `SILVERMAN_GITHUB_PAGES_REPO_PATH`).

When ComfyUI generation is disabled, publish behavior MUST remain backward compatible with posts that already include valid `image` front matter, companion PNG, and public asset (or successful adoption path).

When front matter `image` points to a non-canonical path, publish MUST NOT invoke generation for remediation; validation or operator remediation MUST handle the mismatch.

#### Scenario: Disabled generation with existing public asset

- **WHEN** ComfyUI generation is disabled and the ready post already has valid `image`, companion PNG, and public asset
- **THEN** publish proceeds through validation and bridge apply unchanged from pre-handoff behavior

### Requirement: Extended blog publish error surfacing for image generation

When publish fails due to blog image generation or public asset handoff, `errors[]` MUST include the stable error code from `comfyui-blog-image-generation` or `blog-image-public-asset-handoff` (for example `blog_image_generation_comfyui_failed`, `blog_image_public_asset_handoff_failed`, or `blog_image_generation_failed` only when no specific code applies).

#### Scenario: Handoff failure visible in publish errors

- **WHEN** publish aborts because public asset handoff failed
- **THEN** `errors[]` includes `blog_image_public_asset_handoff_failed` and `blog_image_generation.status` is `failed` in the response

#### Scenario: Generation failure visible in publish errors

- **WHEN** publish aborts because ComfyUI generation failed
- **THEN** `errors[]` includes a `blog_image_generation_*` code and `blog_image_generation.status` is `failed` in the response

### Requirement: Configuration

Editorial base path MUST come from existing worker configuration (`SILVERMAN_BLOG_LINKEDIN_BASE_PATH`).

Public GitHub Pages repository checkout path MUST come from `SILVERMAN_GITHUB_PAGES_REPO_PATH`.

Site URL MUST default to `https://silverman.pro` when not provided in the request.

#### Scenario: Default site URL

- **WHEN** `site_url` is omitted from the HTTP request
- **THEN** public URL calculation uses `https://silverman.pro`

### Requirement: Stable blog publish error codes

The publish flow MUST use stable machine-readable error codes including at minimum:

- `blog_publish_validation_failed`
- `blog_publish_invalid_campaign_state`
- `blog_publish_content_hash_changed`
- `blog_publish_target_exists`
- `blog_publish_failed`
- `blog_publish_metadata_write_failed`
- `blog_publish_public_repo_not_configured`
- `blog_publish_source_not_ready`
- `blog_publish_flow_b_not_allowed`

#### Scenario: Invalid campaign state error code

- **WHEN** publish is attempted from a disallowed campaign state
- **THEN** `errors[]` includes `blog_publish_invalid_campaign_state`

#### Scenario: Metadata write failure

- **WHEN** campaign metadata cannot be written after a publish attempt
- **THEN** response includes `metadata_written: false` and `metadata_error_code` describing the failure

### Requirement: Non-goals enforcement

This child change MUST NOT modify n8n workflow JSON.

This child change MUST NOT generate LinkedIn derivative packages or schedule LinkedIn distribution.

This child change MUST NOT physically move source files between editorial folders.

This child change MUST NOT commit or push the public GitHub Pages repository.

#### Scenario: No n8n workflow changes

- **WHEN** this child change is applied
- **THEN** no files under n8n workflow export paths are modified

#### Scenario: No source file relocation

- **WHEN** publish succeeds
- **THEN** the source Markdown file remains at its original path under `blog-posts/ready/`

### Requirement: Blog image public asset handoff integration reference

Blog publish MUST satisfy canonical spec `blog-image-public-asset-handoff` during the pre-validation image step so Jekyll-canonical `assets/images/<public_slug>.png` exists before validation and bridge apply without manual operator copying.

#### Scenario: Publish passes public repo path to image step

- **WHEN** `publish_blog_post` invokes `ensure_blog_image()`
- **THEN** the configured `SILVERMAN_GITHUB_PAGES_REPO_PATH` is available for public asset evaluation and handoff

