## Why

Flow A blog publish failed in production for calendar item `2026-07-10-deferring-is-not-avoiding-it-can-be-architecture` (`failed_step: publish_blog`, `blog_image_generation_failed`) even though ComfyUI had already produced a valid sibling PNG in `blog-posts/ready/`. The public Jekyll asset at `assets/images/deferring-is-not-avoiding-it-can-be-architecture.png` was never handed off into the configured public blog repo checkout, so publish could not complete safely. Operators should not manually copy images into `silverberdi.github.io` during normal automation.

## Goals

- Make blog image generation and public asset handoff production-safe end-to-end.
- Treat an existing readable public asset at `public-blog/assets/images/<public_slug>.png` as authoritative for Jekyll/public publishing; do not call ComfyUI or overwrite the public asset solely because the ready sibling PNG is missing.
- Adopt an already-generated local sibling PNG beside the ready Markdown source into public assets when the public asset is missing (the post `02` production bug).
- Backfill `blog-posts/ready/<source_slug>.png` from an existing public asset only for bridge/publish compatibility; never overwrite an existing ready sibling PNG.
- Prefer a non-blocking warning when public asset exists but ready sibling backfill fails, as long as publish can proceed safely using the public asset; fail only when downstream validation/publish truly requires the ready sibling.
- After ComfyUI generation or local adoption, copy the image into the public blog repo asset path before publish continues.
- Return a specific stable error code `blog_image_public_asset_handoff_failed` when required handoff/copy into public assets fails (ready sibling → public adoption path).
- On retry, skip duplicate ComfyUI calls when a valid local sibling PNG or public asset already exists.
- Avoid production-blocking ownership/permission issues where possible (readable copied assets; tests must not assume root ownership).
- Add automated tests covering public-asset reuse with backfill success/failure, ready-sibling adoption, generation handoff, handoff failure, retry idempotency, and the post `02` failure scenario.
- Add or update operator documentation explaining automatic handoff, public-asset authority, ready-sibling backfill, and retry behavior.

## Non-Goals

- LinkedIn publication, n8n activation, cron/systemd timers, or calendar changes.
- Queue-slot calendar mode or `calendar.json` modifications.
- Changes to `linkedin-article-preview-image-support`.
- Modifications to archived OpenSpec changes.
- Manual image copy as an expected operator step in production.
- Git commit/push of the public blog repository.

## What Changes

- Add OpenSpec change `blog-image-public-asset-handoff` introducing production-safe public blog image handoff.
- Add capability spec `blog-image-public-asset-handoff` covering detection, reuse, adoption, copy semantics, permissions, retry behavior, and stable error codes.
- Extend `ensure_blog_image()` / blog image orchestration to evaluate public repo assets, adopt sibling ready PNGs, and hand off to `public-blog/assets/images/<public_slug>.png`.
- Extend `publish_blog_post()` integration so image prerequisites include the public asset path and failures surface `blog_image_public_asset_handoff_failed` distinctly from generic generation failures.
- Add delta specs for `comfyui-blog-image-generation` and `worker-blog-publishing-endpoint`.
- Add tests in `tests/test_blog_image_generation.py` and `tests/test_blog_publish_flow.py` (or dedicated handoff tests) with fakes/mocks; no live ComfyUI required.
- Update operator documentation (for example `docs/workflows/blog-publishing-bridge.md` or adjacent ops doc) describing automatic handoff, canonical public paths, and retry reuse.

No n8n JSON changes, no LinkedIn API changes, and no execution-connector changes unless strictly required to pass through the new error code (expected to flow via existing publish result fields).

## Capabilities

### New Capabilities

- `blog-image-public-asset-handoff`: Worker-side public blog image handoff — detect and reuse existing public assets, adopt sibling ready PNGs, copy generated or adopted images into the configured public repo `assets/images/` path, idempotent retry without duplicate ComfyUI, permission-safe copy, metadata recording, and stable `blog_image_public_asset_handoff_failed` error code.

### Modified Capabilities

- `comfyui-blog-image-generation`: Extend missing-image detection and `ensure_blog_image()` to consider public repo assets, perform public asset handoff after generation or adoption, skip ComfyUI when a valid public or local image is reusable, and add handoff-specific error codes and metadata fields.
- `worker-blog-publishing-endpoint`: Publish flow sequence and error surfacing updated so image prerequisites include public asset handoff success; publish responses distinguish handoff failures from generic `blog_image_generation_failed`.

## Impact

- **Image orchestration**: `src/silverman_blog_linkedin/blog_image_generation.py` — public asset detection, handoff copy, reuse logic, new error code.
- **Publish flow**: `src/silverman_blog_linkedin/blog_publish_flow.py` — pass public repo path into image step; surface handoff results in `blog_image_generation` summary.
- **Publishing bridge**: `src/silverman_blog_linkedin/github_pages_publish.py` — may gain a thin reusable copy helper for public `assets/images/` writes without duplicating bridge apply logic.
- **Configuration**: Reuse `SILVERMAN_GITHUB_PAGES_REPO_PATH`; no new secrets.
- **Tests**: `tests/test_blog_image_generation.py`, `tests/test_blog_publish_flow.py`, and/or new handoff-focused tests; fixtures for post `02-deferring-is-not-avoiding-it-can-be-architecture`.
- **Documentation**: `docs/workflows/blog-publishing-bridge.md` or related ops doc.
- **Operations**: Production publish no longer requires manual `cp` into `silverberdi.github.io/assets/images/`; retries reuse existing valid images.
