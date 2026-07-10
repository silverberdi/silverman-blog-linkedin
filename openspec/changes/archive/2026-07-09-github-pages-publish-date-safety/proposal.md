## Why

Flow A immediate blog publish for post `02-deferring-is-not-avoiding-it-can-be-architecture` wrote Jekyll frontmatter `date: 2026-07-10 00:00:00 -0500` while GitHub Pages built the site before that timestamp in UTC. Because the public blog `_config.yml` does not set `future: true`, Jekyll excluded the post and the expected URL returned HTTP 404 even though the file was committed. Operators had to manually adjust the public post date and add an explicit `permalink` to restore the intended URL.

## Goals

- Prevent immediate Flow A publication from writing Jekyll posts that GitHub Pages will exclude as future-dated.
- Distinguish **publication timestamp** (safe for Jekyll build inclusion at execution time) from **intended URL date/path** (editorial/calendar target).
- When a source or calendar date is in the future relative to publish execution, adjust the output `date` to a safe publish timestamp and add an explicit `permalink` preserving the intended public URL path.
- Preserve existing behavior when the source frontmatter date is already safe (no unnecessary permalink).
- Keep `source_public_url`, campaign metadata, and `_posts/` filename semantics coherent with the intended public URL.
- Add automated tests and operator documentation for Jekyll future-post exclusion and permalink preservation.
- Do not change LinkedIn publication behavior.

## Non-Goals

- LinkedIn publication, n8n activation, cron/systemd timers, or `calendar.json` edits.
- Enabling `future: true` in the public blog `_config.yml`.
- Git commit/push of the public blog repository.
- Modifications to archived OpenSpec changes or `linkedin-article-preview-image-support`.
- Image generation or ComfyUI changes.
- Deployment.

## What Changes

- Extend `github_pages_publish.py` date resolution to compute a safe Jekyll `date` at publish execution time when the editorial/calendar date would be future-relative to that moment.
- Introduce explicit `permalink` in published frontmatter when the safe publish timestamp date differs from the intended URL date so the canonical public path remains stable.
- Extend `PublishPlan` / publish summaries with `intended_url_date`, `publish_timestamp`, and `permalink_applied` (or equivalent) for operator visibility and tests.
- Wire Flow A `publish_blog_post()` to use safe date resolution and report the intended public URL (not a URL derived only from the adjusted Jekyll `date` when permalink preserves a different path).
- Add delta specs for `github-pages-blog-publishing`, `worker-blog-publishing-endpoint`, and `flow-a-automatic-publishing`.
- Add tests in `tests/test_github_pages_publish.py` and `tests/test_blog_publish_flow.py` covering future-date adjustment, permalink preservation, safe-date no-op, filename/frontmatter coherence, and unchanged LinkedIn paths.
- Update `docs/workflows/blog-publishing-bridge.md` (or adjacent ops doc) explaining Jekyll future-post exclusion, safe publish timestamps, and permalink preservation.

## Capabilities

### New Capabilities

- `github-pages-publish-date-safety`: Worker-side Jekyll publish date and permalink safety for immediate Flow A blog publication — safe publish timestamp vs intended URL date, explicit permalink when adjusted, and coherent public URL reporting.

### Modified Capabilities

- `github-pages-blog-publishing`: Jekyll post filename, frontmatter `date`, optional `permalink`, and public URL reporting updated to separate publication timestamp from intended URL date.
- `worker-blog-publishing-endpoint`: Flow A publish bridge invocation uses safe date resolution; publish results expose intended public URL and date-adjustment metadata.
- `flow-a-automatic-publishing`: Confirmed `source_public_url` and publish metadata align with intended URL path when publish timestamp is adjusted for Jekyll safety.

## Impact

- **Publishing bridge**: `src/silverman_blog_linkedin/github_pages_publish.py` — date resolution, permalink emission, plan/summary fields.
- **Publish flow**: `src/silverman_blog_linkedin/blog_publish_flow.py` — pass execution time, consume intended URL from safe date logic, store confirmed URL metadata.
- **Tests**: `tests/test_github_pages_publish.py`, `tests/test_blog_publish_flow.py`; regression fixture for post `02-deferring-is-not-avoiding-it-can-be-architecture` scenario.
- **Documentation**: `docs/workflows/blog-publishing-bridge.md`.
- **Operations**: Immediate Flow A publish no longer requires manual public-repo date/permalink edits after normal execution.
