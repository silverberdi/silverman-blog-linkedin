## 1. State and metadata model

- [x] 1.1 Add `SOURCE_LOCATION_QUEUED`, execution state constants, canonical recovery classification enum (`no_action`, `retryable`, `repair_required`, `requeue_required`, `manual_intervention_required`), and transition helpers to `campaign_lifecycle.py`
- [x] 1.2 Extend campaign metadata sanitization and initial document shape with `queued_*`, `error_*`, execution attempt fields, `last_error`, and `last_transition_at`
- [x] 1.3 Implement `invalid_operational_transition` enforcement and legacy compatibility readers for campaigns without queue metadata
- [x] 1.4 Add `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` configuration with fail-fast positive integer validation (minimum 60, default 3600)

## 2. Filesystem layout and coordinated moves

- [x] 2.1 Add `blog-posts/queued` to `EXPECTED_FOLDERS` in `paths.py`
- [x] 2.2 Implement shared coordinated Markdown+image move helper: Markdown-first, path confinement, no-overwrite, partial-move detection; queued collision rejection (no suffix rename); processed/error suffix allocation only when required with logical slug identity preserved
- [x] 2.3 Implement hidden-artifact filter helper (`.DS_Store`, `._*`, dotfile basenames) for scanners and queue candidacy

## 3. Queue acceptance and filesystem transitions

- [x] 3.1 Implement `accept_flow_a_source_for_queue` following the canonical protocol: resolve identity → intake checks → prepare metadata in memory → move Markdown (preserve filename) → move image → persist metadata → return status
- [x] 3.2 Record queue metadata only after Markdown is physically in `queued/` (`queued_source_relative_path`, `queued_at`, `original_source_relative_path`, `source_file_status.location=queued`)
- [x] 3.3 Implement reconciliation for metadata-write failure after move, image-only partial move, missing physical queued source, and lost-response idempotent retry; set `physical_move_state` and `recovery_classification=repair_required` as appropriate
- [x] 3.4 Implement idempotent same-campaign/same-hash queued destination acceptance and conflicting-destination rejection with `flow_a_queue_destination_collision`
- [x] 3.5 Implement `requeue_flow_a_source_from_error` (error→queued) preserving campaign identity, slug fields, and side-effect evidence

## 4. Processing claim and stale detection

- [x] 4.1 Implement `claim_flow_a_execution`, `release_flow_a_execution`, and `detect_stale_flow_a_execution` using canonical rule `now >= last_progress_at + stale_seconds`
- [x] 4.2 Set `last_progress_at` and derived `processing_lease_expires_at` at claim creation and after every completed Flow A stage boundary
- [x] 4.3 Reject duplicate claims when claim is not stale; allow reclaim when `execution_state=stale`
- [x] 4.4 Make `release_flow_a_execution` idempotent (`already_released` no-op) for defensive post-completion calls

## 5. Error and recovery semantics

- [x] 5.1 Classify failures into intake (no calendar, path safety, deterministic validation), editorial validation, transient runtime, pre-side-effect deterministic, and post-side-effect categories per design policy
- [x] 5.2 Implement deterministic intake-failure movement: no calendar → stay ready; unsafe path → no move; calendar-selected validation failure → error when applicable
- [x] 5.3 Implement pre-side-effect deterministic error-folder moves; post-side-effect failures stay in `queued/` with `repair_required` unless specific safe rule applies
- [x] 5.4 Keep transient failures in `queued/` with `recovery_classification=retryable` and populated `last_error`
- [x] 5.5 Preserve post-schedule partial-move repair behavior (`distribution_scheduled`, `flow_a_source_move_failed` / `partial`)

## 6. Flow A integration

- [x] 6.1 Insert queue-acceptance stage 0 and claim/release wrapping in `editorial_calendar_flow_a_execute.py`; terminal success relies on `complete_flow_a_source_lifecycle` for claim closure
- [x] 6.2 Implement already-queued campaign resolution (`skipped_already_queued`, `queued_source_relative_path` active path, no ready-file requirement)
- [x] 6.3 Add `queue_acceptance_status`, `failed_step=queue_acceptance`, and dry-run would-accept reporting on item results
- [x] 6.4 Update `flow_a_source_lifecycle.py` to move queued→processed and set `execution_state=idle` on terminal completion (legacy ready fallback for pre-queue campaigns only)
- [x] 6.5 Extend `resolve_campaign_source_paths` for queued, processing, and processed locations
- [x] 6.6 Update `blog_publish_flow.py`, `linkedin_package_flow.py`, and `linkedin_distribution_schedule.py` for queued path resolution

## 7. Validation and scanning integration

- [x] 7.1 Apply hidden-artifact filtering in `ready_scan.py` and queue candidacy paths
- [x] 7.2 Extend `validate_ready_post` / `file_reader.py` to accept `blog-posts/queued/` during processing validation
- [x] 7.3 Run full editorial validation at processing start (after queue acceptance, before publish)

## 8. Compatibility behavior

- [x] 8.1 Ensure legacy `processed`-only campaigns retain idempotent publish/package/schedule behavior
- [x] 8.2 Ensure sources remaining in `ready/` on first run after deploy are queue-accepted before publish
- [x] 8.3 Preserve dry-run: no queue moves, no claims, no lifecycle moves, no fabricated queue paths
- [x] 8.4 Preserve `flow_a_complete` terminal semantics and existing path traceability fields

## 9. Automated tests

- [x] 9.1 Add unit tests for operational transition table and invalid transition rejection
- [x] 9.2 Add tests for ready→queued acceptance preserving filename, calendar gating, and ready-without-calendar untouched
- [x] 9.3 Add tests for idempotent same-campaign/same-hash queued destination, conflicting queued destination rejection, and public slug unchanged after queue acceptance
- [x] 9.4 Add tests for claim, stale detection from `last_progress_at`, reclaim, and dry-run no-claim behavior
- [x] 9.5 Add tests for already-queued connector retry (transient failure, stale reclaim, distribution_scheduled lifecycle-only, post-due-time)
- [x] 9.6 Add tests for successful queued→processed Flow A path through connector
- [x] 9.7 Add tests for intake-failure categories (no calendar, unsafe path, deterministic validation), post-acceptance editorial validation failure, transient retry, and pre-side-effect error-folder moves
- [x] 9.8 Add tests for post-side-effect failures staying in queued with `repair_required` (after blog publish, after derivative generation, after scheduling/final move failure)
- [x] 9.9 Add tests for partial image moves, processed/error collision suffixes with unchanged logical slugs, and repair classifications
- [x] 9.10 Add tests for retry idempotency (no duplicate blog, derivative package, or schedule records)
- [x] 9.11 Add tests for requeue-from-error identity and side-effect evidence preservation
- [x] 9.12 Add tests for queue-acceptance protocol reconciliation (metadata failure after move, lost response)
- [x] 9.13 Add tests for hidden macOS artifact filtering
- [x] 9.14 Add tests for idempotent defensive `release_flow_a_execution` after lifecycle completion
- [x] 9.15 Add legacy campaign compatibility tests and extend connector/source-lifecycle test fixtures to ready→queued→processed
- [x] 9.16 Run full regression suite; confirm blog publish, image handoff, publish-date safety, article preview, derivative, and scheduling tests pass

## 10. Documentation and configuration

- [x] 10.1 Update workflow docs (`editorial-calendar-flow-a-execution-connector.md`, `phase-1-target-flow.md`) with ready/queued/processed/error semantics, recovery classifications, and queue acceptance protocol
- [x] 10.2 Document `blog-posts/queued/` creation expectation for deployment (no automatic data migration)
- [x] 10.3 Document `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` (minimum 60, default 3600) in worker configuration reference

## 11. Validation

- [x] 11.1 Run `openspec validate flow-a-operational-queue-lifecycle --strict`
- [x] 11.2 Run `openspec validate --all --strict`
