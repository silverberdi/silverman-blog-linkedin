## Why

Flow A `POST /generate-linkedin-package` records variant text, paths, and publish-confirmed `source_public_url`, but it does not yet record structured article preview metadata derived from the blog post hero image. Operators and downstream LinkedIn publication work need a canonical `public_image_url` and related fields at package-generation time so link-preview context is available before any LinkedIn API call. A real LinkedIn publication validated successfully but appeared as plain text plus URL without a visual card; recording preview metadata early makes that gap visible and prepares campaigns for a future publication-time slice.

## Goals

- Record article preview metadata during `POST /generate-linkedin-package` from blog front matter `image` and publish-confirmed `source_public_url`.
- Resolve absolute `public_image_url` as `https://silverman.pro/assets/images/<public_slug>.png` (or configured site base URL) from site-root-relative front matter paths such as `/assets/images/<public_slug>.png`.
- When `SILVERMAN_GITHUB_PAGES_REPO_PATH` is configured, validate that the matching public blog image file exists before marking preview status `available`.
- Expose package-level `article_preview` metadata and per-variant preview fields where useful.
- Emit stable warnings when preview metadata is incomplete; package generation MUST still complete unless existing eligibility rules already fail the request.
- Preserve existing LinkedIn package generation, lifecycle transitions, scheduling behavior, and Flow A Core boundaries.
- Add tests with no LinkedIn API calls, no OAuth tokens, and no media upload.

## Non-Goals

- LinkedIn publication-time preview behavior (Images API upload, OG fetch, `publish_linkedin_due_variants()` integration, fail-closed publish semantics).
- Preview enablement env vars for publication (`SILVERMAN_LINKEDIN_PREVIEW_*`).
- Activating n8n, cron, `--real-publish`, or LinkedIn publication (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`).
- Modifying the public blog repository, ComfyUI generation, or archived OpenSpec changes.
- Applying preserved WIP from `stash@{0}` as part of this proposal update.
- Archiving this change or committing/pushing as part of this proposal edit.

## What Changes

- Narrow active OpenSpec change `linkedin-article-preview-image-support` to **LinkedIn article preview metadata support** at package-generation time only.
- Add capability spec `linkedin-article-preview-image-support` covering preview resolution, public-repo validation, status values (`available`, `missing`, `skipped`, `invalid`), package/variant metadata shape, stable warning codes, and test coverage.
- Extend `generate_linkedin_package()` / `linkedin_package_flow.py` to resolve and persist `article_preview` metadata without changing queue, schedule, or publish semantics.
- Add delta spec for `linkedin-derivative-package-generation` (package metadata, HTTP response, tests).
- Add delta spec for `flow-a-automatic-publishing` (umbrella note: metadata recorded at package generation; publication-time preview deferred).
- Update operator documentation for package-generation preview metadata only.

No delta changes to `linkedin-publication-integration`. No new HTTP endpoints. No n8n workflow JSON changes. No LinkedIn API calls.

## Capabilities

### New Capabilities

- `linkedin-article-preview-image-support`: Worker-side LinkedIn article preview **metadata** support during package generation — `public_image_url` / `public_image_path` resolution from front matter, optional public-repo file validation, preview status values, package- and variant-level metadata, stable warning codes, and tests without LinkedIn credentials.

### Modified Capabilities

- `linkedin-derivative-package-generation`: Package generation and `POST /generate-linkedin-package` responses gain `article_preview` metadata and per-variant preview fields; existing generation, idempotency, and lifecycle behavior preserved.
- `flow-a-automatic-publishing`: Umbrella Flow A sequence documents article preview metadata at package generation; LinkedIn publication-time preview remains a deferred follow-up.

## Impact

- **Package generation reference**: `linkedin_package_flow.py`, canonical spec `linkedin-derivative-package-generation`.
- **Blog metadata reference**: front matter `image`, `source_public_url`, `github-pages-blog-publishing` URL conventions, optional `SILVERMAN_GITHUB_PAGES_REPO_PATH` for existence checks.
- **New module (apply phase)**: for example `linkedin_article_preview.py` with `resolve_linkedin_article_preview()` (name MAY differ if equivalent).
- **Configuration**: Reuse existing `SILVERMAN_GITHUB_PAGES_REPO_PATH` and site URL settings; no new LinkedIn preview publication env vars.
- **Tests**: Extend `tests/test_linkedin_package_generation.py` (and related fixtures); no live LinkedIn in CI.
- **Deferred**: Publication-time OG strategy, `linkedin_explicit` Images API upload, `publish_linkedin_due_variants()` preview integration, smoke-script preview reporting — tracked as future work outside this change.
