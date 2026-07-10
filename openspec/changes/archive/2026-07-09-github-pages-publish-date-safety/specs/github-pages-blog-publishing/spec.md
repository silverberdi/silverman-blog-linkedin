## MODIFIED Requirements

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
