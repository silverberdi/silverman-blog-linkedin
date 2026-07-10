## ADDED Requirements

### Requirement: Staged editorial image remediation phase

The worker SHALL expose an editorial-only image remediation phase (for example `ensure_editorial_blog_image` or an internal step of `ensure_blog_image` invoked with `handoff=False`) that:

- detects missing, empty, or canonical frontmatter `image` states per missing image detection rules;
- generates via ComfyUI, adopts a local sibling, or backfills the active-folder sibling from a readable public asset when eligible;
- patches canonical frontmatter `image: /assets/images/<public_slug>.png` when authorized;
- writes or updates companion PNG beside the active Markdown folder;
- records editorial provenance metadata;
- MUST NOT write to the configured public GitHub Pages repository checkout.

ComfyUI MUST NOT run when a readable public asset exists and reuse/backfill rules apply.

#### Scenario: Editorial remediation writes queued PNG without public handoff

- **WHEN** `ensure_editorial_blog_image` completes ComfyUI generation for `blog-posts/queued/02-example.md` inside `publish_blog_post` before full validation
- **THEN** `blog-posts/queued/02-example.png` exists, frontmatter is patched if needed, and no file is written to `assets/images/` in the public checkout

#### Scenario: Missing frontmatter image patched during editorial remediation

- **WHEN** `ensure_editorial_blog_image` is called for a ready post whose front matter lacks `image`, ComfyUI generation is enabled, and no reusable public or local PNG exists
- **THEN** the function generates a PNG beside the active Markdown, patches front matter to `image: /assets/images/<public_slug>.png`, and does not write to the public repo

### Requirement: Staged public asset handoff phase

The worker SHALL expose a public handoff phase (for example `handoff_public_blog_image` or an internal step invoked only after full validation) that:

- runs only after `validate_ready_post()` succeeds for the active local Markdown + companion PNG pair;
- copies or reuses the validated active-folder PNG into `assets/images/<public_slug>.png` per `blog-image-public-asset-handoff`;
- MUST NOT run when full validation fails.

`publish_blog_post` orchestration MUST defer public handoff until after full validation even if `ensure_blog_image()` remains a compatibility facade for other callers.

#### Scenario: Full validation failure performs no public asset write

- **WHEN** `publish_blog_post` runs editorial remediation successfully but `validate_ready_post` fails afterward
- **THEN** no file is created or modified at `assets/images/<public_slug>.png` in the public checkout and publish returns failed with the validation error

#### Scenario: Public handoff runs only after full validation success

- **WHEN** editorial remediation and full validation both succeed for `blog-posts/queued/01-example.md`
- **THEN** `handoff_public_blog_image` copies or reuses the validated queued PNG into public assets before GitHub Pages post publish proceeds

## MODIFIED Requirements

### Requirement: Missing image detection

The worker MUST treat a post as eligible for blog image remediation when **either**:

- YAML front matter omits `image` or `image` is empty/whitespace-only, OR
- front matter `image` equals `/assets/images/<public_slug>.png` and companion PNG `<active_source_folder>/<source_slug>.png` is missing **and** public repo `assets/images/<public_slug>.png` is missing, OR
- front matter `image` equals `/assets/images/<public_slug>.png`, companion PNG exists beside the active Markdown, and public repo `assets/images/<public_slug>.png` is missing

`<active_source_folder>` MUST be derived from `source_relative_path` as `blog-posts/ready` or `blog-posts/queued`. Unsupported source folders MUST be rejected.

When front matter `image` equals `/assets/images/<public_slug>.png` (or is absent/empty and will be patched), companion PNG is missing, and a readable public asset exists, the worker MUST NOT invoke ComfyUI; it MUST backfill the active-folder sibling from the public asset during editorial remediation per `blog-image-public-asset-handoff` before full validation.

When front matter `image` is present and non-empty and points to any non-canonical path (any value other than `/assets/images/<public_slug>.png`), the worker MUST NOT invoke ComfyUI generation, MUST NOT overwrite front matter or companion files, and MUST leave the post unchanged so existing validation or operator remediation handles the mismatch (for example `frontmatter_invalid_image`).

When a valid sibling PNG exists beside the active Markdown and only the public asset is missing, the worker MUST adopt the sibling into the public repo during the handoff phase after full validation and MUST NOT call ComfyUI.

When a valid readable public asset exists, the worker MUST reuse it without ComfyUI, including when the active-folder sibling PNG is missing; editorial remediation MUST attempt active-folder backfill so full validation operates on the local pair.

When generation is disabled and detection finds missing prerequisites that cannot be satisfied by reuse, adoption, or backfill, the worker MUST NOT generate and MUST leave remediation to full validation (which will fail with existing codes).

#### Scenario: Missing companion in queued folder triggers generation when enabled

- **WHEN** editorial remediation runs for `blog-posts/queued/01-example.md` with canonical or absent frontmatter `image`, no companion PNG in `blog-posts/queued/`, no public asset, and `SILVERMAN_COMFYUI_IMAGE_ENABLED` is true
- **THEN** ComfyUI generation is attempted and output is written to `blog-posts/queued/01-example.png` without public repo write

#### Scenario: Missing companion in ready folder still triggers generation

- **WHEN** editorial remediation runs for `blog-posts/ready/01-example.md` with absent `image`, no companion PNG, no public asset, and generation is enabled
- **THEN** ComfyUI generation is attempted, frontmatter is patched, and output is written to `blog-posts/ready/01-example.png` without public repo write

#### Scenario: Public asset exists with missing queued sibling does not trigger ComfyUI

- **WHEN** public `assets/images/<public_slug>.png` exists and is readable, front matter `image` is canonical or absent, and `blog-posts/queued/<source_slug>.png` is missing
- **THEN** editorial remediation does not call ComfyUI; it backfills the queued sibling from the public asset when writable

#### Scenario: Non-canonical image path does not trigger auto-generation

- **WHEN** front matter `image` is `/assets/images/wrong-slug.png` for derived `public_slug` `why-i-did-not-start-with-the-database`
- **THEN** editorial remediation returns `status: skipped` or `not_applicable` without overwriting front matter or writing a companion PNG

### Requirement: Blog image generation entry point

The worker SHALL expose a blog image generation entry point (for example `ensure_blog_image(base_path, source_relative_path, *, config=..., client=..., dry_run=..., github_pages_repo_path=..., handoff=...)`) that MAY compose editorial remediation and public handoff for compatibility.

For `publish_blog_post`, the entry point or publish orchestrator MUST enforce staged ordering: editorial remediation and frontmatter patch before full validation; public handoff only after full validation.

Generated companion PNG MUST be written beside the active Markdown source file (`blog-posts/ready/<source_slug>.png` or `blog-posts/queued/<source_slug>.png`).

Detection and output MUST NOT hardcode `blog-posts/ready/` when `source_relative_path` is under `blog-posts/queued/`.

The entry point MUST return a structured `BlogImageGenerationResult` (or equivalent dataclass) serializable to JSON.

#### Scenario: Queued source generation writes beside queued Markdown

- **WHEN** editorial remediation completes ComfyUI generation for `blog-posts/queued/02-example.md`
- **THEN** `blog-posts/queued/02-example.png` exists and `image_relative_path` in the result references the queued path

#### Scenario: Ready source generation unchanged

- **WHEN** editorial remediation completes ComfyUI generation for `blog-posts/ready/02-example.md` with absent `image`
- **THEN** `blog-posts/ready/02-example.png` exists, frontmatter is patched, and existing ready-path behavior is preserved

#### Scenario: Compatibility facade may compose both phases for non-publish callers

- **WHEN** `ensure_blog_image` is called directly outside `publish_blog_post` with default handoff behavior for legacy ready-path callers
- **THEN** it MAY run editorial remediation and public handoff in one call while `publish_blog_post` still uses staged ordering internally
