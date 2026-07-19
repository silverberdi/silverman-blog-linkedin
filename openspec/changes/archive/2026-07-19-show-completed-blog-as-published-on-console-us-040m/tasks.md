## 1. Product story alignment

- [x] 1.1 Add US-040M to `docs/product/user-stories.md` with acceptance criteria matching this change
- [x] 1.2 Update BL-015 expected outcomes / completion language in `docs/product/backlog.md` for completed-blog display honesty
- [x] 1.3 Add US-040M checklist entry under BL-015 in `docs/product/progress-checklist.md` (AC agreed; work not started until apply)

## 2. Worker schedule-visibility mapping

- [x] 2.1 Add display constant `completed` and map calendar blog `status: completed` → `publication_state: completed` in `flow_a_schedule_visibility.py`
- [x] 2.2 Keep `linkedin_api_published: false` for blog channel; remove legacy title suffix for completed blogs
- [x] 2.3 Update `tests/test_flow_a_schedule_visibility.py` for completed vs planned blog mapping

## 3. Console presentation

- [x] 3.1 Extend `PublicationDisplayState` / labels / filters / colors with `completed` → “Published on blog”
- [x] 3.2 Ensure Upcoming/Pending (and similar) metric helpers do not treat blog `completed` as upcoming work
- [x] 3.3 Add/adjust Vitest coverage for label + filter behavior; keep LinkedIn `published` label unchanged
- [x] 3.4 Rebuild static console assets into worker static path

## 4. Docs and verification

- [x] 4.1 Update `docs/CURRENT-STATE.md` for the display-mapping behavior (no false claim of Story accepted)
- [x] 4.2 Run targeted pytest + Vitest for touched modules; `git diff --check`
- [ ] 4.3 After deploy approval: smoke July schedule-visibility shows completed blogs as `publication_state: completed` with `linkedin_api_published: false`

## 5. Business validation

- [ ] 5.1 Confirm US-040M acceptance criteria against deployed/smoke evidence; update progress checklist only for demonstrated outcomes
- [ ] 5.2 Leave US-040L and Flow B untouched; do not close BL-015 or mark G–K Story accepted as a side effect
