# worker-blog-publishing-endpoint

## Purpose

Flow A worker blog publishing for the `silverman-blog-linkedin` HTTP worker: validation-first publish orchestration, campaign lifecycle transitions, GitHub Pages bridge integration, idempotent `already_published` handling, and `POST /publish-blog-post`. Implements child slice 4 under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`.
## Requirements
### Requirement: Umbrella and dependency references

This child change SHALL implement Flow A worker blog publishing under active umbrella change `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 4).

Blog publish behavior MUST align with Flow A policy in canonical spec `editorial-canon` and artifact `content-strategy/silverman-editorial-system.md`.

Ready-post validation MUST be governed by canonical capability `ready-post-editorial-validation` and worker module `ready_post_validation.py`.

For non-short-circuited publish execution, `publish_blog_post()` MUST use two validation phases in this order:

1. `validate_ready_post_pre_generation()`;
2. editorial image remediation (local only);
3. authorized hash reconciliation when frontmatter changes;
4. full `validate_ready_post()`;
5. public asset handoff;
6. GitHub Pages publish.

Editorial image remediation and hash reconciliation are permitted before full validation because they are controlled local canonicalization steps, not public publish side effects.

Public asset handoff and public post writes MUST occur only after full validation succeeds.

An `already_published` idempotency short-circuit is exempt from both validation phases and all image/public side effects.

Campaign metadata and state transitions MUST use canonical spec `flow-a-lifecycle` and worker module `campaign_lifecycle.py`.

File preparation and public URL derivation MUST use canonical spec `github-pages-blog-publishing` and worker module `github_pages_publish.py` without duplicating publish logic.

Flow B campaigns MUST NOT enter this publish path.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, validation child `ready-post-editorial-validation`, lifecycle child `flow-a-lifecycle-and-duplicate-prevention`, and publishing bridge `github-pages-blog-publishing`

#### Scenario: Flow B blocked

- **WHEN** `publish_blog_post` is invoked for a campaign with `flow` `flow_b`
- **THEN** the operation fails with error code `blog_publish_flow_b_not_allowed` and does not write public repo files

#### Scenario: Staged validation does not require full validation before local remediation

- **WHEN** `publish_blog_post` runs editorial image remediation or authorized hash reconciliation for a non-short-circuited campaign
- **THEN** those steps are permitted before full `validate_ready_post()` succeeds and no public asset handoff or public post write occurs until full validation succeeds
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
### Requirement: Publish flow validation and image generation ordering

Ready-post validation MUST be governed by canonical capability `ready-post-editorial-validation`.

The `already_published` metadata/idempotency short-circuit MUST be evaluated first, before pre-generation validation, full validation, editorial image remediation, public asset handoff, `resolve_source_paths()`, GitHub Pages bridge planning/apply, or any public repository read/write performed only for a publish attempt.

When the short-circuit applies for a Flow A campaign with matching stored identity evidence (`state` `blog_published`, matching `source_content_sha256`, matching `blog_publish.idempotency_key`, and stored `source_public_url`), `publish_blog_post()` MUST return `status: completed` with `blog_publish.status` `already_published` without requiring Markdown or PNG to be resolvable from `ready/`, `queued/`, or `processed/`, without calling `resolve_source_paths()`, and without overwriting public files.

For non-short-circuited campaigns, `publish_blog_post()` MUST orchestrate the following strict order:

1. **Pre-generation gate** — `validate_ready_post_pre_generation()` validates deterministic requirements without blocking solely on missing/empty generatable frontmatter `image` or a generatable missing companion PNG.
2. **Editorial image remediation** — `ensure_editorial_blog_image()` (or staged equivalent with `handoff=False`) per `comfyui-blog-image-generation`, using the active `source_relative_path` folder (`ready/` or `queued/`); detect, generate/adopt/backfill locally; patch canonical frontmatter when authorized; **no public repo write**.
3. **Authorized hash reconciliation** — when editorial remediation patches frontmatter, recompute active `source_content_sha256`, persist on the same campaign, and recompute blog publish idempotency key per `flow-a-lifecycle`; metadata-write failure blocks publish without public repo writes.
4. **Full validation** — `validate_ready_post()` requires canonical `image` and companion PNG beside the active folder.
5. **Public asset handoff** — `handoff_public_blog_image()` (or staged equivalent) per `blog-image-public-asset-handoff`; runs only after full validation succeeds.
6. **GitHub Pages post publish** — existing publish bridge semantics.

Editorial image remediation and hash reconciliation are permitted before full validation because they are controlled local canonicalization steps, not public publish side effects. Public asset handoff and public post writes MUST occur only after full validation succeeds.

If pre-generation validation returns `ok: false`, the publish flow MUST return `status: failed` with validation error codes, MUST NOT call editorial remediation, MUST NOT call full `validate_ready_post()`, MUST NOT call public handoff, MUST NOT transition to `blog_publish_pending`, and MUST NOT write public repo files.

If editorial remediation is required and returns failure, the publish flow MUST return `status: failed` with the stable error code from the image step (including `blog_image_generation_*` or local write/patch inconsistency codes), MUST NOT call full `validate_ready_post()`, MUST NOT call public handoff, MUST NOT transition to `blog_publish_pending`, and MUST NOT write public repo files. Generation failures MUST NOT be reported as `ready_post_image_missing`.

If authorized hash reconciliation fails to persist metadata, the publish flow MUST return `status: failed` with primary error code `blog_publish_hash_reconciliation_failed`, MAY include the underlying metadata persistence error separately, MUST NOT call public handoff, and MUST NOT write public repo files.

If full validation returns `ok: false`, the publish flow MUST return `status: failed` with validation error codes, MUST NOT call public handoff, MUST NOT transition to `blog_publish_pending`, and MUST NOT write public repo post files. No public asset write may have occurred.

If public handoff fails after successful full validation, the publish flow MUST return `status: failed` with `blog_image_public_asset_handoff_failed`, MUST NOT write public repo post files, and MUST preserve the validated editorial PNG.

`publish_blog_post()` MUST pass the configured public GitHub Pages repository path into handoff helpers when handoff runs.

GitHub Pages source resolution MUST use active `source_relative_path` supporting `blog-posts/ready/`, `blog-posts/queued/`, and `blog-posts/processed/` for idempotent reruns per `github-pages-blog-publishing`.

`ensure_blog_image()` MAY remain a compatibility facade for non-publish callers, but `publish_blog_post` MUST enforce staged ordering internally.

#### Scenario: Queued Markdown-only publish runs remediation before full validation and handoff

- **WHEN** `publish_blog_post` is called with `source_relative_path` `blog-posts/queued/01-example.md`, absent `image`, no companion PNG, and ComfyUI enabled
- **THEN** pre-generation validation passes, editorial remediation runs and writes `blog-posts/queued/01-example.png` without public write, hash is reconciled, full validation runs, handoff runs, and publish may proceed

#### Scenario: Pre-generation failure skips remediation and handoff

- **WHEN** `publish_blog_post` is called and pre-generation validation fails for non-canonical frontmatter `image`
- **THEN** editorial remediation is not called, full validation is not called, handoff is not called, and publish returns failed with the pre-generation error

#### Scenario: ComfyUI failure does not report ready_post_image_missing

- **WHEN** `publish_blog_post` is called, ComfyUI generation is required, and editorial remediation fails at ComfyUI
- **THEN** response `status` is `failed` with a `blog_image_generation_*` error code, full `validate_ready_post` is not called, handoff is not called, and `ready_post_image_missing` is not the primary error

#### Scenario: Full validation failure performs no public asset write

- **WHEN** editorial remediation succeeds but `validate_ready_post` fails afterward
- **THEN** publish returns failed with the validation error, no public asset file is written, and no public post file is written

#### Scenario: Direct ready publish path preserved with missing image remediation

- **WHEN** `publish_blog_post` is called with `blog-posts/ready/01-example.md`, absent `image`, and no companion PNG
- **THEN** pre-generation validation, editorial remediation (including frontmatter patch), hash reconciliation, full validation, handoff, and publish proceed as before queue lifecycle

#### Scenario: Already published skips validation and image steps

- **WHEN** campaign is already `blog_published` with matching hash and idempotency key
- **THEN** response `status` is `completed`, `blog_publish.status` is `already_published`, validation and image steps are not called, and no public repo files are written

#### Scenario: Public handoff failure blocks publish after full validation

- **WHEN** editorial remediation and full validation succeed but public asset handoff fails
- **THEN** `publish_blog_post` returns `status: failed` with `blog_image_public_asset_handoff_failed`, does not write public repo post files, and preserves the editorial PNG

#### Scenario: Authorized frontmatter patch updates campaign hash safely

- **WHEN** editorial remediation patches missing `image` frontmatter for a queued source
- **THEN** active `source_content_sha256` and blog publish idempotency key are updated on the same campaign, `campaign_id` is unchanged, and validation does not fail with `campaign_content_hash_changed`

#### Scenario: Unrelated body mutation still rejected

- **WHEN** source Markdown body changes between queue acceptance and publish outside authorized image remediation
- **THEN** publish fails with `campaign_content_hash_changed` or `blog_publish_content_hash_changed` per existing guards and does not write public repo files
### Requirement: Campaign state transitions for blog publish

For Flow A blog publish, the worker MUST support these transitions:

- `validated` → `blog_publish_pending` → `blog_published` on success

A raw `ready` post MAY be submitted to `POST /publish-blog-post`. The publish flow MUST run `validate_ready_post()` first; if validation succeeds, campaign state becomes `validated` and publish may proceed. Publishing MUST be rejected only if, after validation, the campaign is not eligible for `validated` → `blog_publish_pending`.

The worker MUST reject publish attempts when campaign state is:

- `validation_failed`
- `error`
- a state beyond `blog_published` that would regress lifecycle: `derivatives_pending`, `derivatives_generated`, `distribution_scheduled`, `distribution_complete`, `flow_a_complete`

State `blog_published` is NOT invalid when it satisfies the idempotent `already_published` checks in the publish flow sequence requirement.

State `ready` MUST be handled by validation, not rejected upfront.

Invalid state attempts MUST fail with error code `blog_publish_invalid_campaign_state`.

#### Scenario: Happy-path state progression

- **WHEN** a validated campaign publishes successfully
- **THEN** campaign `state` progresses `validated` → `blog_publish_pending` → `blog_published` with `state_history` entries for each transition

#### Scenario: Ready post validated then published

- **WHEN** campaign `state` is `ready` and `publish_blog_post` is invoked for a valid ready post
- **THEN** `validate_ready_post()` runs first, campaign transitions to `validated` on validation success, and publish proceeds to `blog_publish_pending` without upfront `blog_publish_invalid_campaign_state` rejection

#### Scenario: Validation failed state rejected

- **WHEN** campaign `state` is `validation_failed`
- **THEN** the operation fails with `blog_publish_invalid_campaign_state`

#### Scenario: Error state rejected

- **WHEN** campaign `state` is `error`
- **THEN** the operation fails with `blog_publish_invalid_campaign_state`

#### Scenario: Regressive state rejected

- **WHEN** campaign `state` is `derivatives_pending`, `derivatives_generated`, `distribution_scheduled`, `distribution_complete`, or `flow_a_complete`
- **THEN** the operation fails with `blog_publish_invalid_campaign_state` without regressing `state`
### Requirement: Content hash guard

If stored campaign `source_content_sha256` differs from the current source file digest at publish time, the publish flow MUST fail with error code `blog_publish_content_hash_changed` and MUST NOT overwrite public repo files or campaign publish metadata.

#### Scenario: Changed content after validation

- **WHEN** campaign is `validated` but source file bytes differ from stored `source_content_sha256`
- **THEN** publish fails with `blog_publish_content_hash_changed`
### Requirement: Blog publish idempotency

Blog publish MUST use the idempotency key from `build_blog_publish_idempotency_key()` in `campaign_lifecycle.py`.

If campaign `state` is `blog_published`, `flow` is `flow_a`, stored `blog_publish.idempotency_key` matches the computed key, `source_content_sha256` matches, and stored `source_public_url` exists, the publish flow MUST return `status: completed` with `blog_publish.status` `already_published` without calling `validate_ready_post()` and without overwriting existing public repo files.

If public repo targets already exist but campaign metadata does not prove the same idempotency key, the publish flow MUST fail with `blog_publish_target_exists` and MUST NOT overwrite.

#### Scenario: Idempotent re-run after published

- **WHEN** publish is requested again for a campaign already `blog_published` with `flow` `flow_a`, matching idempotency key, matching content hash, and stored `source_public_url`
- **THEN** response `status` is `completed`, `blog_publish.status` is `already_published`, `validate_ready_post()` is not called, and no duplicate files are written

#### Scenario: Target exists without matching metadata

- **WHEN** `_posts/` or `assets/images/` targets exist but campaign metadata does not prove the same blog idempotency key
- **THEN** publish fails with `blog_publish_target_exists` without overwriting files

#### Scenario: Content change produces different idempotency key

- **WHEN** `source_content_sha256` changes
- **THEN** the computed blog publish idempotency key differs from any prior `blog_publish.idempotency_key` on the campaign
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
### Requirement: Campaign metadata blog_publish updates

On publish attempt, the worker MUST update campaign `blog_publish` with:

- `idempotency_key`
- `status`: one of `pending`, `published`, `already_published`, or `failed`
- `source_public_url` when known
- `published_at` when publish completes
- `public_repo_path` or safe relative published paths when available
- `error_code` when failed

Campaign metadata MUST NOT store full Markdown content, generated draft bodies, or secrets.

#### Scenario: Successful publish metadata

- **WHEN** blog publish completes successfully
- **THEN** `blog_publish.status` is `published`, `source_public_url` is set, `published_at` is a UTC ISO8601 timestamp, and `source_public_url` is also set at campaign top level

#### Scenario: Failed publish metadata

- **WHEN** blog publish fails after `blog_publish_pending` transition
- **THEN** `blog_publish.status` is `failed` and `blog_publish.error_code` records the stable failure code

#### Scenario: Metadata excludes body content

- **WHEN** campaign metadata is written after publish
- **THEN** the persisted JSON does not include `markdown_content` or `generated_draft_content`
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
### Requirement: HTTP endpoint POST /publish-blog-post

The worker SHALL expose `POST /publish-blog-post` protected by the same API-key authentication as other mutating worker endpoints.

Request body MUST accept:

- `source_relative_path` (required)
- `site_url` (optional; default `https://silverman.pro`)
- `public_slug` (optional; only when bridge safely supports override)

Response body MUST include at minimum:

- `status`: `completed` or `failed`
- `campaign_id`, `state`, `source_slug`, `public_slug`, `publication_date`
- `source_relative_path`, `image_relative_path`
- `source_public_url`
- `errors`, `warnings`
- `validation` (summary object)
- `blog_publish` (object)
- `blog_image_generation` (object summary when generation was evaluated)
- `metadata_written`, `metadata_error_code`

#### Scenario: Authenticated publish request

- **WHEN** a client sends `POST /publish-blog-post` with valid API key and `source_relative_path`
- **THEN** the worker returns HTTP 200 with the structured publish result JSON

#### Scenario: Missing API key rejected

- **WHEN** a client sends `POST /publish-blog-post` without valid API key
- **THEN** the worker rejects the request with the same unauthorized behavior as other protected endpoints

#### Scenario: Source public URL in response

- **WHEN** publish completes successfully
- **THEN** response includes `source_public_url` matching the bridge-computed public URL for the post

#### Scenario: Blog image generation summary in response

- **WHEN** publish evaluates blog image generation for a ready post
- **THEN** response includes `blog_image_generation` with at minimum `status` and, when applicable, `public_image_path` and `error_code`
### Requirement: ComfyUI blog image generation integration reference

Blog publish MUST integrate staged blog image generation and public asset handoff per canonical specs `comfyui-blog-image-generation` and `blog-image-public-asset-handoff`, using worker modules `blog_image_generation.py` and `comfyui_client.py`.

`publish_blog_post()` MUST enforce staged ordering internally: editorial remediation before full validation; public handoff only after full validation.

`publish_blog_post()` MUST pass the configured public GitHub Pages repository path into handoff helpers when handoff runs.

When ComfyUI generation is disabled, publish behavior MUST remain backward compatible with posts that already include valid `image` front matter, companion PNG, and public asset (or successful adoption path).

When front matter `image` points to a non-canonical path, publish MUST NOT invoke generation for remediation; validation or operator remediation MUST handle the mismatch.

#### Scenario: Disabled generation with existing public asset

- **WHEN** ComfyUI generation is disabled and the ready post already has valid `image`, companion PNG, and public asset
- **THEN** publish proceeds through validation and bridge apply unchanged from pre-handoff behavior
### Requirement: Extended blog publish error surfacing for image generation

When publish fails due to blog image generation or public asset handoff, `errors[]` MUST include the stable error code from `comfyui-blog-image-generation` or `blog-image-public-asset-handoff` (for example `blog_image_generation_comfyui_failed`, `blog_image_public_asset_handoff_failed`, or `blog_image_generation_failed` only when no specific code applies).

#### Scenario: Handoff failure visible in publish errors

- **WHEN** publish aborts because public asset handoff failed
- **THEN** `errors[]` includes `blog_image_public_asset_handoff_failed` and `blog_image_generation.status` is `failed` in the response

#### Scenario: Generation failure visible in publish errors

- **WHEN** publish aborts because ComfyUI generation failed
- **THEN** `errors[]` includes a `blog_image_generation_*` code and `blog_image_generation.status` is `failed` in the response
### Requirement: Configuration

Editorial base path MUST come from existing worker configuration (`SILVERMAN_BLOG_LINKEDIN_BASE_PATH`).

Public GitHub Pages repository checkout path MUST come from `SILVERMAN_GITHUB_PAGES_REPO_PATH`.

Site URL MUST default to `https://silverman.pro` when not provided in the request.

#### Scenario: Default site URL

- **WHEN** `site_url` is omitted from the HTTP request
- **THEN** public URL calculation uses `https://silverman.pro`
### Requirement: Stable blog publish error codes

The publish flow MUST use stable machine-readable error codes including at minimum:

- `blog_publish_hash_reconciliation_failed`
- `blog_publish_validation_failed`
- `blog_publish_invalid_campaign_state`
- `blog_publish_content_hash_changed`
- `blog_publish_target_exists`
- `blog_publish_failed`
- `blog_publish_metadata_write_failed`
- `blog_publish_public_repo_not_configured`
- `blog_publish_source_not_ready`
- `blog_publish_flow_b_not_allowed`

#### Scenario: Invalid campaign state error code

- **WHEN** publish is attempted from a disallowed campaign state
- **THEN** `errors[]` includes `blog_publish_invalid_campaign_state`

#### Scenario: Metadata write failure

- **WHEN** campaign metadata cannot be written after a publish attempt
- **THEN** response includes `metadata_written: false` and `metadata_error_code` describing the failure
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

### Requirement: Live-site confirmation opt-in on publish service entry point

The publish service entry point MUST accept optional `live_site_confirmation: bool = False` (default false).

When `live_site_confirmation: true` and enabled per canonical spec `blog-live-site-confirmation`, the entry point MUST run HTTP live-site confirmation after successful Git publication evidence exists in the same invocation or campaign metadata.

Overall publish `status` MUST be `partial` when Git push succeeded but live-site confirmation failed after `live_site_confirmation` was requested.

#### Scenario: Live confirmation opt-in after successful push

- **WHEN** `publish_blog_post` is called with `git_publication: true`, `live_site_confirmation: true`, both features enabled, handoff and push succeed
- **THEN** the function invokes live-site confirmation and includes `blog_live_site_publication` in the result

#### Scenario: Default publish without live confirmation

- **WHEN** `publish_blog_post` is called without `live_site_confirmation` opt-in
- **THEN** no HTTP probes run and the result omits successful `blog_live_site_publication.confirmed` state

#### Scenario: Push success with live confirmation failure is partial

- **WHEN** `publish_blog_post` is called with `live_site_confirmation: true`, push succeeds, and all probe attempts fail
- **THEN** the result has `status: partial`, `blog_git_publication` preserves push evidence, and `blog_live_site_publication.status` is `failed`

### Requirement: HTTP live-site confirmation opt-in on POST /publish-blog-post

`POST /publish-blog-post` MUST accept optional request field `live_site_confirmation` (boolean, default `false`).

When `live_site_confirmation` is `true` and `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true`, the worker MUST attempt live-site confirmation per `blog-live-site-confirmation` after successful Git publication in the same request.

When `live_site_confirmation` is `false` or omitted, publish behavior MUST NOT perform HTTP probes regardless of environment enablement.

#### Scenario: Opt-in triggers live confirmation

- **WHEN** a client sends `POST /publish-blog-post` with `git_publication: true`, `live_site_confirmation: true`, valid API key, and both features enabled
- **THEN** the response includes `blog_live_site_publication` after successful push and probe

#### Scenario: Omitted flag preserves no-probe behavior

- **WHEN** a client sends `POST /publish-blog-post` without `live_site_confirmation` even when live confirmation is enabled in the environment
- **THEN** no HTTP probes run

### Requirement: Extended blog publish error codes for live-site confirmation

The publish flow MUST surface stable live-site confirmation error codes from `blog-live-site-confirmation` in `errors[]` when live confirmation is requested, including at minimum:

- `blog_live_site_confirmation_disabled`
- `blog_live_site_confirmation_git_required`
- `blog_live_site_confirmation_invalid_url`
- `blog_live_site_confirmation_unreachable`

When push succeeded but live confirmation fails, `errors[]` MUST include actionable recovery guidance without secrets.

#### Scenario: Disabled live confirmation error code

- **WHEN** `live_site_confirmation` is true but enablement flag is false
- **THEN** `errors[]` includes `blog_live_site_confirmation_disabled`

#### Scenario: Probe failure after push uses partial status

- **WHEN** `live_site_confirmation` is true, push succeeds, and all probes fail
- **THEN** response `status` is `partial`, `errors[]` includes `blog_live_site_confirmation_unreachable`, and `blog_git_publication` reflects successful push

### Requirement: Publish HTTP tests for live-site confirmation

Automated tests MUST cover `POST /publish-blog-post` with `live_site_confirmation` opt-in, environment-only enablement without opt-in, partial response when push succeeds and probe fails, and git-required guard when push did not run.

#### Scenario: HTTP live confirmation opt-in test

- **WHEN** tests call `POST /publish-blog-post` with `git_publication: true`, `live_site_confirmation: true`, and HTTP client fake returns 200 with slug marker
- **THEN** tests verify `blog_live_site_publication.status` `confirmed` in the response

#### Scenario: HTTP partial probe failure test

- **WHEN** tests call `POST /publish-blog-post` with live confirmation opt-in, push succeeds, and HTTP client fake always fails
- **THEN** tests verify response `status` is `partial` and push evidence is preserved

### Requirement: Processed source resolution for idempotent publish

The `already_published` short-circuit MUST use stored campaign identity and publish evidence (`state` `blog_published`, matching hash/idempotency key, and `source_public_url`) and MUST NOT require reading processed source files merely to prove an already-completed publish again.

When the short-circuit applies, `publish_blog_post()` MUST return `status: completed` with `blog_publish.status` `already_published` without calling `validate_ready_post_pre_generation()`, `validate_ready_post()`, `ensure_editorial_blog_image()`, `handoff_public_blog_image()`, `resolve_source_paths()`, GitHub Pages bridge planning/apply, or any public repository read/write performed only for a publish attempt.

When campaign metadata indicates `source_file_status.location` is `processed` and publish genuinely needs source files (non-short-circuited repair, reconciliation, or publish), `publish_blog_post` MUST resolve `blog-posts/processed/<source_slug>.{md,png}` from `processed_source_relative_path` (falling back to `source_relative_path` when processed path is absent on legacy campaigns) and MUST apply path confinement rules.

When `source_file_status.location` is `queued` or `execution_state` is `processing` or `stale`, `publish_blog_post` MUST resolve the source Markdown path from `queued_source_relative_path` (falling back to active `source_relative_path`).

Campaign lookup by `source_relative_path` MUST match `original_source_relative_path`, `queued_source_relative_path`, `processed_source_relative_path`, or active `source_relative_path`.

Idempotent publish for post-schedule campaigns MUST NOT fail with `blog_publish_source_not_ready` solely because the Markdown file is absent from `blog-posts/ready/`.

An already-published processed campaign MUST NOT fail solely because bridge source-pair resolution was attempted unnecessarily.

Active Flow A publish for queued campaigns MUST NOT fail with `blog_publish_source_not_ready` solely because the Markdown file is absent from `blog-posts/ready/` when `queued_source_relative_path` exists on disk.

`publish_blog_post` MUST continue to NOT perform physical source file moves; moves remain owned by `flow-a-operational-queue-lifecycle` and `flow-a-source-lifecycle-completion`.

#### Scenario: Already published processed campaign short-circuits before resolve_source_paths

- **WHEN** a Flow A campaign is `blog_published` with matching stored hash, idempotency key, and `source_public_url`, and sources exist only under `blog-posts/processed/`
- **THEN** `publish_blog_post` returns `status: completed` with `blog_publish.status` `already_published` without calling `resolve_source_paths()`, validation, editorial remediation, handoff, or public repo writes

#### Scenario: Missing processed Markdown or PNG does not invalidate already_published

- **WHEN** `publish_blog_post` is called for a campaign that satisfies `already_published` stored identity evidence and `blog-posts/processed/<source_slug>.md` or `blog-posts/processed/<source_slug>.png` is absent from disk
- **THEN** the operation returns `status: completed` with `blog_publish.status` `already_published` without requiring sources in `ready/` or `queued/` and without calling `resolve_source_paths()`

#### Scenario: Non-short-circuited processed repair resolves processed pair with confinement

- **WHEN** a non-short-circuited repair or publish attempt genuinely needs source files, `source_file_status.location` is `processed`, and `blog-posts/processed/<source_slug>.{md,png}` exists
- **THEN** `publish_blog_post` resolves both paths under `blog-posts/processed/` with path confinement and proceeds without requiring ready-folder copies

#### Scenario: Publish resolves queued source during active Flow A

- **WHEN** `publish_blog_post` is called for a campaign with `source_file_status.location` `queued` and Markdown only under `blog-posts/queued/`
- **THEN** publish proceeds without `blog_publish_source_not_ready` and does not require the file in `blog-posts/ready/`

#### Scenario: Campaign lookup by original ready path after move

- **WHEN** `publish_blog_post` is called with `source_relative_path` equal to a campaign's `original_source_relative_path` after lifecycle completion
- **THEN** the campaign is resolved and idempotent behavior applies without `blog_publish_source_not_ready`
### Requirement: Blog image public asset handoff integration reference

Blog publish MUST satisfy canonical spec `blog-image-public-asset-handoff` during the post-validation handoff step so Jekyll-canonical `assets/images/<public_slug>.png` exists before bridge apply without manual operator copying.

#### Scenario: Publish passes public repo path to handoff step

- **WHEN** `publish_blog_post` invokes `handoff_public_blog_image()` after full validation
- **THEN** the configured `SILVERMAN_GITHUB_PAGES_REPO_PATH` is available for public asset evaluation and copy
