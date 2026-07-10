# github-pages-blog-publishing

## Purpose

Operator-invoked CLI publishing helper that prepares one ready editorial blog post pair (`<source-slug>.md` + `<source-slug>.png`) for the public Jekyll/GitHub Pages site at [silverman.pro](https://silverman.pro). The helper validates inputs, derives a public slug for published assets, normalizes frontmatter, defaults to dry-run, writes only with explicit `--apply`, and does not run git operations or expose an HTTP endpoint.

## Requirements

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
### Requirement: Publishing helper CLI entry point

The repository SHALL provide an operator-invoked publishing helper that prepares one ready editorial blog post pair for the public GitHub Pages repository.

The helper MUST accept a source slug argument identifying the base name shared by editorial Markdown and companion PNG files.

For the **operator CLI helper**, sources remain `blog-posts/ready/<source-slug>.md` and `blog-posts/ready/<source-slug>.png`.

For the **worker publish bridge** (`resolve_source_paths` or equivalent used by `blog_publish_flow`), resolution MUST derive folder from the supplied `source_relative_path` per worker publish source path resolution requirement.

The helper MUST derive a public slug from the source slug for public filenames, image paths, frontmatter, and URLs. By default, when the source slug matches `^\d+-<rest>`, the helper MUST strip the leading numeric ordering prefix and hyphen; otherwise it MUST use the source slug unchanged. The operator MAY override the derived public slug with an explicit `--public-slug` flag.

Both source slug and public slug MUST match `^[a-z0-9]+(?:-[a-z0-9]+)*$` (lowercase alphanumeric segments separated by single hyphens; no leading/trailing hyphens, no path separators, no `..` segments).

The helper MUST default to dry-run mode and MUST NOT write files to the public blog repo checkout unless the operator passes an explicit apply flag (for example `--apply`).

The helper MUST print a structured summary including `source_slug`, `public_slug`, planned output paths, and the expected public URL.

#### Scenario: CLI helper remains ready-only

- **WHEN** the operator CLI publishing helper is invoked with a source slug
- **THEN** it reads sources from `blog-posts/ready/<source-slug>.{md,png}` only

#### Scenario: Worker bridge uses active queued path

- **WHEN** `blog_publish_flow` publishes with `source_relative_path` `blog-posts/queued/01-example.md`
- **THEN** `resolve_source_paths` locates Markdown and PNG under `blog-posts/queued/` without requiring ready copies

#### Scenario: Dry-run by default

- **WHEN** the operator invokes the publishing helper with a valid slug and without an apply flag
- **THEN** the helper validates inputs, reports planned `_posts/` and `assets/images/` targets, reports the expected public URL, and does not create or modify files in the public blog repo checkout

#### Scenario: Apply mode writes outputs

- **WHEN** the operator invokes the publishing helper with a valid slug and an explicit apply flag
- **THEN** the helper writes the prepared Markdown post and copies the PNG image into the configured public blog repo checkout

#### Scenario: Missing slug argument

- **WHEN** the operator invokes the publishing helper without a slug argument
- **THEN** the helper exits with a non-zero status and prints usage guidance without modifying any files
### Requirement: Configuration for editorial and public blog paths

The publishing helper SHALL be configurable through environment variables and/or CLI flags for:

- editorial base path (defaulting to the configured worker editorial root, for example `/data/silverman-blog-linkedin` in container or `/home/silverman/compartido_mac/silverman-blog-linkedin` on the Ubuntu host)
- public blog repository checkout path (local clone of `silverberdi.github.io`)
- canonical public site base URL (default `https://silverman.pro`)

The helper MUST resolve all source and target paths relative to these configured roots and MUST NOT accept arbitrary absolute filesystem paths from the slug argument.

#### Scenario: Default canonical URL

- **WHEN** the operator does not override the site base URL
- **THEN** the helper calculates public URLs using `https://silverman.pro`

#### Scenario: Configured public blog checkout

- **WHEN** the operator provides a valid public blog repo checkout path
- **THEN** the helper writes outputs only under that checkout's `_posts/` and `assets/images/` directories when apply mode is used
### Requirement: Source pair validation

Before preparing outputs, the publishing helper SHALL validate:

- `blog-posts/ready/<source-slug>.md` exists and is a readable regular file
- `blog-posts/ready/<source-slug>.png` exists and is a readable regular file
- `<source-slug>` is safe for URL and filesystem use
- the resolved `<public-slug>` is safe for URL and filesystem use

A slug MUST match `^[a-z0-9]+(?:-[a-z0-9]+)*$` (lowercase alphanumeric segments separated by single hyphens; no leading/trailing hyphens, no path separators, no `..` segments).

#### Scenario: Valid source pair

- **WHEN** the source slug is safe and both matching `.md` and `.png` files exist under `blog-posts/ready/`
- **THEN** the helper proceeds to prepare publication outputs using the derived or overridden public slug

#### Scenario: Numeric ordering prefix stripped from public slug

- **WHEN** the source slug is `01-why-i-did-not-start-with-the-database` and the operator does not pass `--public-slug`
- **THEN** the helper reads sources from `blog-posts/ready/01-why-i-did-not-start-with-the-database.{md,png}` and uses public slug `why-i-did-not-start-with-the-database` for `_posts/`, `assets/images/`, frontmatter `image`, and the reported public URL

#### Scenario: Explicit public slug override

- **WHEN** the operator passes `--public-slug custom-public-slug` with a safe slug value
- **THEN** the helper still reads editorial sources by source slug but uses `custom-public-slug` for public filenames, image paths, frontmatter `image`, and the reported public URL

#### Scenario: Missing Markdown source

- **WHEN** `blog-posts/ready/<source-slug>.md` does not exist
- **THEN** the helper exits with a non-zero status, reports the missing Markdown file, and does not write to the public blog repo checkout

#### Scenario: Missing PNG source

- **WHEN** `blog-posts/ready/<source-slug>.md` exists but `blog-posts/ready/<source-slug>.png` does not
- **THEN** the helper exits with a non-zero status, reports the missing PNG file, and does not write to the public blog repo checkout

#### Scenario: Unsafe source slug rejected

- **WHEN** the source slug contains uppercase letters, path separators, `..`, or other unsafe characters
- **THEN** the helper exits with a non-zero status and does not access paths outside the editorial ready folder

#### Scenario: Unsafe public slug override rejected

- **WHEN** the operator passes an unsafe `--public-slug` value
- **THEN** the helper exits with a non-zero status and does not write to the public blog repo checkout
### Requirement: Jekyll post filename and publication date

The publishing helper SHALL generate the public blog post filename as `_posts/YYYY-MM-DD-<public-slug>.md` where `YYYY-MM-DD` is the **intended URL date** from source frontmatter or explicit override.

The publishing helper MUST resolve publish dates via canonical `github-pages-publish-date-safety` semantics, distinguishing intended URL date from publication timestamp.

When no explicit publication date is provided, the intended URL date MUST default to the current UTC calendar date unless source frontmatter supplies a parseable `date`.

The provided intended URL date MUST be a valid calendar date in `YYYY-MM-DD` format.

For immediate publication, when the Jekyll datetime for the intended URL date would be future-relative to execution time, the helper MUST adjust the publication timestamp per `github-pages-publish-date-safety` while keeping the `_posts/` filename prefix on the intended URL date.

#### Scenario: Default publication date

- **WHEN** the operator does not provide a publication date and source frontmatter has no `date`
- **THEN** the helper uses the current UTC calendar date as the intended URL date in the `_posts/` filename and frontmatter `date` field

#### Scenario: Explicit publication date

- **WHEN** the operator provides `--date 2026-07-06`
- **THEN** the helper generates `_posts/2026-07-06-<public-slug>.md` and sets frontmatter `date` accordingly when safe at execution time

#### Scenario: Invalid publication date

- **WHEN** the operator provides a malformed publication date
- **THEN** the helper exits with a non-zero status without writing files

#### Scenario: Future intended date filename unchanged

- **WHEN** immediate publish runs with intended URL date `2026-07-10`, execution time before that Jekyll datetime, and public slug `example-post`
- **THEN** the planned filename remains `_posts/2026-07-10-example-post.md` while frontmatter `date` uses the safe publication timestamp
### Requirement: Image copy convention

The publishing helper SHALL copy the source PNG to `assets/images/<public-slug>.png` in the public blog repo checkout when apply mode is used.

The helper MUST set frontmatter `image` to `/assets/images/<public-slug>.png` (site-root-relative path).

#### Scenario: Image target path

- **WHEN** the helper prepares outputs for source slug `01-architect-solution-state-of-art`
- **THEN** the planned image destination is `assets/images/architect-solution-state-of-art.png` and frontmatter `image` is `/assets/images/architect-solution-state-of-art.png`
### Requirement: Frontmatter normalization

The publishing helper SHALL read the source Markdown file, preserve the post body content after frontmatter, and write or normalize YAML frontmatter for Jekyll.

Published frontmatter MUST include at minimum: `layout`, `title`, `date`, `categories`, `tags`, `description`, and `image`.

Published frontmatter MUST NOT include editorial-only fields such as `status`. The helper MUST remove `status` from published output regardless of source value (for example `draft`).

If the source Markdown already contains frontmatter, the helper MUST merge/normalize required fields without discarding the body.

If `description` is missing, null, or an empty string and source frontmatter has a non-empty `subtitle`, the helper MUST use `subtitle` as `description`. The helper MUST NOT invent descriptions beyond this fallback or from post body content.

If `title` is absent in source frontmatter, the helper MAY derive a title from the public slug. The helper MUST NOT invent unsupported editorial claims.

`categories` and `tags` MUST be preserved when present in source frontmatter and MUST default to empty lists when absent. The helper MUST NOT fabricate categories or tags.

The `date` field MUST reflect the **publication timestamp** from publish date resolution. The `image` field MUST reflect `/assets/images/<public-slug>.png`.

When publish date resolution sets `date_adjusted` true, published frontmatter MUST include `permalink` `/YYYY/MM/DD/<public-slug>/` using the intended URL date. When `date_adjusted` is false, the helper MUST NOT add `permalink` solely for date safety.

#### Scenario: Body content preserved

- **WHEN** the source Markdown contains a body after frontmatter
- **THEN** the published Markdown contains the same body content (aside from normalized line endings if applicable)

#### Scenario: Required frontmatter fields present

- **WHEN** the helper writes a published Markdown file
- **THEN** the frontmatter includes `layout`, `title`, `date`, `categories`, `tags`, `description`, and `image`

#### Scenario: Editorial status removed

- **WHEN** the source frontmatter includes `status: draft`
- **THEN** the published frontmatter does not include a `status` field

#### Scenario: Description falls back to subtitle

- **WHEN** the source frontmatter has no `description` (or it is empty) and a non-empty `subtitle`
- **THEN** the published frontmatter `description` is set to the subtitle value

#### Scenario: No invented description

- **WHEN** the source frontmatter has no `description`, no `subtitle`, and a non-empty body
- **THEN** the published frontmatter `description` is an empty string and the helper does not derive description from body content

#### Scenario: Permalink added when date adjusted

- **WHEN** publish date resolution adjusts the publication timestamp for intended URL date `2026-07-10`
- **THEN** published frontmatter includes `permalink` preserving `/2026/07/10/<public-slug>/`
### Requirement: Public URL reporting

The publishing helper SHALL calculate and report the expected canonical public URL as:

`https://silverman.pro/YYYY/MM/DD/<public-slug>/`

where `YYYY`, `MM`, and `DD` are derived from the **intended URL date**, not from the adjusted publication timestamp when they differ.

The helper MUST include this URL in dry-run and apply output summaries.

When date adjustment occurs, summaries SHOULD include `date_adjusted` and publication timestamp metadata for operator visibility.

#### Scenario: Public URL for dated post

- **WHEN** the source slug is `01-architect-solution-state-of-art` and intended URL date is `2026-07-06`
- **THEN** the helper reports `https://silverman.pro/2026/07/06/architect-solution-state-of-art/`

#### Scenario: Public URL uses intended path when date adjusted

- **WHEN** immediate publish adjusts publication timestamp for intended URL date `2026-07-10` and public slug `deferring-is-not-avoiding-it-can-be-architecture`
- **THEN** the helper reports `https://silverman.pro/2026/07/10/deferring-is-not-avoiding-it-can-be-architecture/`
### Requirement: Safe non-overwrite behavior

The publishing helper MUST NOT overwrite an existing `_posts/YYYY-MM-DD-<public-slug>.md` file or an existing `assets/images/<public-slug>.png` file in the public blog repo checkout.

If either target already exists, the helper MUST exit with a non-zero status and report which path would have been overwritten.

#### Scenario: Existing post file blocks publish

- **WHEN** `_posts/YYYY-MM-DD-<public-slug>.md` already exists in the public blog repo checkout
- **THEN** the helper refuses to write and exits with a non-zero status even when apply mode is requested

#### Scenario: Existing image file blocks publish

- **WHEN** `assets/images/<public-slug>.png` already exists in the public blog repo checkout
- **THEN** the helper refuses to write and exits with a non-zero status even when apply mode is requested

#### Scenario: Dry-run reports overwrite conflict

- **WHEN** the helper runs in dry-run mode and a target file already exists
- **THEN** the helper reports the conflict and exits with a non-zero status without writing files
### Requirement: Source files remain in ready

The publishing helper MUST NOT move, delete, rename, or modify files in `blog-posts/ready/`, `blog-posts/processed/`, or `blog-posts/error/`.

#### Scenario: Ready sources unchanged after apply

- **WHEN** the operator runs the helper in apply mode with a valid source slug
- **THEN** the original `blog-posts/ready/<source-slug>.md` and `blog-posts/ready/<source-slug>.png` remain in place and unchanged
### Requirement: No automatic git operations

The publishing helper MUST NOT run `git commit`, `git push`, or other remote publishing commands.

#### Scenario: Apply leaves git dirty

- **WHEN** the operator runs the helper in apply mode successfully
- **THEN** new or modified files exist only in the local public blog repo checkout and the operator is responsible for commit and push
### Requirement: Publishing helper tests

The repository SHALL include automated tests for the publishing helper covering:

- source slug and public slug validation (safe vs unsafe; numeric prefix stripping; override)
- `_posts/YYYY-MM-DD-<public-slug>.md` filename generation using intended URL date
- `assets/images/<public-slug>.png` path convention
- frontmatter `image` path and required fields
- public URL calculation using `https://silverman.pro`
- publish date safety: future editorial date adjustment, permalink preservation, safe-date no-op
- non-overwrite refusal when targets exist
- dry-run producing no writes

#### Scenario: Filename transformation tests

- **WHEN** tests run with a known slug and intended URL date
- **THEN** tests verify the generated `_posts/` filename matches `YYYY-MM-DD-<public-slug>.md` using the intended URL date

#### Scenario: Public URL tests

- **WHEN** tests run with slug `example-post` and intended URL date `2026-07-06`
- **THEN** tests verify the reported URL is `https://silverman.pro/2026/07/06/example-post/`

#### Scenario: Future date safety tests

- **WHEN** tests run with a future intended URL date relative to frozen execution time
- **THEN** tests verify safe frontmatter `date`, explicit `permalink`, and intended `public_url`

#### Scenario: Non-overwrite tests

- **WHEN** tests run apply mode against a checkout where the target post or image already exists
- **THEN** tests verify the helper exits with failure and does not replace existing files

#### Scenario: Dry-run tests

- **WHEN** tests run without apply mode
- **THEN** tests verify no files are created in the public blog repo checkout
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
