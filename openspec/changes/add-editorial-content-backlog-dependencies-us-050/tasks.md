## 1. Store model — dependencies and queue rank

- [x] 1.1 Extend `editorial_content_backlog_items` schema ensure (Postgres + `memory://`) with `depends_on_item_ids` (JSONB/list, default `[]`) and `queue_rank` (non-negative int, default on create)
- [x] 1.2 Backfill / default existing rows: empty dependency lists; assign contiguous `queue_rank` values for current items
- [x] 1.3 Extend store create/get/list/update to read/write the new fields; list sort = `queue_rank ASC`, then priority band (`high` < `medium` < `low`), then `updated_at_utc DESC`

## 2. Validation and domain helpers

- [x] 2.1 Validate `depends_on_item_ids`: bounded length, distinct ids, no self-ref, all ids exist; reject dangling refs with structured 4xx
- [x] 2.2 Reject dependency writes that introduce a cycle (`dependency_cycle` or equivalent stable code + actionable message); no partial persist
- [x] 2.3 Validate `queue_rank` as non-negative integer; keep existing `priority` enum validation; assign default rank on create when omitted
- [x] 2.4 Include `depends_on_item_ids` and `queue_rank` in secret-safe response snapshots

## 3. Authenticated HTTP API

- [x] 3.1 Extend `POST`/`PUT`/`GET` `/editorial/content-backlog` request/response contracts for dependencies and queue rank (ADR-0001; auth required)
- [x] 3.2 Optionally add authenticated `PUT /editorial/content-backlog/reorder` that reassigns contiguous ranks from `ordered_item_ids` (4xx on unknown ids); skip only if per-item `queue_rank` PUT fully covers AC
- [x] 3.3 Ensure create/update/reorder MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or write `linkedin-posts/` packages

## 4. Authority Manager Content backlog UI

- [x] 4.1 Extend API client/types for `depends_on_item_ids`, `queue_rank`, and reorder (if shipped)
- [x] 4.2 Extend `ContentBacklogModal`: show dependencies (resolve ids → topic labels), edit dependency selection, change priority, move earlier/later (or equivalent)
- [x] 4.3 Surface plain-language errors for cycle, dangling dependency, validation, and auth failures; keep optional-enrichment copy (save ≠ Flow B / LinkedIn publish)
- [x] 4.4 Rebuild console static assets into the worker console path after UI changes

## 5. Tests

- [x] 5.1 Pytest: dependency round-trip; empty deps valid; dangling / self / cycle rejected; priority + queue_rank update; list order contract; reorder if shipped; auth + secret-free responses
- [x] 5.2 Pytest: Flow B independence regression — discovery / gap-trigger modules do not require backlog deps/ranks; empty backlog still non-blocking
- [x] 5.3 Vitest: Content backlog dependency edit + prioritize/reprioritize + failure messaging
- [x] 5.4 Run targeted pytest + Vitest; fix warnings attributable to this change; `git diff --check` clean on touched paths

## 6. Docs and business progress (demonstrated criteria only)

- [x] 6.1 Update `docs/CURRENT-STATE.md` for US-050 dependency + prioritization capability (local vs deployed; not Story accepted; BL-020 still open)
- [x] 6.2 Update `docs/product/user-stories.md` US-050 AC checkboxes only for criteria demonstrated by tests/UI; do **not** mark Story accepted
- [x] 6.3 Update `docs/product/progress-checklist.md` BL-020 / US-050 progress (work started / demonstrated as accurate); do **not** close BL-020
- [x] 6.4 Glossary touch only if new operator-facing terms need a one-line definition (optional; skip if unnecessary)

## 7. Business validation gate

- [x] 7.1 Confirm US-050 AC mapping: identify dependencies; prioritize/reprioritize; MUST NOT block P4 Flow B; visible to operator; clear failures; no unintentional Flow A/B regression
- [x] 7.2 Confirm out-of-scope held: no discovery seed required wiring; no auto-publish/packaging; no Story accepted / BL-020 closed / deploy / push without explicit operator approval
