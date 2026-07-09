## Why

Flow A blog publishing today requires every ready post to ship with a companion PNG and a canonical `image` front matter path before `validate_ready_post()` can pass. Authors sometimes deliver Markdown without an image, which blocks publish even when the post is otherwise editorially ready. The public blog at [silverman.pro](https://silverman.pro) uses the same `image` value for post hero, home/list cards, tag cards, and sidebar thumbnails at 4:3 (`aspect-ratio: 1.3333333333`, `object-fit: cover`), so missing images degrade the site and stop automation. ComfyUI (local/LAN or Comfy Cloud/hosted) can generate professional 1200×900 editorial images; the worker should orchestrate that step through the configured ComfyUI-compatible REST API (ADR-0001) before validation and publish, with safe defaults (disabled unless explicitly enabled) and dry-run support.

## Goals

- Detect ready blog posts lacking canonical image prerequisites: missing or empty `image` front matter, or canonical `image` path with missing companion PNG.
- MUST NOT auto-generate when `image` points to a non-canonical path; leave the post unchanged for validation or operator remediation.
- Generate a visual prompt from title, description, tags, categories, and post body.
- Call ComfyUI with configurable workflow, timeout, and output dimensions (default 1200×900, 4:3).
- Write generated PNG to editorial assets (`blog-posts/ready/<source_slug>.png` or configured editorial image path) and update front matter to `image: /assets/images/<public_slug>.png`.
- Record image generation metadata in campaign/run metadata without storing secrets or full prompts in HTTP responses.
- Integrate into the existing `publish_blog_post` flow **before** `validate_ready_post()` when generation is needed.
- Fail publish with stable error codes when generation is required but fails; never publish a post that still lacks a valid image after a failed generation attempt.
- Support dry-run behavior (plan prompt, paths, and dimensions without ComfyUI call or file writes).
- Keep ComfyUI image generation **disabled by default** (`SILVERMAN_COMFYUI_IMAGE_ENABLED=false` or equivalent).
- Add tests for missing image, existing image skip, failed generation, metadata recording, and dry-run — using fakes/mocks, not a live ComfyUI instance.

## Non-Goals

- Activating n8n workflows or adding cron/scheduled triggers.
- Real publish runs (`--real-publish`) or modifying the public `silverberdi.github.io` repository directly in this change.
- LinkedIn Images API, LinkedIn article preview images, or any LinkedIn-side image upload.
- Replacing or redesigning the blog theme/CSS or changing aspect-ratio expectations on silverman.pro.
- Requiring a live ComfyUI server during normal unit/integration tests.
- Archiving this change or committing/pushing repository changes.

## What Changes

- Add OpenSpec change `comfyui-blog-image-generation` introducing automatic blog hero/thumbnail image generation via ComfyUI.
- Add capability spec `comfyui-blog-image-generation` covering detection, prompt assembly, ComfyUI client abstraction, asset writes, front matter updates, metadata, configuration, dry-run, and stable error codes.
- Add worker modules (for example `comfyui_client.py`, `blog_image_generation.py`, and prompt helper) with injectable ComfyUI client for tests.
- Extend `publish_blog_post()` in `blog_publish_flow.py` with a pre-validation image generation step when canonical image prerequisites are missing and generation is enabled.
- Add environment variables for ComfyUI base URL, enable flag, workflow path, timeout, width, height, and dry-run/output behavior.
- Extend campaign/run metadata with a `blog_image_generation` (or equivalent) object recording status, paths, dimensions, prompt hash, and error codes.
- Add delta specs for `worker-blog-publishing-endpoint` and `flow-a-automatic-publishing` documenting the new pre-validation image generation gate.
- Add `tests/test_blog_image_generation.py` and extend publish-flow tests for integration points.
- Provide a checked-in ComfyUI workflow JSON template path configurable via env (workflow file lives in this repo; ComfyUI server is external).

No n8n JSON changes, no public repo git operations, no LinkedIn API changes, and no changes to `silverberdi.github.io` unless explicitly requested in a later change.

## Capabilities

### New Capabilities

- `comfyui-blog-image-generation`: Worker-side ComfyUI blog image generation — canonical missing-image detection (missing/empty `image`, or canonical `image` with missing companion PNG; never overwrite non-canonical `image` paths), editorial visual prompt assembly, configurable ComfyUI-compatible REST API client, 1200×900 PNG output suitable for 4:3 `object-fit: cover`, front matter and companion PNG updates under editorial workspace, generation metadata, dry-run mode, disabled-by-default configuration, injectable client for tests, and stable error codes.

### Modified Capabilities

- `worker-blog-publishing-endpoint`: Publish flow sequence gains a pre-validation blog image generation step when canonical image prerequisites are missing and generation is enabled; publish MUST fail when generation is required and fails; publish response MAY include `blog_image_generation` summary fields.
- `flow-a-automatic-publishing`: Flow A umbrella sequence documents ComfyUI blog image generation before editorial validation when canonical image prerequisites are missing and generation is enabled; non-canonical `image` paths MUST NOT trigger auto-generation.

## Impact

- **Blog publish reference**: Canonical spec `openspec/specs/worker-blog-publishing-endpoint/spec.md` and `src/silverman_blog_linkedin/blog_publish_flow.py` — new step before validation.
- **Validation reference**: Canonical spec `openspec/specs/ready-post-editorial-validation/spec.md` and `ready_post_validation.py` — unchanged blocking rules; generation must complete successfully before validation runs.
- **Publishing bridge reference**: Canonical spec `openspec/specs/github-pages-blog-publishing/spec.md` and `github_pages_publish.py` — continues to copy existing PNG; no bridge API invention.
- **Flow A umbrella**: Canonical spec `openspec/specs/flow-a-automatic-publishing/spec.md` — sequence updated to mention pre-validation image generation.
- **Public blog**: [silverman.pro](https://silverman.pro) / `silverberdi.github.io` — **not modified directly**; generated assets land in editorial workspace and flow through existing publish bridge.
- **Configuration**: New env vars under worker settings (ComfyUI URL, enable flag, workflow path, timeout, width/height, dry-run). Defaults safe/disabled.
- **Tests**: New `tests/test_blog_image_generation.py`; extensions to `tests/test_blog_publish_flow.py` with fake ComfyUI client.
- **Operations**: Operator must provide ComfyUI (local/LAN or Comfy Cloud/hosted) when enabling generation in non-test environments; worker calls it through the configured ComfyUI-compatible REST API.
