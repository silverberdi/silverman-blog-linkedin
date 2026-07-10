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
