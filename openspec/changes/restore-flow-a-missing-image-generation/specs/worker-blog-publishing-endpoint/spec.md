## MODIFIED Requirements

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
