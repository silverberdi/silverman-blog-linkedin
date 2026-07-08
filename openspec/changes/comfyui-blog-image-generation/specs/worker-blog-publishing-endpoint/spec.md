## MODIFIED Requirements

### Requirement: Publish flow sequence

The publish flow MUST perform safe preflight path/source inspection sufficient to derive `source_slug`, `public_slug`, `publication_date` (when possible), `source_content_sha256`, `campaign_id`, and the expected blog idempotency key before any publish side effect.

If campaign metadata exists and `state` is `blog_published`, and `flow` is `flow_a`, and stored `source_content_sha256` matches the current source hash, and stored `blog_publish.idempotency_key` matches the expected key, and stored `source_public_url` exists, the publish flow MUST return `status: completed` with `blog_publish.status` `already_published` without calling `validate_ready_post()` and without writing public repo files.

For all other non-published campaigns, before calling `validate_ready_post()`, the publish flow MUST invoke canonical spec `comfyui-blog-image-generation` entry point `ensure_blog_image()` when the ready post lacks canonical image prerequisites per `comfyui-blog-image-generation` missing-image detection and ComfyUI generation is enabled per worker configuration.

Canonical image prerequisites are satisfied when front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `blog-posts/ready/<source_slug>.png` exists. When front matter `image` points to a non-canonical path, `ensure_blog_image()` MUST NOT be invoked for remediation; validation or operator remediation MUST handle the mismatch.

If `ensure_blog_image()` is required and returns failure, the publish flow MUST return `status: failed` with a stable blog image generation error code, MUST NOT call `validate_ready_post()`, MUST NOT transition to `blog_publish_pending`, and MUST NOT write public repo files.

If `ensure_blog_image()` updates the source Markdown front matter, the publish flow MUST recompute `source_content_sha256` from the updated source file before validation and idempotency checks.

For all other non-published campaigns after the optional image generation step, the publish flow MUST call `validate_ready_post()` before transitioning to `blog_publish_pending` or writing public repo files.

If validation returns `ok: false`, the publish flow MUST return `status: failed` with error code `blog_publish_validation_failed` and MUST include validation errors in the response.

If validation succeeds and campaign state is `validated` with matching content hash, the publish flow MUST transition `validated` → `blog_publish_pending`, invoke the GitHub Pages bridge apply, then transition `blog_publish_pending` → `blog_published`.

#### Scenario: Idempotent already-published short-circuit before validation

- **WHEN** publish is requested for a campaign already `blog_published` with `flow` `flow_a`, matching idempotency key, matching content hash, and stored `source_public_url`
- **THEN** response `status` is `completed`, `blog_publish.status` is `already_published`, `validate_ready_post()` is not called, `ensure_blog_image()` is not called, and no public repo files are written

#### Scenario: Image generation before validation when enabled

- **WHEN** publish is requested for a non-published campaign, the ready post lacks canonical image prerequisites (missing or empty `image`, or canonical `image` path with missing companion PNG), and ComfyUI generation is enabled
- **THEN** `ensure_blog_image()` runs before `validate_ready_post()`, and validation runs only after generation succeeds or is skipped

#### Scenario: Non-canonical image path skips generation before validation

- **WHEN** publish is requested for a non-published campaign and front matter `image` points to a non-canonical path
- **THEN** `ensure_blog_image()` is not invoked for remediation, the post remains unchanged, and validation or operator remediation handles the mismatch

#### Scenario: Image generation failure prevents publish

- **WHEN** publish is requested, ComfyUI generation is enabled, the ready post lacks canonical image prerequisites, and `ensure_blog_image()` fails
- **THEN** `publish_blog_post` returns `status: failed` with a blog image generation error code, does not call `validate_ready_post()`, does not transition to `blog_publish_pending`, and does not write public repo files

#### Scenario: Validation failure prevents publish

- **WHEN** `validate_ready_post` returns `ok: false` for a ready post
- **THEN** `publish_blog_post` returns `status: failed`, includes `blog_publish_validation_failed` in `errors[]`, embeds a `validation` summary, does not transition to `blog_publish_pending`, and does not write public repo files

#### Scenario: Validation success allows publish attempt

- **WHEN** `validate_ready_post` returns `ok: true` and campaign is in state `validated` with matching content hash
- **THEN** the publish flow transitions to `blog_publish_pending` and attempts GitHub Pages bridge apply

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

## ADDED Requirements

### Requirement: ComfyUI blog image generation integration reference

Blog publish MUST integrate pre-validation blog image generation per canonical spec `comfyui-blog-image-generation` and worker modules `blog_image_generation.py` and `comfyui_client.py`.

When ComfyUI generation is disabled, publish behavior MUST remain backward compatible with posts that already include valid `image` front matter and companion PNG.

When front matter `image` points to a non-canonical path, publish MUST NOT invoke generation for remediation; validation or operator remediation MUST handle the mismatch.

#### Scenario: Disabled generation preserves existing publish path

- **WHEN** ComfyUI generation is disabled and the ready post already has valid `image` and PNG
- **THEN** publish proceeds through validation and bridge apply unchanged from pre-change behavior

### Requirement: Extended blog publish error surfacing for image generation

When publish fails due to blog image generation, `errors[]` MUST include the stable error code from `comfyui-blog-image-generation` (for example `blog_image_generation_comfyui_failed` or `blog_image_generation_failed`).

#### Scenario: Generation failure visible in publish errors

- **WHEN** publish aborts because ComfyUI generation failed
- **THEN** `errors[]` includes a `blog_image_generation_*` code and `blog_image_generation.status` is `failed` in the response
