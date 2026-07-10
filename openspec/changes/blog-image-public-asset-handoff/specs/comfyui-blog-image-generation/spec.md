## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Public blog asset handoff integration reference

Blog image generation MUST integrate public asset handoff per canonical spec `blog-image-public-asset-handoff` and MUST accept the configured public GitHub Pages repository path from `SILVERMAN_GITHUB_PAGES_REPO_PATH` (or an explicit parameter for tests).

#### Scenario: Handoff uses configured public repo path

- **WHEN** `ensure_blog_image` runs during publish with `SILVERMAN_GITHUB_PAGES_REPO_PATH` set
- **THEN** public asset evaluation and copy use that checkout root
