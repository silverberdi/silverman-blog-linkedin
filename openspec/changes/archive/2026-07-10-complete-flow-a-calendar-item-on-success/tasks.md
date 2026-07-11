## 1. Calendar persistence and schema

- [x] 1.1 Add stable error codes: `calendar_item_not_found`, `calendar_completion_write_failed`, `calendar_completion_concurrent_update`, `calendar_completion_campaign_unresolved`, `calendar_completion_facts_conflict`
- [x] 1.2 Extend `load_calendar` validation for optional `completed_at_utc`, `processed_source_relative_path`, and `flow_a_completion` object (minimum keys: `campaign_state`, `execution_status`, `source_lifecycle_status`, `blog_publish_status`, `public_url`, `linkedin_package_status`, `linkedin_distribution_status`; no duplication of parent canonical fields)
- [x] 1.3 Implement `save_calendar_atomic(base_path, calendar, *, expected_fingerprint=None)` with validate-then-temp-write-then-fingerprint-check-then-replace semantics and `updated_at_utc` refresh
- [x] 1.4 Implement `complete_flow_a_calendar_item(calendar, *, item_id, completion_facts)` preserving audit fields, `notes` byte-for-byte, unrelated items, equivalent-completed no-op indicator, and `calendar_completion_facts_conflict` on conflicting terminal facts
- [x] 1.5 Update `docs/examples/editorial-calendar/calendar.example.json` with one completed-item example showing canonical completion fields and `flow_a_completion` summary evidence without duplicated parent fields

## 2. Flow A connector integration

- [x] 2.1 Extend `EditorialCalendarFlowAItemResult` with `calendar_update_status` and calendar-related errors
- [x] 2.2 Implement reconciliation ordering: for each due Flow A item, resolve campaign by authoritative `campaign_id` (legacy normalized ready `source_relative_path` fallback only when `campaign_id` absent) before missing-source rejection
- [x] 2.3 Implement authoritative `campaign_id` reconciliation: load exact campaign, verify `flow_a_complete` + processed lifecycle evidence + identity consistency, reconcile without Flow A side effects
- [x] 2.4 Implement legacy source-path fallback: search only `flow_a_complete` campaigns, require exactly one match, return `calendar_completion_campaign_unresolved` on zero or multiple matches, never choose first match
- [x] 2.5 After successful `complete_flow_a_source_lifecycle` with campaign `flow_a_complete`, build completion facts from publish/package/schedule/lifecycle results and persist calendar item only when mutation indicator requires write
- [x] 2.6 Ensure calendar completion does not run on publish/package/schedule/lifecycle failure paths
- [x] 2.7 Handle calendar persistence failure: item `calendar_update_status=failed`, top-level `partial`, error `calendar_completion_write_failed`, no publication rollback, calendar-only retry path
- [x] 2.8 Handle missing calendar item during completion (`calendar_item_not_found`) deterministically
- [x] 2.9 Handle conflicting terminal completion facts (`calendar_completion_facts_conflict`) without silent overwrite
- [x] 2.10 Ensure reconciliation and idempotent no-op paths do not call ComfyUI, handoff, publish, package, schedule, lifecycle, or increment attempt count
- [x] 2.11 Never mutate `notes` on completion or reconciliation
- [x] 2.12 Set top-level `read_only=false` only when real execution performs calendar write; dry-run remains read-only

## 3. Tests — calendar persistence

- [x] 3.1 Test successful atomic save updates `updated_at_utc` and preserves unrelated items
- [x] 3.2 Test atomic write failure leaves original valid `calendar.json` intact
- [x] 3.3 Test `complete_flow_a_calendar_item` preserves original `source_relative_path`, sets canonical completion fields, and leaves `notes` unchanged
- [x] 3.4 Test duplicate `item_id` rejection remains enforced by `load_calendar`
- [x] 3.5 Test completed item with optional fields loads successfully; invalid `completed_at_utc` rejected
- [x] 3.6 Test already equivalent completed item produces no persistable mutation from `complete_flow_a_calendar_item`
- [x] 3.7 Test conflicting terminal completion facts return `calendar_completion_facts_conflict`
- [x] 3.8 Test concurrent calendar modification is not overwritten; unrelated item remains intact; `calendar_completion_concurrent_update` returned; temp file cleaned up
- [x] 3.9 Test atomic save succeeds when fingerprint unchanged

## 4. Tests — executor and planner integration

- [x] 4.1 Test successful Flow A execution changes matching calendar item to `status=completed` with `notes` unchanged
- [x] 4.2 Test completed item is no longer due in `plan_editorial_calendar_due` results
- [x] 4.3 Test completed item is excluded before source existence validation and does not yield `calendar_source_not_found`
- [x] 4.4 Test unrelated calendar items remain structurally unchanged after completion
- [x] 4.5 Test completion records correct `campaign_id`, `processed_source_relative_path`, and `public_url` in `flow_a_completion` when available
- [x] 4.6 Test calendar completion occurs only after lifecycle success and campaign `flow_a_complete` (not after schedule-only success)
- [x] 4.7 Test failure before lifecycle completion does not falsely complete calendar item
- [x] 4.8 Test schedule-success-but-lifecycle-failure leaves calendar item schedulable (not `completed`)
- [x] 4.9 Test calendar persistence failure after successful Flow A returns `partial` with `calendar_completion_write_failed`; retry reconciles calendar only without republication
- [x] 4.10 Test reconciliation by exact `campaign_id` when original ready source no longer exists
- [x] 4.11 Test reconciliation occurs before missing-source rejection for stale `flow_a_complete` campaign
- [x] 4.12 Test stale completed campaign does not emit `calendar_source_not_found`
- [x] 4.13 Test historical item without `campaign_id` reconciles only through one unique completed-campaign source match
- [x] 4.14 Test zero fallback matches produces `calendar_completion_campaign_unresolved` with no calendar mutation
- [x] 4.15 Test multiple fallback matches produces `calendar_completion_campaign_unresolved` with no calendar mutation and no first-match selection
- [x] 4.16 Test source-path fallback never chooses the first match when multiple candidates exist
- [x] 4.17 Test `notes` remains unchanged on reconciliation
- [x] 4.18 Test already equivalent completed item produces no `calendar.json` write; `completed_at_utc` stable across repeated reconciliation
- [x] 4.19 Test conflicting terminal completion facts produce `calendar_completion_facts_conflict`
- [x] 4.20 Test genuine scheduled missing-source item without completed campaign still yields existing missing-source diagnostic
- [x] 4.21 Test reconciliation does not call ComfyUI, handoff, publish, package, scheduling, lifecycle, or increment attempt count
- [x] 4.22 Test existing `/publish-blog-post` processed-source idempotency tests still pass (regression)
- [x] 4.23 Test existing `tests/test_editorial_calendar_flow_a_execute.py` suite still passes with updated calendar-write and reconciliation expectations
- [x] 4.24 Test Flow A success with concurrent calendar update returns `partial` and `calendar_completion_concurrent_update` without rolling back publication
- [x] 4.25 Test retry after concurrent calendar conflict reconciles calendar only without republication
- [x] 4.26 Test filesystem-level equivalent-completed executor path performs no `save_calendar_atomic` and preserves bytes, mtime, `completed_at_utc`, and `notes`

## 5. Documentation

- [x] 5.1 Update `docs/workflows/editorial-calendar-flow-a-execution-connector.md`: calendar completion boundary, authoritative `campaign_id` reconciliation, legacy fallback limits, reconciliation ordering, `notes` immutability, persistence-failure recovery
- [x] 5.2 Update `docs/workflows/editorial-calendar-orchestration.md` (minimum): terminal `completed` exclusion before source validation

## 6. Validation

- [x] 6.1 Run targeted pytest for new and updated editorial calendar tests
- [x] 6.2 Run full test suite or agreed Flow A regression subset before archive
