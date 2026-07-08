## Why

Flow A LinkedIn publication currently sends personal-profile text posts whose commentary includes variant text and the blog URL. A real publication validated successfully, but the live post appeared as plain text plus URL without a visual link preview card—even though the blog post has a canonical hero image (1200×900, 4:3) suitable for social sharing. Future automated publications should preserve visual presence when a public blog image is available. This change depends on `comfyui-blog-image-generation` so every Flow A post can rely on a canonical blog image before LinkedIn preview support is implemented.

## Goals

- Define how LinkedIn publication uses the blog image for article/link preview support when a public image is available.
- Support two controlled strategies: (1) Open Graph/social metadata via public blog URL, and (2) LinkedIn explicit image upload/register via Images API.
- Add configuration flags so visual preview behavior is disabled/safe by default until explicitly enabled.
- Add validation/dry-run behavior that reports which preview strategy would be used without calling LinkedIn API.
- Add publication result metadata: preview strategy, image path/URL, and LinkedIn image URN when applicable.
- When preview is required, fail closed—do not publish a degraded plain URL-only post if visual preview cannot be created.
- Add tests with a fake LinkedIn image/media client; no live LinkedIn API in default tests.
- **MUST NOT** implement until `comfyui-blog-image-generation` is implemented, validated, and archived.

## Non-Goals

- Implementing this change or modifying runtime code as part of this proposal.
- Activating n8n, cron/scheduled triggers, or `--real-publish`.
- Modifying the public blog repository directly or changing ComfyUI image generation behavior.
- Company page publishing, native LinkedIn scheduling, analytics, or comment automation.
- Archiving this change or committing/pushing as part of this proposal.

## What Changes

- Add OpenSpec change `linkedin-article-preview-image-support` as a **proposed-only** follow-up to `comfyui-blog-image-generation` and `linkedin-publication-integration`.
- Add capability spec `linkedin-article-preview-image-support` covering preview strategy selection, OG metadata validation, LinkedIn Images API upload path, configuration, dry-run planning, publication metadata, fail-closed semantics, and stable error codes.
- Extend `publish_linkedin_due_variants()` (and related client modules) to plan and optionally execute visual preview when enabled—without changing queue/cancel semantics.
- Add environment variables for preview enablement, strategy mode, required-vs-optional preview, and OG validation timeout.
- Extend per-variant `linkedin_publication` metadata and publish-due HTTP responses with `preview_strategy`, `preview_image_url`, `preview_image_path`, and `linkedin_image_urn` when applicable.
- Add delta specs for `linkedin-publication-integration` (publish-due behavior, configuration, metadata, tests, operator docs) and `flow-a-automatic-publishing` (umbrella sequence note).
- Add `linkedin_image_client.py` (or equivalent) with injectable protocol for Images API fakes; extend `tests/test_linkedin_publication.py` and add focused preview tests.
- Document operator prerequisites for preview (public `og:image` on live blog, optional Images API product/scopes) and dependency gate on archived `comfyui-blog-image-generation`.

No n8n workflow JSON changes. No automatic triggers. No live LinkedIn API calls in default test runs.

## Capabilities

### New Capabilities

- `linkedin-article-preview-image-support`: Worker-side LinkedIn article/link preview image support — strategy selection (`og_metadata`, `linkedin_explicit`, `auto`), public image URL resolution from campaign/blog metadata, OG metadata sufficiency checks, LinkedIn Images API upload/register path, dry-run planning, preview metadata on publication results, fail-closed when preview is required, disabled-by-default configuration, injectable image client for tests, and stable error codes.

### Modified Capabilities

- `linkedin-publication-integration`: Publish-due service gains optional visual preview path when enabled; configuration, per-variant metadata, stable error codes, test coverage, smoke script dry-run reporting, and operator documentation updated from text-only-only to include controlled preview strategies.
- `flow-a-automatic-publishing`: Umbrella Flow A sequence documents LinkedIn preview image support as a deferred slice after canonical blog images exist (`comfyui-blog-image-generation` archived).

## Impact

- **Dependency gate**: Implementation blocked until `comfyui-blog-image-generation` is archived; assumes canonical `image` front matter and public asset at `/assets/images/<public_slug>.png` (1200×900).
- **LinkedIn publication reference**: Canonical spec `openspec/specs/linkedin-publication-integration/spec.md`, `linkedin_publication_flow.py`, `linkedin_client.py`.
- **Blog metadata reference**: Campaign `source_public_url` (publish-confirmed), front matter `image`, `github-pages-blog-publishing` public URL conventions.
- **New modules**: Preview planner/resolver (for example `linkedin_preview_flow.py`), LinkedIn Images API client (for example `linkedin_image_client.py`).
- **Configuration**: New env vars under LinkedIn publication settings; defaults keep current text-only behavior.
- **Tests**: Extended `tests/test_linkedin_publication.py`; new preview-focused tests with fake image client; no live LinkedIn in CI.
- **Operations**: Operator may need LinkedIn Images API product when using `linkedin_explicit` strategy; OG strategy requires live blog page with sufficient `og:image`, `og:title`, `og:description`, and canonical URL.
