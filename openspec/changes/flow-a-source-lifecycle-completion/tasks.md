## 1. Preconditions

- [x] 1.1 Confirm archived changes `blog-image-public-asset-handoff`, `github-pages-publish-date-safety`, and `linkedin-article-preview-image-support` are deployed and baseline tests pass
- [x] 1.2 Review `openspec/changes/flow-a-source-lifecycle-completion/specs/` delta specs and approve before implementation

## 2. Source lifecycle module

- [x] 2.1 Create `flow_a_source_lifecycle.py` with `FlowASourceLifecycleResult` dataclass and stable error codes (`flow_a_source_move_failed`, `flow_a_source_move_partial`, `flow_a_source_lifecycle_premature`, `flow_a_source_move_collision_exhausted`)
- [x] 2.2 Implement `complete_flow_a_source_lifecycle(base_path, *, campaign_id, source_relative_path=None)` with eligibility gate (`distribution_scheduled` minimum)
- [x] 2.3 Implement Markdown move from `blog-posts/ready/` to `blog-posts/processed/` with deterministic `-processed-<n>` collision suffix
- [x] 2.4 Implement companion image move when `blog-posts/ready/<source_slug>.png` exists; record `original_image_relative_path` and `processed_image_relative_path`
- [x] 2.5 Implement idempotent skip when `source_file_status.location` is `processed` and processed paths exist on disk
- [x] 2.6 On success: update campaign metadata path fields, set `source_relative_path` to processed path, set `physical_move_completed_at`, transition to `flow_a_complete`
- [x] 2.7 On partial/failed move after schedule success: record `physical_move_state`, preserve `distribution_scheduled` state, return repairable errors/warnings

## 3. Campaign lifecycle metadata extensions

- [x] 3.1 Extend `campaign_lifecycle.py` initial metadata and sanitization for `original_source_relative_path`, `processed_source_relative_path`, image path fields, and `physical_move_state`
- [x] 3.2 Add shared helper `resolve_campaign_source_paths(campaign)` for active Markdown/image paths
- [x] 3.3 Extend `_find_campaign_by_source_path` (or equivalent) to match original, processed, and active `source_relative_path`

## 4. Flow A execution connector integration

- [x] 4.1 Invoke `complete_flow_a_source_lifecycle` as step 4 in `editorial_calendar_flow_a_execute._execute_flow_a_item` after successful `schedule_linkedin_distribution`
- [x] 4.2 Add `source_lifecycle_status` to `EditorialCalendarFlowAItemResult` (`completed`, `skipped`, `failed`)
- [x] 4.3 Preserve `execution_status: executed` when scheduling succeeds but lifecycle fails; merge lifecycle warnings/errors
- [x] 4.4 Confirm dry-run does not call lifecycle completion

## 5. Downstream idempotent source resolution

- [x] 5.1 Update `blog_publish_flow.py` preflight/idempotent paths to resolve processed sources for post-schedule campaigns
- [x] 5.2 Update `linkedin_package_flow.py` source read and campaign lookup for processed paths
- [x] 5.3 Update `linkedin_distribution_schedule.py` campaign lookup for original/processed paths on idempotent re-run

## 6. Tests

- [x] 6.1 Add `tests/test_flow_a_source_lifecycle.py`: successful `.md` move, image move, metadata path fields, idempotent skip, failure no-move, collision suffix
- [x] 6.2 Extend `tests/test_editorial_calendar_flow_a_execute.py`: lifecycle invoked after schedule; skipped on schedule failure; dry-run exclusion; post-schedule move failure warnings
- [x] 6.3 Add idempotent re-run tests for publish/package/schedule without ready copy (processed path only)
- [x] 6.4 Run full `pytest` and confirm blog publish, image handoff, publish-date safety, and article preview tests pass

## 7. Operator documentation

- [x] 7.1 Update `docs/workflows/editorial-calendar-flow-a-execution-connector.md` with step 4 source lifecycle, folder semantics, and repair guidance for `flow_a_source_move_failed`
- [x] 7.2 Update `docs/workflows/phase-1-target-flow.md` (or adjacent ops doc): `ready/` = pending input, `processed/` = consumed source, campaign metadata is traceability authority; operators must not manually move files after successful Flow A

## 8. Validation

- [x] 8.1 Run `openspec validate flow-a-source-lifecycle-completion --strict` and fix any issues
- [x] 8.2 Run `openspec validate --all --strict`
- [x] 8.3 Manual staging check: run real-mode Flow A connector for one post; verify `ready/` cleared and campaign metadata contains original/processed paths
