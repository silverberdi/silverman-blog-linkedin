## ADDED Requirements

### Requirement: Completed blog calendar items display as published-on-blog

Authenticated `GET /flow-a/schedule-visibility` MUST map editorial-calendar blog items whose calendar `status` is `completed` to display `publication_state` **`completed`** (not `planned`).

For those blog-channel items the worker MUST:

- set `linkedin_api_published` to **`false`**
- set `source_state` to the calendar status (`completed`)
- preserve schedule non-editability for completed calendar status
- MUST NOT append the legacy title suffix `(blog handoff completed — not LinkedIn API published)` to `title`

The console MUST present `publication_state: completed` with an operator-facing label equivalent to **“Published on blog”**, distinct from LinkedIn `published` (“Published (API evidence)”).

The console MUST include `completed` in publication-state filters and status coloring without treating it as LinkedIn API published.

This requirement MUST NOT mark blog items as LinkedIn API published, MUST NOT mutate calendar Postgres status as part of the display fix, and MUST NOT implement Flow B or US-040L.

#### Scenario: Completed blog maps to completed display state

- **WHEN** schedule-visibility includes an editorial-calendar blog item with calendar `status: completed`
- **THEN** the item’s `channel` is `blog`, `publication_state` is `completed`, `linkedin_api_published` is `false`, and `title` does not include the legacy handoff suffix

#### Scenario: Planned blog remains planned

- **WHEN** schedule-visibility includes an editorial-calendar blog item with calendar status in the planned-like set (`planned`, `scheduled`, `due`, `in_progress`, or equivalent non-terminal states used today)
- **THEN** the item’s `publication_state` remains `planned` (or the existing non-completed mapping) and is not labeled “Published on blog”

#### Scenario: Console label distinguishes blog completed from LinkedIn published

- **WHEN** the console renders a blog item with `publication_state: completed` and a LinkedIn item with `publication_state: published`
- **THEN** the blog item shows a “Published on blog” (or equivalent) label and the LinkedIn item continues to show the LinkedIn API evidence published label; the blog item MUST NOT claim LinkedIn API published

#### Scenario: Completed blogs remain filterable and non-editable

- **WHEN** an operator filters by the completed / published-on-blog publication state
- **THEN** completed blog items are included by that filter and remain schedule-read-only (not schedule-editable)

#### Scenario: Scope excludes Flow B and filters-modal redesign

- **WHEN** this capability is implemented
- **THEN** Flow B (BL-016+) and US-040L Search/Filters header modal remain out of scope, and no calendar status backfill is required for items already `completed` in the store
