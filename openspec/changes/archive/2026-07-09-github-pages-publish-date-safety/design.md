## Context

Flow A blog publish (`publish_blog_post` → `github_pages_publish.run_publish`) prepares Jekyll posts for [silverman.pro](https://silverman.pro). The bridge currently sets frontmatter `date` from the editorial/calendar `publication_date` using a fixed suffix (` 00:00:00 -0500`) and derives the public URL and `_posts/` filename from that same calendar date.

Production failure on post `02-deferring-is-not-avoiding-it-can-be-architecture` (calendar target `2026-07-10`):

- Worker wrote `date: 2026-07-10 00:00:00 -0500` into `_posts/2026-07-10-deferring-is-not-avoiding-it-can-be-architecture.md`.
- GitHub Pages built before that timestamp in UTC.
- Jekyll excludes future posts by default (`future` not enabled in `_config.yml`).
- Expected URL returned HTTP 404 until operators manually set `date: 2026-07-09 21:08:00 -0500` and `permalink: /2026/07/10/deferring-is-not-avoiding-it-can-be-architecture/`.

Constraints:

- Worker HTTP boundary only; no n8n Execute Command (ADR-0001).
- Do not modify public blog `_config.yml` or enable `future: true`.
- No LinkedIn, n8n activation, calendar edits, or deployment in this change.
- Bridge remains the single source of truth for slug, path, frontmatter, and URL derivation (`github_pages_publish.py`).
- Campaign `publication_date` and idempotency keys must remain aligned with editorial/calendar intent.

## Goals / Non-Goals

**Goals:**

- Separate **publication timestamp** (Jekyll-safe `date` at execution time) from **intended URL date** (editorial/calendar target from source frontmatter or explicit override).
- For immediate Flow A publish, ensure Jekyll `date` is never in the future relative to publish execution time.
- When dates are adjusted, emit explicit `permalink` preserving the intended `/YYYY/MM/DD/<public-slug>/` path.
- Keep `_posts/YYYY-MM-DD-<public-slug>.md` filename, reported `public_url`, and campaign `source_public_url` aligned with the **intended URL date**, not the adjusted Jekyll timestamp.
- Preserve existing behavior when the editorial date is already safe (no spurious `permalink`).
- Expose date-resolution metadata in publish plans/results for tests and operators.
- Add automated tests and operator documentation.

**Non-Goals:**

- LinkedIn publication behavior changes.
- `future: true` in public Jekyll config.
- Cron/systemd scheduled publish execution.
- Git commit/push of the public blog repo.
- Image generation, ComfyUI, or `linkedin-article-preview-image-support`.
- Modifying archived OpenSpec changes.

## Decisions

### 1. Introduce `PublishDateResolution` in `github_pages_publish.py`

**Decision:** Add a resolver (for example `resolve_publish_dates(intended_url_date, execution_time)`) returning:

- `intended_url_date: date` — editorial/calendar target (from source frontmatter or CLI `--date`)
- `publish_timestamp: datetime` — actual safe datetime written to Jekyll `date`
- `permalink: str | None` — site-relative path `/YYYY/MM/DD/<public-slug>/` when adjustment required; `None` when safe
- `date_adjusted: bool` — whether permalink/timestamp adjustment occurred

**Rationale:** Single place for future-post safety logic reused by CLI and Flow A publish flow.

**Alternative considered:** Inline check only in `blog_publish_flow.py`. Rejected — duplicates bridge semantics and breaks CLI parity.

### 2. Future detection compares Jekyll datetime, not calendar date alone

**Decision:** Treat the editorial date as future when the Jekyll datetime that would be written (`intended_url_date` + configured timezone suffix, default `00:00:00 -0500`) is strictly after `execution_time` (timezone-aware, compared in UTC).

**Rationale:** Matches Jekyll `site.time` behavior and the production failure mode (midnight -0500 on a calendar date can still be future in UTC at evening publish time).

**Alternative considered:** Compare calendar dates only in America/Bogota. Rejected — insufficient when UTC build time crosses midnight boundary differently.

### 3. Immediate publish adjusts timestamp and adds permalink (preferred path)

**Decision:** When future-relative and publish mode is immediate (default for Flow A and CLI `--apply`), set `publish_timestamp` to `execution_time` (truncated to second, normalized to configured editorial timezone `-0500` for output formatting) and set `permalink` to `/YYYY/MM/DD/<public-slug>/` using `intended_url_date`.

**Rationale:** Matches the operator manual fix; avoids 404 on immediate publication while preserving calendar URL.

**Alternative considered:** Fail with error requiring scheduled execution. Supported as a secondary mode (for example explicit `scheduled_publish=true` or future-only CLI flag) but **not** the Flow A default.

### 4. `_posts/` filename and public URL use intended URL date

**Decision:**

- `_posts/` filename prefix: `intended_url_date` (`YYYY-MM-DD-<public-slug>.md`)
- `public_url` / `source_public_url`: derived from `intended_url_date` + `public_slug`
- Frontmatter `date`: formatted from `publish_timestamp`
- Frontmatter `permalink`: present only when `date_adjusted`

**Rationale:** Keeps calendar filenames and confirmed URLs stable; Jekyll serves the intended path via permalink when `date` is earlier.

### 5. Safe dates: no permalink, preserve current suffix behavior

**Decision:** When `intended_url_date` is not future-relative to execution time, `publish_timestamp` uses `intended_url_date` at `00:00:00 -0500` (existing `jekyll_date` behavior), `permalink` is omitted, and all outputs match current bridge behavior.

**Rationale:** Requirement 6 — no unnecessary permalink for already-safe posts.

### 6. Campaign `publication_date` remains editorial intent

**Decision:** `campaign_lifecycle` `publication_date`, `campaign_id`, and idempotency keys continue to use the editorial `YYYY-MM-DD` from source frontmatter (intended URL date). Only the written Jekyll `date` field may differ.

**Rationale:** Calendar orchestration and duplicate prevention are keyed on editorial schedule, not GitHub Pages build clock.

### 7. Flow A passes execution time into bridge

**Decision:** `publish_blog_post()` supplies `execution_time=datetime.now(timezone.utc)` (injectable in tests) to `run_publish` / `build_plan`. Bridge performs resolution internally.

**Rationale:** Publish flow must not duplicate date logic; tests can freeze time for regression scenarios.

### 8. Reconciliation and idempotency compare canonical rendered output

**Decision:** `render_expected_public_post` and publish reconciliation use the same `PublishDateResolution` so expected bytes include `permalink` when adjusted.

**Rationale:** Smoke tests and `already_published` reconciliation remain correct after date adjustment.

### 9. Optional explicit future-only failure mode (secondary)

**Decision:** Expose a resolver parameter `on_future_date: "adjust" | "fail"` defaulting to `"adjust"`. When `"fail"`, raise `PublishError` with stable code `blog_publish_future_date_requires_scheduled_execution` (or bridge-level equivalent) instead of adjusting.

**Rationale:** Supports future scheduled execution without enabling it in this change; Flow A uses `"adjust"`.

## Risks / Trade-offs

- **[Risk] Jekyll permalink format mismatch** → Mitigation: use site-root-relative `/YYYY/MM/DD/<slug>/` matching existing silverman.pro URLs; test against post `02` regression fixture.
- **[Risk] Drift between campaign `publication_date` and Jekyll `date`** → Mitigation: document in ops guide; expose `date_adjusted` in publish result; operators must not manually edit dates after normal Flow A execution.
- **[Risk] CLI `--date` in the future with `--apply`** → Mitigation: default adjust+permalink; document that immediate apply always writes Jekyll-safe timestamps.
- **[Risk] Reconciliation false negatives when permalink added** → Mitigation: update `render_expected_public_post` and reconciliation tests together.
- **[Risk] LinkedIn CTA URL mismatch** → Mitigation: `source_public_url` uses intended URL date path; no LinkedIn code changes required.

## Migration Plan

1. Implement resolver and bridge changes behind this OpenSpec change.
2. Add unit tests with frozen execution time reproducing post `02` scenario.
3. Add publish-flow integration tests confirming `source_public_url` uses intended path when `date` adjusted.
4. Update operator documentation.
5. Deploy worker update; no public blog config changes required.
6. Existing published posts with manual permalink fixes remain valid; no retroactive rewrite.

## Open Questions

- None blocking implementation. Scheduled future-only publish mode remains out of scope until a dedicated calendar execution change enables it.
