## 1. LinkedIn summary derivation helper

- [x] 1.1 Add `derive_flow_a_linkedin_completion_statuses(campaign)` to `editorial_calendar_plan.py` implementing package and distribution mapping rules from design.md (use `linkedin_package.package_status`, `linkedin_distribution.distribution_id`, top-level `campaign["variants"][]`)
- [x] 1.2 Export helper for use by the Flow A execution connector (module-level public function or documented import path consistent with project conventions)

## 2. Completion facts builder

- [x] 2.1 Update `_build_completion_facts_from_campaign` in `editorial_calendar_flow_a_execute.py` to call the shared derivation helper instead of reading `linkedin_package.status` / `linkedin_distribution.status`
- [x] 2.2 Verify post-execution calendar completion and reconciliation paths both inherit corrected summaries through the shared builder

## 3. Repair semantics for incomplete summaries (planner-level)

- [x] 3.1 Extend `_flow_a_completion_equivalent` / `complete_flow_a_calendar_item` conflict logic so null or missing LinkedIn summary fields on completed items allow repair when derived facts supply non-null values and other fields match
- [x] 3.2 Preserve `calendar_completion_facts_conflict` when stored non-null LinkedIn summary values differ from derived values
- [x] 3.3 Do **not** extend `find_due_items` — forward-only HTTP repair is limited to `scheduled`/`due` reconcile-close (per design decision 4)

## 4. Tests

- [x] 4.1 Add unit tests for `derive_flow_a_linkedin_completion_statuses` covering `package_status: generated`, `linkedin_distribution` with `distribution_id`, top-level `variants[]` with `scheduled_at_utc`/`publish_state`, and pre-package/pre-schedule campaigns
- [x] 4.2 Add executor test: `execute_due_editorial_calendar_flow_a` reconcile-close of a **`scheduled`** item against a `flow_a_complete` campaign with **realistic** metadata persists non-null `linkedin_package_status` and `linkedin_distribution_status` (replace fictional `linkedin_package.status` fixtures where touched)
- [x] 4.3 Add planner unit test: `complete_flow_a_calendar_item` repairs null LinkedIn summary fields on an already-`completed` item when derived facts supply non-null values and other fields match (planner contract only — documents repair semantics; not an HTTP end-to-end requirement)
- [x] 4.4 Add reconciliation test: completed item with **conflicting non-null** LinkedIn summaries still returns `calendar_completion_facts_conflict`
- [x] 4.5 Run targeted pytest: `tests/test_editorial_calendar_completion.py`, `tests/test_editorial_calendar_flow_a_execute.py`

## 5. Validation and product tracking

- [x] 5.1 Run `/opsx-verify` after implementation; fix any failures before commit approval
- [x] 5.2 Update `docs/CURRENT-STATE.md` if capability wording for calendar LinkedIn summary accuracy changes
- [x] 5.3 After demonstrated validation, update `docs/product/progress-checklist.md` and US-006/US-007/US-008 acceptance criteria for BL-003 only where outcomes are evidenced (forward completion + reconcile-close; legacy `completed` null rows may remain unless manually patched)

## Out of scope (do not implement in this change)

- Extending `find_due_items` to scan `completed` items for automatic HTTP repair
- `auto_queue_pending` / LinkedIn publication tooling
- n8n workflow changes
