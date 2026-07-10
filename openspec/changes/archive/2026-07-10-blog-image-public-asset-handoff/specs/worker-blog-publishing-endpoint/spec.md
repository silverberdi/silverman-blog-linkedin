## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Blog image public asset handoff integration reference

Blog publish MUST satisfy canonical spec `blog-image-public-asset-handoff` during the pre-validation image step so Jekyll-canonical `assets/images/<public_slug>.png` exists before validation and bridge apply without manual operator copying.

#### Scenario: Publish passes public repo path to image step

- **WHEN** `publish_blog_post` invokes `ensure_blog_image()`
- **THEN** the configured `SILVERMAN_GITHUB_PAGES_REPO_PATH` is available for public asset evaluation and handoff
