# comfyui-blog-image-generation

## Purpose

Worker-side ComfyUI blog image generation for Flow A: missing-image detection, editorial visual prompt assembly, configurable ComfyUI-compatible REST API client (local/LAN or Comfy Cloud), asset writes, front matter updates, generation metadata, dry-run mode, and stable error codes. Consumed by `publish_blog_post()` before `validate_ready_post()` when generation is enabled.
## Requirements
### Requirement: Umbrella and dependency references

This change SHALL implement ComfyUI blog image generation as a worker capability consumed by Flow A blog publish.

Image generation behavior MUST align with public blog template constraints at [silverman.pro](https://silverman.pro): single front matter `image` reused for post hero, list cards, tag cards, and sidebar thumbnails at 4:3 aspect ratio with `object-fit: cover`.

Blog publish integration MUST use canonical spec `worker-blog-publishing-endpoint` and worker module `blog_publish_flow.py`.

Ready-post validation rules MUST remain defined by canonical spec `ready-post-editorial-validation`; generation MUST satisfy those rules before validation runs.

Publishing bridge semantics MUST remain defined by canonical spec `github-pages-blog-publishing` and worker module `github_pages_publish.py`.

Flow B campaigns MUST NOT trigger ComfyUI blog image generation.

#### Scenario: Child change cites publish and validation dependencies

- **WHEN** this capability is documented or implemented
- **THEN** it references `worker-blog-publishing-endpoint`, `ready-post-editorial-validation`, and `github-pages-blog-publishing`

#### Scenario: Flow B blocked

- **WHEN** blog image generation runs in the context of a Flow B campaign
- **THEN** generation is skipped or publish fails according to publish-flow policy without writing generated assets

### Requirement: Blog image generation service entry point

The worker SHALL expose a blog image generation entry point (for example `ensure_blog_image(base_path, source_relative_path, *, config=..., client=..., dry_run=..., github_pages_repo_path=...)`) that detects missing canonical blog images, optionally generates them via ComfyUI, performs public blog asset handoff per canonical spec `blog-image-public-asset-handoff`, updates editorial source files, and returns a structured `BlogImageGenerationResult` (or equivalent dataclass) serializable to JSON.

The entry point MUST NOT move source files between `ready`, `processed`, or `error` folders.

The entry point MUST NOT run `git commit` or `git push`.

The entry point MUST hand off or reuse images in the configured public GitHub Pages repository checkout per `blog-image-public-asset-handoff` but MUST NOT overwrite an existing public `assets/images/<public_slug>.png` except by explicit reuse semantics defined in `blog-image-public-asset-handoff`.

#### Scenario: Generate image for post missing front matter image

- **WHEN** `ensure_blog_image` is called for a ready post whose front matter lacks `image`, ComfyUI generation is enabled, dry-run is false, and no reusable public or local PNG exists
- **THEN** the function generates a PNG, writes `blog-posts/ready/<source_slug>.png`, hands off to `assets/images/<public_slug>.png` in the public repo when missing, updates front matter to `image: /assets/images/<public_slug>.png`, and returns `status: generated`

#### Scenario: Skip when image already valid locally and publicly

- **WHEN** front matter `image` equals `/assets/images/<public_slug>.png`, companion PNG `blog-posts/ready/<source_slug>.png` exists, and public `assets/images/<public_slug>.png` exists
- **THEN** the function returns `status: skipped` without calling ComfyUI

#### Scenario: Public asset reuse without ComfyUI

- **WHEN** public `assets/images/<public_slug>.png` exists and is readable
- **THEN** the function returns `status: skipped` with public asset reuse metadata and does not call ComfyUI, even if the editorial ready sibling PNG is missing

#### Scenario: Public asset exists with missing ready sibling does not trigger ComfyUI

- **WHEN** public `assets/images/<public_slug>.png` exists and is readable, front matter `image` is canonical, and `blog-posts/ready/<source_slug>.png` is missing
- **THEN** the function does not call ComfyUI solely because the ready sibling is missing; it may attempt optional ready sibling backfill per `blog-image-public-asset-handoff`

### Requirement: Missing image detection

The worker MUST treat a ready post as eligible for blog image remediation when **either**:

- YAML front matter omits `image` or `image` is empty/whitespace-only, OR
- front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `blog-posts/ready/<source_slug>.png` is missing **and** public repo `assets/images/<public_slug>.png` is missing, OR
- front matter `image` equals `/assets/images/<public_slug>.png`, companion PNG exists, and public repo `assets/images/<public_slug>.png` is missing

When front matter `image` equals `/assets/images/<public_slug>.png`, companion PNG is missing, and a readable public asset exists, the worker MUST NOT invoke ComfyUI; it MUST reuse the public asset and MAY attempt optional ready sibling backfill per `blog-image-public-asset-handoff`.

When front matter `image` is present and points to any non-canonical path (any value other than `/assets/images/<public_slug>.png`), the worker MUST NOT invoke ComfyUI generation, MUST NOT overwrite front matter or companion files, and MUST leave the post unchanged so existing validation or operator remediation handles the mismatch (for example `frontmatter_invalid_image`).

When a valid ready sibling PNG exists and only the public asset is missing, the worker MUST adopt the sibling into the public repo per `blog-image-public-asset-handoff` and MUST NOT call ComfyUI.

When a valid readable public asset exists, the worker MUST reuse it per `blog-image-public-asset-handoff` and MUST NOT call ComfyUI, including when the ready sibling PNG is missing.

When generation is disabled and detection finds missing prerequisites that cannot be satisfied by reuse or adoption, the worker MUST NOT generate and MUST leave remediation to the operator (validation will fail with existing codes).

#### Scenario: Missing image front matter triggers generation when enabled

- **WHEN** a ready post has valid front matter except missing `image`, no reusable public or local PNG exists, and `SILVERMAN_COMFYUI_IMAGE_ENABLED` is true
- **THEN** `ensure_blog_image` attempts ComfyUI generation followed by public asset handoff

#### Scenario: Public asset exists with missing ready sibling triggers reuse not generation

- **WHEN** front matter `image` is `/assets/images/<public_slug>.png`, companion PNG `blog-posts/ready/<source_slug>.png` is missing, public `assets/images/<public_slug>.png` exists and is readable, and `SILVERMAN_COMFYUI_IMAGE_ENABLED` is true
- **THEN** `ensure_blog_image` reuses the public asset without calling ComfyUI and may attempt optional ready sibling backfill

#### Scenario: Canonical image path with missing companion and missing public asset triggers generation when enabled

- **WHEN** front matter `image` is `/assets/images/<public_slug>.png`, companion PNG `blog-posts/ready/<source_slug>.png` is missing, public asset is missing, and `SILVERMAN_COMFYUI_IMAGE_ENABLED` is true
- **THEN** `ensure_blog_image` attempts ComfyUI generation to write the missing companion PNG and hand off to public assets

#### Scenario: Ready sibling exists but public asset missing triggers adoption

- **WHEN** front matter `image` is canonical, `blog-posts/ready/<source_slug>.png` exists, and public `assets/images/<public_slug>.png` is missing
- **THEN** `ensure_blog_image` adopts the sibling into the public repo without calling ComfyUI

#### Scenario: Non-canonical image path does not trigger auto-generation

- **WHEN** front matter `image` is `/assets/images/wrong-slug.png` for derived `public_slug` `why-i-did-not-start-with-the-database`
- **THEN** `ensure_blog_image` returns `status: skipped` or `not_applicable` without overwriting front matter or writing a companion PNG

#### Scenario: Disabled generation leaves post unchanged when adoption impossible

- **WHEN** `image` is missing, no reusable public or local PNG exists, and `SILVERMAN_COMFYUI_IMAGE_ENABLED` is false
- **THEN** `ensure_blog_image` returns `status: skipped` with reason `generation_disabled` and does not call ComfyUI

### Requirement: Visual prompt assembly

The worker SHALL build a deterministic visual generation prompt from available post fields:

- front matter `title`
- front matter `description` (when present)
- front matter `tags` and `categories` (when present)
- a bounded excerpt from the Markdown body after front matter (for example first N characters or first paragraph)

Prompt assembly MUST enforce editorial image rules:

- default output dimensions 1200×900 (4:3)
- professional technical editorial style suitable for software architecture, AI, engineering leadership, and systems design
- no small readable text
- no fake logos or brand marks
- no critical subject detail near edges (safe for `object-fit: cover`)
- main subject centered

The worker MUST also supply a negative prompt (or workflow-equivalent) excluding text, typography, logos, watermarks, and cluttered borders.

#### Scenario: Prompt includes title and description

- **WHEN** a post has `title` and `description` in front matter
- **THEN** the assembled positive prompt incorporates both fields and editorial style constraints

#### Scenario: Prompt uses body excerpt when metadata sparse

- **WHEN** tags and categories are absent but body content exists
- **THEN** the assembled prompt incorporates a bounded body excerpt

### Requirement: ComfyUI client abstraction

The worker SHALL call ComfyUI using a configurable base URL, optional API path prefix, and workflow definition. ComfyUI may be local/LAN or hosted (for example Comfy Cloud at `https://cloud.comfy.org`).

ComfyUI integration MUST be behind an injectable client interface (protocol or abstract base) so tests can substitute fakes without a live ComfyUI server.

The client MUST build endpoint URLs as `{base_url}{api_prefix}/prompt`, `{base_url}{api_prefix}/view`, and poll job completion via either `{base_url}{api_prefix}/jobs/{job_id}` (Comfy Cloud) or `{base_url}{api_prefix}/history/{prompt_id}` (local ComfyUI). When `api_prefix` is empty, behavior MUST match local ComfyUI defaults.

For Comfy Cloud (`https://cloud.comfy.org` with `api_prefix` `/api`), `POST /prompt` returns `prompt_id` which is also the `job_id`. Job status MUST be polled via `GET /jobs/{job_id}` until `status` is `completed` and/or `execution_status.status_str` is `success`, or until timeout/failure. Completed job output images MUST be read from `outputs[<output_node_id>].images[0]` using the workflow binding `bindings.output.node` for `filename`, `subfolder`, and `type`.

For local ComfyUI, job completion MUST continue to be polled via `GET /history/{prompt_id}`.

Image download via `GET /view` MUST follow HTTP redirects (Comfy Cloud returns HTTP 302 to signed storage URLs). The client MUST return final PNG bytes from the redirect target without logging, storing, or exposing signed redirect URLs in results, metadata, or exceptions.

When `SILVERMAN_COMFYUI_API_KEY` is configured, the client MUST send the API key in the configured auth header on ComfyUI requests. When `SILVERMAN_COMFYUI_AUTH_HEADER_NAME` is `Authorization`, the value MUST be `Bearer <api-key>`. When the header name is any other value (Comfy Cloud example `X-API-Key`), the value MUST be the raw API key with no `Bearer` prefix.

When `SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD` is also configured (Comfy Cloud example `api_key_comfy_org`), the client MUST include the API key in the `/prompt` request `extra_data` under that field name (for Comfy Cloud Partner Nodes).

The API key MUST NOT appear in HTTP responses, campaign metadata, run metadata, exceptions exposed by the worker, or test assertion output.

The client MUST load workflow JSON from a configurable path defaulting to a repository workflow template.

The client MUST inject at minimum: positive prompt into the workflow before submission.

Optional workflow bindings (when present in the template): negative prompt, width, height, and seed. When a binding is absent, the client MUST NOT fail injection.

The default Comfy Cloud workflow template (`silverman-blog-openai-gpt-image.json`) uses `OpenAIGPTImage1` with preset size `1536x1024` because `gpt-image-1.5` does not support custom resolution in that template. Local workflows MAY expose width/height bindings (for example `blog-image-workflow.json` targeting 1200×900).

When width/height bindings are absent, metadata MUST record configured `width`/`height` as requested dimensions (not verified output size) and MUST set `workflow_controls_dimensions: false` because the worker does not inject dimensions into the workflow graph.

When both width and height bindings are present, metadata MUST set `workflow_controls_dimensions: true` because the worker injects configured dimensions into the workflow before submission.

The client MUST poll ComfyUI job completion within a configurable timeout and retrieve output PNG bytes.

ComfyUI errors MUST map to stable worker error codes without exposing secrets or full stack traces in HTTP JSON responses.

#### Scenario: Successful ComfyUI generation returns PNG bytes

- **WHEN** ComfyUI completes a job successfully within timeout
- **THEN** the client returns PNG bytes suitable for writing to disk

#### Scenario: ComfyUI timeout fails safely

- **WHEN** ComfyUI does not complete within `SILVERMAN_COMFYUI_TIMEOUT_SECONDS`
- **THEN** the client raises or returns a failure with error code `blog_image_generation_timeout`

#### Scenario: Hosted API prefix applied

- **WHEN** `SILVERMAN_COMFYUI_API_PREFIX` is `/api` and base URL is `https://cloud.comfy.org`
- **THEN** the client calls `https://cloud.comfy.org/api/prompt`, polls `https://cloud.comfy.org/api/jobs/{job_id}`, and downloads via `https://cloud.comfy.org/api/view` with redirect following

#### Scenario: Comfy Cloud job polling and output extraction

- **WHEN** Comfy Cloud returns `prompt_id` from `/prompt` and `/jobs/{job_id}` transitions from in-progress to completed with `outputs[<output_node_id>].images[0]`
- **THEN** the client extracts the output image reference and downloads PNG bytes via `/view`

#### Scenario: Comfy Cloud view redirect followed

- **WHEN** Comfy Cloud `/view` returns HTTP 302 to a signed storage URL
- **THEN** the client follows the redirect, returns PNG bytes, and does not expose the signed URL in worker results or metadata

#### Scenario: Local history polling unchanged

- **WHEN** base URL is local ComfyUI without Comfy Cloud jobs API detection
- **THEN** the client polls `/history/{prompt_id}` as before

#### Scenario: API key sent via auth header and extra_data

- **WHEN** `SILVERMAN_COMFYUI_API_KEY` and `SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD` are configured
- **THEN** the client sends the configured auth header (Bearer only when header name is `Authorization`) and includes the key in `/prompt` `extra_data` without exposing it in worker results or metadata

#### Scenario: Comfy Cloud X-API-Key header

- **WHEN** `SILVERMAN_COMFYUI_AUTH_HEADER_NAME` is `X-API-Key` and an API key is configured
- **THEN** the client sends `X-API-Key: <api-key>` with no `Bearer` prefix

#### Scenario: Tests use fake client

- **WHEN** unit tests run without `SILVERMAN_COMFYUI_IMAGE_ENABLED` against a live server
- **THEN** tests inject a fake client returning deterministic PNG bytes

#### Scenario: Tests do not inherit ambient ComfyUI env

- **WHEN** unit tests run while the operator shell exports Comfy Cloud `SILVERMAN_COMFYUI_*` variables
- **THEN** tests clear or override those variables (shared helper or explicit `environ` / config) so disabled-generation cases remain skipped and enabled cases configure state inside the test

### Requirement: Generated asset paths and front matter update

On successful generation or adoption, the worker MUST:

- ensure PNG exists at `blog-posts/ready/<source_slug>.png`
- ensure PNG exists at public repo `assets/images/<public_slug>.png` when it was missing before handoff
- set front matter `image` to `/assets/images/<public_slug>.png` on the source Markdown file when needed

`public_slug` MUST be derived using the same rules as `github-pages-blog-publishing` (strip leading numeric prefix `^\d+-` when present).

Generated PNG SHOULD default to 1200×900 pixels when the workflow controls dimensions. Non-default sizes (for example 1536×1024 from Comfy Cloud templates) MUST remain valid when handoff succeeds.

#### Scenario: Canonical paths after generation and handoff

- **WHEN** generation succeeds for source slug `02-deferring-is-not-avoiding-it-can-be-architecture`
- **THEN** PNG is at `blog-posts/ready/02-deferring-is-not-avoiding-it-can-be-architecture.png`, public PNG is at `assets/images/deferring-is-not-avoiding-it-can-be-architecture.png`, and front matter `image` is `/assets/images/deferring-is-not-avoiding-it-can-be-architecture.png`

### Requirement: Blog image generation metadata

When blog image generation runs in a publish or standalone context with campaign metadata available, the worker MUST record a `blog_image_generation` object on the campaign including at minimum:

- `status`: one of `generated`, `skipped`, `failed`, `dry_run`
- `image_relative_path` (editorial PNG path when written)
- `public_image_path` (`/assets/images/<public_slug>.png`)
- `public_asset_handoff_status` per `blog-image-public-asset-handoff`
- `public_asset_source` when applicable per `blog-image-public-asset-handoff`
- `public_repo_image_relative_path` when applicable
- `ready_sibling_backfill_status` when applicable per `blog-image-public-asset-handoff`
- `warnings[]` when applicable per `blog-image-public-asset-handoff`
- `width`, `height` (requested dimensions from worker config; actual PNG size may differ when bindings are absent)
- `workflow_controls_dimensions` when true, the workflow template exposes width and height bindings and the worker injected configured dimensions
- `prompt_hash` (SHA-256 of assembled prompt; MUST NOT store full prompt text in campaign metadata)
- `generated_at` when applicable
- `error_code` when failed

The worker SHOULD append a run record under `metadata/runs/` for generation attempts following existing run metadata patterns.

HTTP responses MUST NOT include ComfyUI secrets or full prompt text.

#### Scenario: Successful adoption metadata

- **WHEN** a ready sibling PNG is adopted into public assets during publish
- **THEN** campaign JSON includes `blog_image_generation.status` `generated` or `skipped` as appropriate, `public_asset_handoff_status` `copied`, and `public_asset_source` `ready_sibling_png`

#### Scenario: Failed handoff metadata

- **WHEN** public asset handoff fails
- **THEN** campaign JSON records `blog_image_generation.status` `failed` and `error_code` `blog_image_public_asset_handoff_failed`

### Requirement: Dry-run behavior

The worker MUST support dry-run mode for blog image generation that:

- evaluates missing-image detection including public asset presence
- assembles prompt metadata when ComfyUI would be required
- does NOT call ComfyUI HTTP endpoints
- does NOT write PNG files, modify Markdown front matter, or copy public repo assets
- returns `status: dry_run` with planned paths and dimensions including planned public handoff target

Dry-run MUST be configurable via environment and/or an explicit parameter on the generation entry point for tests.

#### Scenario: Dry-run plans handoff without side effects

- **WHEN** dry-run is true for a post with ready sibling PNG and missing public asset
- **THEN** result includes planned `public_repo_image_relative_path` and source files on disk are unchanged

### Requirement: Configuration

Blog image generation MUST be configurable via environment variables including at minimum:

| Variable | Purpose |
|----------|---------|
| `SILVERMAN_COMFYUI_IMAGE_ENABLED` | Master enable flag |
| `SILVERMAN_COMFYUI_BASE_URL` | ComfyUI server base URL (local/LAN or hosted) |
| `SILVERMAN_COMFYUI_API_PREFIX` | Optional API path prefix (hosted example `/api`) |
| `SILVERMAN_COMFYUI_API_KEY` | ComfyUI/Comfy Cloud API key (never logged or returned) |
| `SILVERMAN_COMFYUI_AUTH_HEADER_NAME` | HTTP header for API key (default `Authorization` → `Bearer <key>`; Comfy Cloud `X-API-Key` → raw key) |
| `SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD` | `extra_data` field for API key on `/prompt` when set (Comfy Cloud example `api_key_comfy_org`) |
| `SILVERMAN_COMFYUI_WORKFLOW_PATH` | Filesystem path to workflow JSON |
| `SILVERMAN_COMFYUI_TIMEOUT_SECONDS` | Generation timeout |
| `SILVERMAN_COMFYUI_IMAGE_WIDTH` | Output width (default 1200) |
| `SILVERMAN_COMFYUI_IMAGE_HEIGHT` | Output height (default 900) |
| `SILVERMAN_COMFYUI_DRY_RUN` | Global dry-run for generation |

`SILVERMAN_COMFYUI_IMAGE_ENABLED` MUST default to false (disabled).

When enabled, missing `SILVERMAN_COMFYUI_BASE_URL` MUST fail with `blog_image_generation_not_configured`.

#### Scenario: Disabled by default

- **WHEN** no ComfyUI env vars are set
- **THEN** generation is disabled and publish behavior matches pre-change validation requirements

#### Scenario: Enabled requires base URL

- **WHEN** `SILVERMAN_COMFYUI_IMAGE_ENABLED` is true and `SILVERMAN_COMFYUI_BASE_URL` is unset
- **THEN** generation fails with `blog_image_generation_not_configured`

### Requirement: Stable blog image generation error codes

The blog image generation flow MUST use stable machine-readable error codes including at minimum:

- `blog_image_generation_disabled`
- `blog_image_generation_not_configured`
- `blog_image_generation_comfyui_failed`
- `blog_image_generation_timeout`
- `blog_image_generation_write_failed`
- `blog_image_generation_frontmatter_update_failed`
- `blog_image_public_asset_handoff_failed`
- `blog_image_generation_failed` (generic wrapper only for unexpected failures not covered by specific codes)

#### Scenario: Handoff failure error code

- **WHEN** public asset copy or adoption fails
- **THEN** errors include `blog_image_public_asset_handoff_failed`

#### Scenario: ComfyUI failure error code

- **WHEN** ComfyUI returns an error or unreachable network
- **THEN** errors include `blog_image_generation_comfyui_failed`

#### Scenario: Front matter update failure

- **WHEN** PNG generation succeeds but Markdown front matter cannot be updated safely
- **THEN** errors include `blog_image_generation_frontmatter_update_failed`

### Requirement: Non-goals enforcement

This change MUST NOT modify n8n workflow JSON.

This change MUST NOT activate n8n schedules or cron triggers.

This change MUST NOT commit or push the public GitHub Pages repository.

This change MUST NOT implement LinkedIn Images API or LinkedIn article preview image behavior.

This change MUST NOT require a live ComfyUI instance during default automated tests.

#### Scenario: No n8n workflow changes

- **WHEN** this change is applied
- **THEN** no files under n8n workflow export paths are modified

#### Scenario: Tests do not require ComfyUI

- **WHEN** `pytest` runs the default test suite
- **THEN** blog image generation tests pass using injected fakes without network access to ComfyUI

### Requirement: Public blog asset handoff integration reference

Blog image generation MUST integrate public asset handoff per canonical spec `blog-image-public-asset-handoff` and MUST accept the configured public GitHub Pages repository path from `SILVERMAN_GITHUB_PAGES_REPO_PATH` (or an explicit parameter for tests).

#### Scenario: Handoff uses configured public repo path

- **WHEN** `ensure_blog_image` runs during publish with `SILVERMAN_GITHUB_PAGES_REPO_PATH` set
- **THEN** public asset evaluation and copy use that checkout root

