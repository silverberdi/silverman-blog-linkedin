## MODIFIED Requirements

### Requirement: GitHub Pages bridge integration

The publish flow MUST invoke the existing `github_pages_publish.py` bridge (for example `run_publish` with `apply=True`) to write prepared Markdown and PNG into the configured public repo checkout.

During implementation (`/opsx-apply`), the worker MUST inspect `src/silverman_blog_linkedin/github_pages_publish.py` and use the actual existing function signatures (`build_plan`, `apply_plan`, `run_publish`). The worker MUST NOT invent bridge APIs. If the existing bridge surface is CLI-oriented or awkward for service use, the worker MAY add a thin internal wrapper around those functions without duplicating publish logic.

The publish flow MUST pass an injectable `execution_time` (default current UTC) into the bridge so publish date safety resolves Jekyll-safe timestamps for immediate publication.

The publish flow MUST NOT duplicate frontmatter normalization, slug derivation, target path logic, or publish date resolution outside the bridge.

The publish flow MUST NOT invoke git operations.

Public repo path MUST come from configuration (`SILVERMAN_GITHUB_PAGES_REPO_PATH`). When missing or layout-invalid, publish MUST fail with `blog_publish_public_repo_not_configured`.

#### Scenario: Files written via bridge

- **WHEN** publish succeeds for a valid ready post pair
- **THEN** `_posts/YYYY-MM-DD-<public-slug>.md` and `assets/images/<public-slug>.png` exist in the configured public repo checkout with content prepared by the bridge using intended URL date in the filename

#### Scenario: Public repo not configured

- **WHEN** `SILVERMAN_GITHUB_PAGES_REPO_PATH` is unset or the checkout lacks required layout
- **THEN** publish fails with `blog_publish_public_repo_not_configured` before apply

#### Scenario: Future editorial date published safely

- **WHEN** Flow A immediate publish runs with intended URL date `2026-07-10`, execution time before that Jekyll datetime, and public slug `deferring-is-not-avoiding-it-can-be-architecture`
- **THEN** the bridge writes `_posts/2026-07-10-deferring-is-not-avoiding-it-can-be-architecture.md` with safe frontmatter `date`, explicit `permalink`, and publish result `source_public_url` `https://silverman.pro/2026/07/10/deferring-is-not-avoiding-it-can-be-architecture/`

### Requirement: Blog publish result shape

`BlogPublishResult` (or equivalent) MUST include fields sufficient for n8n branching and operator review, including at minimum:

- `status`: `completed` or `failed`
- `campaign_id`, `state`, `source_slug`, `public_slug`, `publication_date`
- `source_relative_path`, `image_relative_path`
- `source_public_url`
- `errors`, `warnings`
- `validation` (summary object)
- `blog_publish` (object)
- `blog_image_generation` (object summary when generation was evaluated)
- `metadata_written`, `metadata_error_code`

When publish date adjustment occurs, `blog_publish` (or equivalent summary) SHOULD include `date_adjusted` and `publish_timestamp` metadata.

`publication_date` in the result MUST remain the editorial intended `YYYY-MM-DD` from source frontmatter even when the written Jekyll `date` differs.

#### Scenario: Successful publish response

- **WHEN** publish completes successfully
- **THEN** response includes `source_public_url` matching the bridge-computed intended public URL for the post

#### Scenario: Date adjustment metadata in response

- **WHEN** publish adjusts Jekyll `date` for future-post safety
- **THEN** response includes `date_adjusted` true and `source_public_url` using the intended URL date path

#### Scenario: Blog image generation summary in response

- **WHEN** publish evaluates blog image generation for a ready post
- **THEN** response includes `blog_image_generation` with at minimum `status` and, when applicable, `public_image_path` and `error_code`
