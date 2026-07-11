## Why

The first real Flow A execution for campaign `flow-a-2026-07-10-a-bounded-context-is-not-a-folder` completed successfully: the source moved to `blog-posts/processed/`, and campaign metadata reached `state=flow_a_complete`. The matching editorial calendar item remained `status=scheduled` with the original ready path `blog-posts/ready/04-a-bounded-context-is-not-a-folder.md`. Later planner runs still treated the item as due and rejected it with `calendar_source_not_found` because the ready file no longer exists. Publication idempotency is intact, but the editorial calendar is operationally stale and produces avoidable planner noise.

The post-04 calendar item already contains `campaign_id=flow-a-2026-07-10-a-bounded-context-is-not-a-folder`. Its stale state must be safely reconcilable by authoritative `campaign_id` lookup even when the original ready source no longer exists.

## Goals

- When `POST /editorial-calendar/execute-flow-a-due` fully completes a Flow A item (campaign `flow_a_complete`, source in `processed/`), transition the matching calendar item to terminal `status=completed`.
- Persist completion facts in canonical structured calendar fields only; never mutate `notes`.
- Reconcile stale scheduled items when an associated campaign is already `flow_a_complete`, using `campaign_id` as the authoritative reconciliation identity.
- Run campaign reconciliation before missing-source rejection so stale completed campaigns do not continue producing `calendar_source_not_found`.
- Preserve planner correctness: completed items are not due, not selected, and do not produce `calendar_source_not_found`.
- Define failure, partial-success, calendar-write-failure, ambiguous-campaign, conflicting-facts, and idempotent no-write reconciliation semantics without rolling back completed publication side effects.
- Add focused tests and minimal operator documentation for calendar–campaign lifecycle alignment.

## Non-Goals

- LinkedIn API publication, n8n activation, cron/systemd, calendar database, or new infrastructure dependencies.
- ComfyUI, image-generation, article-preview, or GitHub auto-commit/push changes.
- Broad calendar redesign, unrelated historical migration, or modification of archived change `restore-flow-a-missing-image-generation`.
- Planner changes that globally suppress `calendar_source_not_found` for genuinely invalid scheduled items without a completed campaign.
- Using `source_relative_path` as the normal reconciliation identity.

## What Changes

- Add calendar persistence helpers (load already exists; add atomic save and item completion mutation) in the editorial calendar module layer.
- Extend `execute_due_editorial_calendar_flow_a` real execution to close the calendar item only after successful source lifecycle completion and campaign `flow_a_complete`.
- Add stale-calendar reconciliation ordered before missing-source rejection: resolve by authoritative `campaign_id` first; optional legacy fallback by normalized ready `source_relative_path` only when `campaign_id` is absent.
- Extend calendar item schema with minimal optional completion fields (`completed_at_utc`, `processed_source_relative_path`, `flow_a_completion` summary object) while preserving original `source_relative_path` and `notes` unchanged for audit.
- Extend execution result models with calendar update outcome fields (`calendar_update_status`, error codes, reconciliation flags).
- Add tests for success, planner exclusion, reconciliation ordering, legacy fallback ambiguity, failure paths, calendar-write failure, idempotent no-write reconciliation, notes immutability, concurrency-safe writes, and regression coverage.
- Update minimum workflow documentation for calendar item lifecycle, persistence-failure recovery, reconciliation identity, and planner behavior for terminal items.

## Capabilities

### New Capabilities

- _(none — behavior is an extension of existing editorial calendar and Flow A execution connector capabilities)_

### Modified Capabilities

- `editorial-calendar-orchestration`: Calendar item optional completion fields and validation; atomic `calendar.json` write helper; completion mutation by stable `item_id`; preserve unrelated items and `notes`; document terminal `completed` semantics and planner exclusion before source existence validation.
- `editorial-calendar-flow-a-execution-connector`: Replace immutability of `calendar.json` on successful real execution with post-lifecycle calendar completion; define reconciliation ordering, authoritative `campaign_id` lookup, legacy source-path fallback, failure/partial/calendar-write-failure/conflict/idempotent no-write semantics; extend structured execution response; update operator documentation expectations.

## Impact

- **Calendar module**: `src/silverman_blog_linkedin/editorial_calendar_plan.py` — `save_calendar`, `complete_flow_a_calendar_item`, validation for optional completion fields, atomic JSON replace.
- **Flow A connector**: `src/silverman_blog_linkedin/editorial_calendar_flow_a_execute.py` — reconciliation before missing-source rejection; calendar completion after lifecycle success; response fields for calendar update outcome.
- **HTTP contracts**: `POST /editorial-calendar/execute-flow-a-due` response shape (item-level calendar fields); planner unchanged except benefiting from completed items and explicit completed-before-source-validation ordering.
- **Tests**: Extend `tests/test_editorial_calendar_plan.py`, `tests/test_editorial_calendar_flow_a_execute.py`; add focused calendar persistence tests.
- **Documentation**: `docs/workflows/editorial-calendar-flow-a-execution-connector.md`, `docs/examples/editorial-calendar/calendar.example.json` — completion lifecycle, reconciliation identity, and recovery guidance.
- **Operations**: After successful Flow A or reconciliation, `calendar.json` reflects terminal state; operators no longer see recurring `calendar_source_not_found` for consumed items with resolvable completed campaigns.
