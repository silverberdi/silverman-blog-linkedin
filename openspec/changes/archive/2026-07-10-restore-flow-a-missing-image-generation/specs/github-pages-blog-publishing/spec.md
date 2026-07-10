## ADDED Requirements

### Requirement: Worker publish source path resolution

For worker `publish_blog_post` integration (distinct from the operator CLI helper), source path resolution MUST accept an active `source_relative_path` under:

- `blog-posts/ready/<source_slug>.md` with companion `blog-posts/ready/<source_slug>.png`
- `blog-posts/queued/<source_slug>.md` with companion `blog-posts/queued/<source_slug>.png`
- `blog-posts/processed/<source_slug>.md` with companion `blog-posts/processed/<source_slug>.png` for idempotent reruns

Resolution MUST enforce path confinement under the editorial base and MUST reject unsupported folders.

The worker publish bridge MUST NOT require a duplicate copy in `blog-posts/ready/` once queue acceptance has moved the source to `blog-posts/queued/`.

#### Scenario: Queued source resolves Markdown and generated PNG

- **WHEN** publish planning resolves sources for `blog-posts/queued/01-example.md` and `blog-posts/queued/01-example.png` exists
- **THEN** both paths are returned for publish bridge use without requiring ready-folder copies

#### Scenario: Processed source resolves for idempotent rerun

- **WHEN** publish is retried with `source_relative_path` under `blog-posts/processed/` and matching PNG exists
- **THEN** resolution succeeds for idempotent skip or repair paths

#### Scenario: Unsupported folder rejected

- **WHEN** `source_relative_path` is outside `blog-posts/ready/`, `blog-posts/queued/`, or `blog-posts/processed/`
- **THEN** resolution fails with a stable path error and does not access paths outside confinement

## MODIFIED Requirements

### Requirement: Source slug input validation

The publishing helper MUST accept a source slug argument identifying the base name shared by editorial Markdown and companion PNG files.

For the **operator CLI helper**, sources remain `blog-posts/ready/<source-slug>.md` and `blog-posts/ready/<source-slug>.png`.

For the **worker publish bridge** (`resolve_source_paths` or equivalent used by `blog_publish_flow`), resolution MUST derive folder from the supplied `source_relative_path` per worker publish source path resolution requirement.

#### Scenario: CLI helper remains ready-only

- **WHEN** the operator CLI publishing helper is invoked with a source slug
- **THEN** it reads sources from `blog-posts/ready/<source-slug>.{md,png}` only

#### Scenario: Worker bridge uses active queued path

- **WHEN** `blog_publish_flow` publishes with `source_relative_path` `blog-posts/queued/01-example.md`
- **THEN** `resolve_source_paths` locates Markdown and PNG under `blog-posts/queued/` without requiring ready copies

### Requirement: Processed source resolution defers to publish idempotency short-circuit

For worker `publish_blog_post` integration, the `already_published` metadata/idempotency short-circuit defined by `worker-blog-publishing-endpoint` MUST be evaluated before:

- pre-generation validation;
- full validation;
- editorial image remediation;
- public asset handoff;
- `resolve_source_paths()` (or equivalent bridge source-pair resolution);
- GitHub Pages bridge planning/apply;
- any public repository read/write performed only for a publish attempt.

When the short-circuit applies for a Flow A campaign with matching stored identity evidence, `publish_blog_post()` MUST return `status: completed` with `blog_publish.status` `already_published`, MUST NOT require Markdown or PNG to be resolvable from `ready/`, `queued/`, or `processed/`, MUST NOT invoke `resolve_source_paths()`, and MUST NOT overwrite public files.

When the short-circuit applies, `resolve_source_paths` (or equivalent bridge source-pair resolution) MUST NOT be invoked and MUST NOT cause failure.

Processed Markdown/PNG source resolution under `blog-posts/processed/<source_slug>.{md,png}` is required only when a non-short-circuited repair, reconciliation, or publish operation genuinely needs the editorial pair on disk. Resolution MUST enforce path confinement under the editorial base.

An already-published processed campaign MUST NOT fail solely because bridge source-pair resolution was attempted unnecessarily, because processed sources are absent from disk, or because Markdown is absent from `blog-posts/ready/`.

The short-circuit MUST use stored campaign identity and publish evidence and MUST NOT require reading processed source files merely to prove an already-completed publish again.

#### Scenario: Already published processed campaign short-circuits before resolve_source_paths

- **WHEN** `publish_blog_post` is called for a Flow A campaign that satisfies `already_published` stored identity evidence with `source_file_status.location` `processed`
- **THEN** `resolve_source_paths` is not invoked, `status` is `completed`, and `blog_publish.status` is `already_published`

#### Scenario: Missing processed Markdown or PNG does not invalidate already_published

- **WHEN** `publish_blog_post` is called for a campaign that satisfies `already_published` checks and `blog-posts/processed/<source_slug>.md` or `.png` is absent from disk
- **THEN** the operation returns `status: completed` with `blog_publish.status` `already_published` without invoking `resolve_source_paths()` or failing with `blog_publish_source_not_ready`

#### Scenario: Non-short-circuited processed repair resolves processed pair with confinement

- **WHEN** a non-short-circuited repair or publish operation requires source files, `source_relative_path` is under `blog-posts/processed/`, and matching Markdown and PNG exist
- **THEN** `resolve_source_paths` returns both paths under `blog-posts/processed/` with path confinement and without requiring ready-folder copies
