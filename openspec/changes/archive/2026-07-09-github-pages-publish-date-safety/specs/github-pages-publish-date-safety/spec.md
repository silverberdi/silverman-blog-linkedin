# github-pages-publish-date-safety

## Purpose

Jekyll publish date and permalink safety for immediate Flow A blog publication: ensure GitHub Pages includes posts at build time while preserving intended editorial/calendar public URL paths.

## ADDED Requirements

### Requirement: Publication timestamp versus intended URL date

The publishing bridge SHALL distinguish:

- **intended URL date**: editorial or calendar target date (`YYYY-MM-DD`) used for `_posts/` filename prefix, reported `public_url`, and optional `permalink` path segments
- **publication timestamp**: actual datetime written to Jekyll frontmatter `date` that MUST NOT be in the future relative to publish execution time for immediate publication

The bridge MUST resolve both values from source frontmatter `date` (or explicit CLI `--date` override) and an injectable `execution_time` (default: current UTC time).

#### Scenario: Resolver exposes both values

- **WHEN** the bridge prepares a post with intended URL date `2026-07-10` and execution time `2026-07-09T21:08:00-05:00`
- **THEN** resolution yields intended URL date `2026-07-10`, a publication timestamp at or before execution time, and `date_adjusted` true

#### Scenario: Safe editorial date needs no adjustment

- **WHEN** the bridge prepares a post with intended URL date `2026-07-06` and execution time `2026-07-06T15:00:00-05:00`
- **THEN** resolution yields `date_adjusted` false and publication timestamp aligned with the intended URL date at `00:00:00 -0500`

### Requirement: Jekyll future-post safety for immediate publication

For immediate publication (default bridge apply and Flow A publish), when the Jekyll datetime that would be written from the intended URL date is strictly after `execution_time`, the bridge MUST adjust the publication timestamp to `execution_time` (timezone-aware, formatted for Jekyll output) so GitHub Pages/Jekyll will include the post without enabling `future: true`.

The bridge MUST NOT modify public blog `_config.yml`.

#### Scenario: Future editorial date adjusted at evening publish

- **WHEN** immediate publish runs with intended URL date `2026-07-10`, execution time `2026-07-09T21:08:00-05:00`, and public slug `deferring-is-not-avoiding-it-can-be-architecture`
- **THEN** written frontmatter `date` reflects `2026-07-09 21:08:00 -0500` (or equivalent safe execution timestamp) and is not future-relative to execution time

#### Scenario: Already-safe date unchanged

- **WHEN** immediate publish runs with intended URL date `2026-07-06` and execution time `2026-07-06T12:00:00-05:00`
- **THEN** written frontmatter `date` remains `2026-07-06 00:00:00 -0500` and no date adjustment metadata is flagged

### Requirement: Permalink preserves intended URL when date is adjusted

When `date_adjusted` is true, the bridge MUST add frontmatter `permalink` set to `/YYYY/MM/DD/<public-slug>/` using the **intended URL date** and public slug.

When `date_adjusted` is false, the bridge MUST NOT add or modify `permalink` solely for date safety.

The reported `public_url` and `PublishPlan.public_url` MUST use the intended URL date path `https://<site>/YYYY/MM/DD/<public-slug>/`, not a path derived only from the adjusted publication timestamp.

#### Scenario: Permalink added for future editorial date

- **WHEN** immediate publish adjusts publication timestamp for intended URL date `2026-07-10` and public slug `deferring-is-not-avoiding-it-can-be-architecture`
- **THEN** published frontmatter includes `permalink: /2026/07/10/deferring-is-not-avoiding-it-can-be-architecture/` and reported `public_url` is `https://silverman.pro/2026/07/10/deferring-is-not-avoiding-it-can-be-architecture/`

#### Scenario: Safe date omits permalink

- **WHEN** immediate publish runs without date adjustment for intended URL date `2026-07-06` and public slug `example-post`
- **THEN** published frontmatter does not include a `permalink` field added by date safety logic

### Requirement: Coherent filename and frontmatter interaction

The bridge MUST name the output file `_posts/<intended-url-date>-<public-slug>.md` regardless of publication timestamp adjustment.

Frontmatter `date` MUST reflect the publication timestamp. Frontmatter `permalink` MUST reflect the intended URL path when adjustment occurs.

#### Scenario: Filename uses intended date while frontmatter date is adjusted

- **WHEN** immediate publish adjusts dates for intended URL date `2026-07-10` and public slug `deferring-is-not-avoiding-it-can-be-architecture`
- **THEN** the written file path is `_posts/2026-07-10-deferring-is-not-avoiding-it-can-be-architecture.md`, frontmatter `date` is the safe execution timestamp, and `permalink` preserves `/2026/07/10/deferring-is-not-avoiding-it-can-be-architecture/`

### Requirement: Explicit failure mode for future dates

The bridge MUST support an `on_future_date` parameter with values `adjust` (default) and `fail`.

When `on_future_date` is `fail` and the intended URL date is future-relative to execution time, the bridge MUST raise a structured error with stable code `blog_publish_future_date_requires_scheduled_execution` instead of adjusting dates.

Flow A immediate publish MUST use `adjust` mode.

#### Scenario: Fail mode rejects future editorial date

- **WHEN** publish resolution runs with `on_future_date` `fail`, intended URL date `2026-07-10`, and execution time `2026-07-09T21:08:00-05:00`
- **THEN** the bridge raises a publish error with code `blog_publish_future_date_requires_scheduled_execution` and does not write public repo files

### Requirement: Publish date safety tests

The repository SHALL include automated tests for publish date safety covering:

- future editorial date relative to execution time → safe `date` plus `permalink` preserving intended URL
- safe editorial date → no unnecessary `permalink`
- reported `public_url` matches intended slug/date path when adjusted
- `_posts/` filename and frontmatter interaction coherence
- no change to LinkedIn publication modules or endpoints

#### Scenario: Post 02 regression fixture

- **WHEN** tests run with source slug `02-deferring-is-not-avoiding-it-can-be-architecture`, intended date `2026-07-10`, and frozen execution time `2026-07-09T21:08:00-05:00`
- **THEN** tests verify safe frontmatter `date`, explicit `permalink`, intended `public_url`, and `_posts/2026-07-10-deferring-is-not-avoiding-it-can-be-architecture.md` filename
