## MODIFIED Requirements

### Requirement: Blog publish service entry point

The worker SHALL expose a publish service entry point (for example `publish_blog_post(base_path, source_relative_path, ...)`) that orchestrates validation, campaign lifecycle transitions, GitHub Pages bridge application, and optional guarded Git publication for one ready blog post.

The entry point MUST accept optional `git_publication: bool = False` (default false).

The entry point MUST return a structured `BlogPublishResult` (or equivalent dataclass) serializable to JSON for HTTP and n8n consumers.

The entry point MUST NOT move editorial source files between `ready`, `processed`, or `error` folders.

When Git publication is not requested or not enabled, the entry point MUST NOT run `git commit` or `git push` in the public GitHub Pages repository.

When Git publication is requested with `git_publication: true` and enabled per canonical spec `github-pages-git-publication`, the entry point MAY run controlled `git commit` and `git push` only for the campaign publication artifacts after successful blog handoff.

Overall publish `status` MUST be one of `completed`, `partial`, or `failed`. Overall `status` MUST be `partial` when blog handoff succeeded but Git commit or push failed after `git_publication` was requested.

#### Scenario: Publish by relative path

- **WHEN** `publish_blog_post` is called with `source_relative_path` `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` and a valid editorial base path
- **THEN** the function validates the post, may write `_posts/` and `assets/images/` targets in the configured public repo checkout, updates campaign metadata, and returns a structured result without relocating the source Markdown file

#### Scenario: No LinkedIn derivatives

- **WHEN** this child change is applied
- **THEN** no LinkedIn draft files are generated and no `derivatives_*` campaign state transitions occur

#### Scenario: Git publication opt-in after handoff

- **WHEN** `publish_blog_post` is called with `git_publication: true`, Git publication is enabled, and blog handoff succeeds
- **THEN** the function invokes guarded Git publication for the campaign artifacts and includes `blog_git_publication` in the result

#### Scenario: Default publish without Git

- **WHEN** `publish_blog_post` is called without Git publication opt-in
- **THEN** behavior matches pre-change handoff-only semantics and no `git` commands run

#### Scenario: Handoff success with Git failure is partial

- **WHEN** `publish_blog_post` is called with `git_publication: true`, handoff succeeds, and Git push fails
- **THEN** the result has `status: partial`, `blog_publish` preserves successful handoff evidence, and `blog_git_publication.status` is `failed` with a stable error code

### Requirement: GitHub Pages bridge integration

The publish flow MUST invoke the existing `github_pages_publish.py` bridge (for example `run_publish` with `apply=True`) to write prepared Markdown and PNG into the configured public repo checkout.

During implementation (`/opsx-apply`), the worker MUST inspect `src/silverman_blog_linkedin/github_pages_publish.py` and use the actual existing function signatures (`build_plan`, `apply_plan`, `run_publish`). The worker MUST NOT invent bridge APIs. If the existing bridge surface is CLI-oriented or awkward for service use, the worker MAY add a thin internal wrapper around those functions without duplicating publish logic.

The publish flow MUST pass an injectable `execution_time` (default current UTC) into the bridge so publish date safety resolves Jekyll-safe timestamps for immediate publication.

The publish flow MUST NOT duplicate frontmatter normalization, slug derivation, target path logic, or publish date resolution outside the bridge.

The bridge apply step MUST NOT invoke git operations.

Optional Git publication after successful bridge apply MUST be implemented per canonical spec `github-pages-git-publication`, not inside `github_pages_publish.py`.

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

#### Scenario: Bridge apply failure

- **WHEN** the bridge raises an error during apply (for example missing PNG)
- **THEN** publish returns `status: failed` with `blog_publish_failed` and records failure in `blog_publish.error_code` when metadata is written

#### Scenario: Git publication runs after bridge apply

- **WHEN** bridge apply succeeds and Git publication is opted in and enabled
- **THEN** Git publication runs after file writes complete and does not modify bridge planning logic

### Requirement: Non-goals enforcement

This child change MUST NOT modify n8n workflow JSON unless explicitly included in implementation tasks for optional documentation-only export notes.

This child change MUST NOT generate LinkedIn derivative packages or schedule LinkedIn distribution.

This child change MUST NOT physically move source files between editorial folders.

When Git publication is disabled or not requested, this capability MUST NOT commit or push the public GitHub Pages repository.

#### Scenario: No n8n workflow changes by default

- **WHEN** this child change is applied without optional n8n task scope
- **THEN** no files under n8n workflow export paths are modified

#### Scenario: No source file relocation

- **WHEN** publish succeeds
- **THEN** the source Markdown file remains at its original path under `blog-posts/ready/` or active queue/processed path per lifecycle rules

## ADDED Requirements

### Requirement: HTTP Git publication opt-in on POST /publish-blog-post

`POST /publish-blog-post` MUST accept optional request field `git_publication` (boolean, default `false`).

When `git_publication` is `true` and `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true`, the worker MUST attempt guarded Git publication per `github-pages-git-publication` after successful blog handoff in the same request.

When `git_publication` is `false` or omitted, publish behavior MUST remain handoff-only regardless of environment enablement.

#### Scenario: Opt-in triggers Git publication

- **WHEN** a client sends `POST /publish-blog-post` with `git_publication: true`, valid API key, and Git publication is enabled
- **THEN** the response includes `blog_git_publication` after successful handoff and push

#### Scenario: Omitted flag preserves handoff-only behavior

- **WHEN** a client sends `POST /publish-blog-post` without `git_publication` even when Git publication is enabled in the environment
- **THEN** no `git` operations run and the response omits successful `blog_git_publication.pushed` state

#### Scenario: Enabled environment without opt-in does not publish

- **WHEN** `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` and the request omits `git_publication` or sets it false
- **THEN** publish performs handoff only and performs no `git` operations

### Requirement: Extended blog publish error codes for Git publication

The publish flow MUST surface stable Git publication error codes from `github-pages-git-publication` in `errors[]` when Git publication is requested, including at minimum:

- `blog_git_publication_disabled`
- `blog_git_publication_artifacts_missing`
- `blog_git_publication_commit_failed`
- `blog_git_publication_push_failed`
- `blog_git_publication_flow_b_not_allowed`

When handoff succeeds but Git fails, `errors[]` MUST include actionable recovery guidance without secrets.

#### Scenario: Disabled Git publication error code

- **WHEN** `git_publication` is true but enablement flag is false
- **THEN** `errors[]` includes `blog_git_publication_disabled`

#### Scenario: Push failure after handoff uses partial status

- **WHEN** `git_publication` is true, handoff succeeds, and push fails
- **THEN** response `status` is `partial`, `errors[]` includes `blog_git_publication_push_failed`, and `blog_publish` reflects successful handoff

### Requirement: Publish HTTP tests for Git publication

Automated tests MUST cover `POST /publish-blog-post` with `git_publication` opt-in, environment-only enablement without opt-in, partial response when handoff succeeds and push fails, and auth behavior unchanged.

#### Scenario: HTTP opt-in test

- **WHEN** tests call `POST /publish-blog-post` with `git_publication: true` and Git runner fake succeeds
- **THEN** tests verify `blog_git_publication.status` `pushed` in the response

#### Scenario: HTTP partial failure test

- **WHEN** tests call `POST /publish-blog-post` with `git_publication: true`, handoff succeeds, and push fails
- **THEN** tests verify response `status` is `partial` and `blog_publish` success evidence is preserved
