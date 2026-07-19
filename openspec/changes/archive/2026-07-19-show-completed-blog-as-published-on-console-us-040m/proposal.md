## Why

Completed Flow A blog calendar items already store `status: completed` with live `public_url` values, but `GET /flow-a/schedule-visibility` maps them to display `publication_state: planned` and appends a long title qualifier. Operators therefore read published blogs as still planned. This blocks trustworthy aesthetic closure of BL-015 console work before Flow B starts.

## What Changes

- Map editorial-calendar blog items with calendar `status: completed` to a distinct schedule-visibility display state that reads as **published on the blog** (not LinkedIn API published).
- Keep `linkedin_api_published: false` for all blog-channel items.
- Update console labels/filters/colors so operators see completed blogs clearly (e.g. “Published on blog”), without implying LinkedIn API publication.
- Soften or remove the redundant title suffix `(blog handoff completed — not LinkedIn API published)` once the display state/label carries that meaning.
- Add product story **US-040M** under BL-015 for this aesthetic/truthfulness fix.
- **No** calendar DB status mutation required for the current six completed blogs (already `completed`).
- **No** Flow B implementation in this change.
- **No** US-040L filters-modal work in this change (separate aesthetic follow-up).

## Goals

- Operators can distinguish unpublished/planned blogs from blogs that already completed handoff / site publication on the calendar.
- Preserve glossary discipline: blog published/completed ≠ LinkedIn API published.
- Smallest coherent worker + console delta under BL-015.

## Non-goals

- Flow B (BL-016–BL-019 / US-074–US-081).
- US-040L Search/Filters header modal.
- Changing Postgres calendar `status` values for already-completed items.
- Marking blog items as LinkedIn API published (`linkedin_api_published: true`).
- Changing LinkedIn variant display mapping.
- Public URL / Google OIDC activation.
- Closing BL-015 or marking US-040G–K Story accepted without their existing walkthrough gates.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-variant-supervision-console`: schedule-visibility blog display mapping and console presentation for completed blog calendar items MUST surface a completed/published-on-blog display state instead of `planned`, while keeping `linkedin_api_published` false for blog channel.

## Impact

- Worker: `src/silverman_blog_linkedin/flow_a_schedule_visibility.py` (`_map_blog_display_state`, title annotation).
- Tests: `tests/test_flow_a_schedule_visibility.py` (+ console Vitest label/filter coverage as needed).
- Frontend: `PublicationDisplayState` / labels / filters / status colors in `frontend/linkedin-variant-supervision-console/`.
- Product: BL-015 + US-040M in `docs/product/{backlog,user-stories,progress-checklist}.md`.
- Specs: delta under `linkedin-variant-supervision-console`.
- Live data: no required mutation; display fix alone corrects operator view for existing completed blogs.

## Related backlog / stories

- **BL-015** — Flow A LinkedIn Variant Supervision Console
- **US-040M** (new) — Show completed blogs as published-on-blog in schedule visibility
- Addresses operator feedback after live calendar inspection (2026-07-19): blogs already `completed` in DB but shown as `planned`
- Intentionally excluded: US-040L filters modal; Flow B; Visual DoD/walkthrough closure for G–K unless separately completed
