## ADDED Requirements

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

The worker SHALL expose a blog image generation entry point (for example `ensure_blog_image(base_path, source_relative_path, *, config=..., client=..., dry_run=...)`) that detects missing canonical blog images, optionally generates them via ComfyUI, updates editorial source files, and returns a structured `BlogImageGenerationResult` (or equivalent dataclass) serializable to JSON.

The entry point MUST NOT move source files between `ready`, `processed`, or `error` folders.

The entry point MUST NOT write to the public GitHub Pages repository checkout.

The entry point MUST NOT run `git commit` or `git push`.

#### Scenario: Generate image for post missing front matter image

- **WHEN** `ensure_blog_image` is called for a ready post whose front matter lacks `image`, ComfyUI generation is enabled, and dry-run is false
- **THEN** the function generates a PNG, writes `blog-posts/ready/<source_slug>.png`, updates front matter to `image: /assets/images/<public_slug>.png`, and returns `status: generated`

#### Scenario: Skip when image already valid

- **WHEN** front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `blog-posts/ready/<source_slug>.png` exists
- **THEN** the function returns `status: skipped` without calling ComfyUI

#### Scenario: No public repo side effects

- **WHEN** blog image generation succeeds
- **THEN** no files are written under the configured public GitHub Pages repository checkout

### Requirement: Missing image detection

The worker MUST treat a ready post as eligible for blog image generation when **either**:

- YAML front matter omits `image` or `image` is empty/whitespace-only, OR
- front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `blog-posts/ready/<source_slug>.png` is missing

When front matter `image` is present and points to any non-canonical path (any value other than `/assets/images/<public_slug>.png`), the worker MUST NOT invoke ComfyUI generation, MUST NOT overwrite front matter or companion files, and MUST leave the post unchanged so existing validation or operator remediation handles the mismatch (for example `frontmatter_invalid_image`).

When generation is disabled and detection finds missing canonical image prerequisites, the worker MUST NOT generate and MUST leave remediation to the operator (validation will fail with existing codes).

#### Scenario: Missing image front matter triggers generation when enabled

- **WHEN** a ready post has valid front matter except missing `image` and `SILVERMAN_COMFYUI_IMAGE_ENABLED` is true
- **THEN** `ensure_blog_image` attempts ComfyUI generation

#### Scenario: Canonical image path with missing companion PNG triggers generation when enabled

- **WHEN** front matter `image` is `/assets/images/<public_slug>.png`, companion PNG `blog-posts/ready/<source_slug>.png` is missing, and `SILVERMAN_COMFYUI_IMAGE_ENABLED` is true
- **THEN** `ensure_blog_image` attempts ComfyUI generation to write the missing companion PNG

#### Scenario: Non-canonical image path does not trigger auto-generation

- **WHEN** front matter `image` is `/assets/images/wrong-slug.png` for derived `public_slug` `why-i-did-not-start-with-the-database`
- **THEN** `ensure_blog_image` returns `status: skipped` or `not_applicable` without overwriting front matter or writing a companion PNG

#### Scenario: Disabled generation leaves post unchanged

- **WHEN** `image` is missing and `SILVERMAN_COMFYUI_IMAGE_ENABLED` is false
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

The worker SHALL call ComfyUI over HTTP using a configurable base URL and workflow definition.

ComfyUI integration MUST be behind an injectable client interface (protocol or abstract base) so tests can substitute fakes without a live ComfyUI server.

The client MUST load workflow JSON from a configurable path defaulting to a repository workflow template.

The client MUST inject at minimum: positive prompt, negative prompt, width, height, and a deterministic or configurable seed into the workflow before submission.

The client MUST poll ComfyUI job completion within a configurable timeout and retrieve output PNG bytes.

ComfyUI errors MUST map to stable worker error codes without exposing secrets or full stack traces in HTTP JSON responses.

#### Scenario: Successful ComfyUI generation returns PNG bytes

- **WHEN** ComfyUI completes a job successfully within timeout
- **THEN** the client returns PNG bytes suitable for writing to disk

#### Scenario: ComfyUI timeout fails safely

- **WHEN** ComfyUI does not complete within `SILVERMAN_COMFYUI_TIMEOUT_SECONDS`
- **THEN** the client raises or returns a failure with error code `blog_image_generation_timeout`

#### Scenario: Tests use fake client

- **WHEN** unit tests run without `SILVERMAN_COMFYUI_IMAGE_ENABLED` against a live server
- **THEN** tests inject a fake client returning deterministic PNG bytes

### Requirement: Generated asset paths and front matter update

On successful generation, the worker MUST:

- write PNG to `blog-posts/ready/<source_slug>.png`
- set front matter `image` to `/assets/images/<public_slug>.png` on the source Markdown file

`public_slug` MUST be derived using the same rules as `github-pages-blog-publishing` (strip leading numeric prefix `^\d+-` when present).

Generated PNG SHOULD default to 1200×900 pixels. Legacy 1024×768 manually supplied images MUST remain valid when generation is not used.

#### Scenario: Canonical paths after generation

- **WHEN** generation succeeds for source slug `01-why-i-did-not-start-with-the-database`
- **THEN** PNG is written to `blog-posts/ready/01-why-i-did-not-start-with-the-database.png` and front matter `image` is `/assets/images/why-i-did-not-start-with-the-database.png`

#### Scenario: Default dimensions 1200x900

- **WHEN** width and height env vars are unset
- **THEN** generation requests 1200×900 output

### Requirement: Blog image generation metadata

When blog image generation runs in a publish or standalone context with campaign metadata available, the worker MUST record a `blog_image_generation` object on the campaign including at minimum:

- `status`: one of `generated`, `skipped`, `failed`, `dry_run`
- `image_relative_path` (editorial PNG path when written)
- `public_image_path` (`/assets/images/<public_slug>.png`)
- `width`, `height`
- `prompt_hash` (SHA-256 of assembled prompt; MUST NOT store full prompt text in campaign metadata)
- `generated_at` when applicable
- `error_code` when failed

The worker SHOULD append a run record under `metadata/runs/` for generation attempts following existing run metadata patterns.

HTTP responses MUST NOT include ComfyUI secrets or full prompt text.

#### Scenario: Successful generation metadata

- **WHEN** generation succeeds during publish for a campaign with metadata
- **THEN** campaign JSON includes `blog_image_generation.status` `generated`, paths, dimensions, and `prompt_hash`

#### Scenario: Failed generation metadata

- **WHEN** generation fails during publish
- **THEN** campaign JSON records `blog_image_generation.status` `failed` and a stable `error_code`

### Requirement: Dry-run behavior

The worker MUST support dry-run mode for blog image generation that:

- evaluates missing-image detection and assembles prompt metadata
- does NOT call ComfyUI HTTP endpoints
- does NOT write PNG files or modify Markdown front matter
- returns `status: dry_run` with planned paths and dimensions

Dry-run MUST be configurable via environment and/or an explicit parameter on the generation entry point for tests.

#### Scenario: Dry-run plans without side effects

- **WHEN** dry-run is true for a post missing `image`
- **THEN** result includes planned `image_relative_path`, `public_image_path`, width, height, and `prompt_hash`, and source files on disk are unchanged

### Requirement: Configuration

Blog image generation MUST be configurable via environment variables including at minimum:

| Variable | Purpose |
|----------|---------|
| `SILVERMAN_COMFYUI_IMAGE_ENABLED` | Master enable flag |
| `SILVERMAN_COMFYUI_BASE_URL` | ComfyUI server base URL |
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
- `blog_image_generation_failed` (generic wrapper when publish aborts)

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