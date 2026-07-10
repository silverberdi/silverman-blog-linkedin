## MODIFIED Requirements

### Requirement: Publish flow validation and image generation ordering

Ready-post validation MUST use canonical spec `ready-post-editorial-validation` via two phases inside `publish_blog_post()` for non-already-published campaigns.

`publish_blog_post()` MUST orchestrate the following strict order:

1. **Pre-generation gate** — `validate_ready_post_pre_generation()` validates deterministic requirements without blocking solely on missing/empty generatable frontmatter `image` or a generatable missing companion PNG.
2. **Editorial image remediation** — `ensure_editorial_blog_image()` (or staged equivalent with `handoff=False`) per `comfyui-blog-image-generation`, using the active `source_relative_path` folder (`ready/` or `queued/`); detect, generate/adopt/backfill locally; patch canonical frontmatter when authorized; **no public repo write**.
3. **Authorized hash reconciliation** — when editorial remediation patches frontmatter, recompute active `source_content_sha256`, persist on the same campaign, and recompute blog publish idempotency key per `flow-a-lifecycle`; metadata-write failure blocks publish without public repo writes.
4. **Full validation** — `validate_ready_post()` requires canonical `image` and companion PNG beside the active folder.
5. **Public asset handoff** — `handoff_public_blog_image()` (or staged equivalent) per `blog-image-public-asset-handoff`; runs only after full validation succeeds.
6. **GitHub Pages post publish** — existing publish bridge semantics.

If campaign metadata exists and `state` is `blog_published`, and `flow` is `flow_a`, and stored `source_content_sha256` matches the current source hash, and stored `blog_publish.idempotency_key` matches the expected key, and stored `source_public_url` exists, the publish flow MUST return `status: completed` with `blog_publish.status` `already_published` without calling validation, editorial remediation, handoff, or publish side effects and without writing public repo files.

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
