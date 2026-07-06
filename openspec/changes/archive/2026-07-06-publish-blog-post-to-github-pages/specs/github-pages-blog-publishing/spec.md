## ADDED Requirements

### Requirement: Publishing helper CLI entry point

The repository SHALL provide an operator-invoked publishing helper that prepares one ready editorial blog post pair for the public GitHub Pages repository.

The helper MUST accept a source slug argument identifying the base name shared by `blog-posts/ready/<source-slug>.md` and `blog-posts/ready/<source-slug>.png`.

The helper MUST derive a public slug from the source slug for public filenames, image paths, frontmatter, and URLs. By default, when the source slug matches `^\d+-<rest>`, the helper MUST strip the leading numeric ordering prefix and hyphen; otherwise it MUST use the source slug unchanged. The operator MAY override the derived public slug with an explicit `--public-slug` flag.

Both source slug and public slug MUST match `^[a-z0-9]+(?:-[a-z0-9]+)*$` (lowercase alphanumeric segments separated by single hyphens; no leading/trailing hyphens, no path separators, no `..` segments).

The helper MUST default to dry-run mode and MUST NOT write files to the public blog repo checkout unless the operator passes an explicit apply flag (for example `--apply`).

The helper MUST print a structured summary including `source_slug`, `public_slug`, planned output paths, and the expected public URL.

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

The publishing helper SHALL generate the public blog post filename as `_posts/YYYY-MM-DD-<public-slug>.md`.

The publication date MUST default to the current UTC date unless the operator provides an explicit publication date (for example `--date YYYY-MM-DD`).

The provided publication date MUST be a valid calendar date in `YYYY-MM-DD` format.

#### Scenario: Default publication date

- **WHEN** the operator does not provide a publication date
- **THEN** the helper uses the current UTC date in the `_posts/` filename and frontmatter `date` field

#### Scenario: Explicit publication date

- **WHEN** the operator provides `--date 2026-07-06`
- **THEN** the helper generates `_posts/2026-07-06-<public-slug>.md` and sets frontmatter `date` accordingly

#### Scenario: Invalid publication date

- **WHEN** the operator provides a malformed publication date
- **THEN** the helper exits with a non-zero status without writing files

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

The `date` field MUST reflect the chosen publication date. The `image` field MUST reflect `/assets/images/<public-slug>.png`.

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

### Requirement: Public URL reporting

The publishing helper SHALL calculate and report the expected canonical public URL as:

`https://silverman.pro/YYYY/MM/DD/<public-slug>/`

where `YYYY`, `MM`, and `DD` are derived from the chosen publication date.

The helper MUST include this URL in dry-run and apply output summaries.

#### Scenario: Public URL for dated post

- **WHEN** the source slug is `01-architect-solution-state-of-art` and publication date is `2026-07-06`
- **THEN** the helper reports `https://silverman.pro/2026/07/06/architect-solution-state-of-art/`

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
- `_posts/YYYY-MM-DD-<public-slug>.md` filename generation
- `assets/images/<public-slug>.png` path convention
- frontmatter `image` path and required fields
- public URL calculation using `https://silverman.pro`
- non-overwrite refusal when targets exist
- dry-run producing no writes

#### Scenario: Filename transformation tests

- **WHEN** tests run with a known slug and publication date
- **THEN** tests verify the generated `_posts/` filename matches `YYYY-MM-DD-<public-slug>.md`

#### Scenario: Public URL tests

- **WHEN** tests run with slug `example-post` and date `2026-07-06`
- **THEN** tests verify the reported URL is `https://silverman.pro/2026/07/06/example-post/`

#### Scenario: Non-overwrite tests

- **WHEN** tests run apply mode against a checkout where the target post or image already exists
- **THEN** tests verify the helper exits with failure and does not replace existing files

#### Scenario: Dry-run tests

- **WHEN** tests run without apply mode
- **THEN** tests verify no files are created in the public blog repo checkout
