## Context

Flow A today runs publish → package → schedule via `editorial_calendar_flow_a_execute` (real mode) or ad hoc HTTP calls. Campaign lifecycle (`flow-a-lifecycle`) records `source_file_status.location = processed` at `flow_a_complete` but explicitly deferred physical file moves. Completed production runs leave files such as `02-deferring-is-not-avoiding-it-can-be-architecture.md` and `.png` in `blog-posts/ready/`, while public blog and LinkedIn artifacts are already produced.

Constraints:

- Worker HTTP boundary only; no n8n Execute Command (ADR-0001).
- Blog post is canonical; lifecycle completion must not republish or alter public blog or LinkedIn package content.
- `publish_blog_post`, `generate_linkedin_package`, and `schedule_linkedin_distribution` each own their domain side effects; source moves are a new orthogonal completion step.
- Existing idempotency for blog publish, derivatives, and scheduling must remain intact.
- Tests use temp editorial layouts; no live LinkedIn or public repo git operations.

## Goals / Non-Goals

**Goals:**

- Move source `.md` and companion `.png` (when present beside source in `ready/`) to `blog-posts/processed/` only after `schedule_linkedin_distribution` returns success (`status: completed`).
- Persist `original_source_relative_path`, `processed_source_relative_path`, optional image path fields, and `source_file_status` physical-move metadata on the campaign document.
- Transition campaign to `flow_a_complete` (or equivalent completion state) when source lifecycle succeeds.
- Idempotent skip when `source_file_status.location` is already `processed` and processed paths exist on disk.
- Allow Flow A service re-runs for `distribution_scheduled`+ campaigns without requiring files in `ready/`.
- Deterministic collision suffix when processed target filename already exists.
- Return structured `FlowASourceLifecycleResult` with stable error code `flow_a_source_move_failed` when move fails after scheduling succeeded.

**Non-Goals:**

- Moving files on validation/publish/package failure.
- LinkedIn publication, n8n, cron, calendar edits, public repo changes.
- New HTTP endpoint (internal service call only unless a future change adds one).
- Moving LinkedIn draft files or run metadata.
- Retroactive migration of already-published campaigns (operators may run a one-off repair script later; not in scope).

## Decisions

### 1. Dedicated `complete_flow_a_source_lifecycle()` module

**Decision:** Add `flow_a_source_lifecycle.py` with entry point `complete_flow_a_source_lifecycle(base_path, *, campaign_id, source_relative_path=None)` returning `FlowASourceLifecycleResult`.

**Rationale:** Keeps move semantics out of publish/package/schedule modules, which today explicitly MUST NOT relocate editorial files. Single place for collision rules, metadata updates, and idempotent skip.

**Alternative considered:** Move inside `schedule_linkedin_distribution`. Rejected because scheduling should not own filesystem lifecycle; also manual HTTP schedule-after-package flows would miss the move.

### 2. Invoke from Flow A execution connector after schedule success

**Decision:** `editorial_calendar_flow_a_execute._execute_flow_a_item` calls `complete_flow_a_source_lifecycle` as step 4 when `schedule_linkedin_distribution` succeeds. Item `execution_status` remains `executed` if scheduling succeeded; add `source_lifecycle_status` (`completed`, `skipped_already_processed`, `failed`) and warnings/errors on move failure.

**Rationale:** Matches user requirement that lifecycle runs only after full Flow A through scheduling. Connector is the canonical real-mode orchestrator.

**Alternative considered:** n8n-only move step. Rejected per scope (no n8n activation) and ADR-0001 worker ownership of file I/O.

### 3. Metadata path fields without breaking existing consumers

**Decision:**

- On first campaign creation, set `source_relative_path` to the ready path (unchanged behavior).
- At lifecycle completion, set:
  - `original_source_relative_path` — ready path at first processing (immutable once set)
  - `processed_source_relative_path` — final path under `blog-posts/processed/`
  - `original_image_relative_path` / `processed_image_relative_path` when companion image existed or was moved
  - `source_relative_path` updated to `processed_source_relative_path` for active resolution (with `original_source_relative_path` retained for traceability)
- `source_file_status.location = processed`, `marked_processed_at` set, optional `physical_move_completed_at`

**Rationale:** Existing code searching by `source_relative_path` continues to work after move if field is updated; `original_source_relative_path` satisfies audit requirement. Campaign lookup by either path supported in `_find_campaign_by_source_path`.

**Alternative considered:** Never update `source_relative_path`. Rejected because downstream services use it as the active path today.

### 4. Collision handling: deterministic suffix `-processed-<n>`

**Decision:** If `blog-posts/processed/<filename>` exists and is not the same inode/content as the source being moved, try `<stem>-processed-1<ext>`, incrementing `n` until a free name is found (cap at 99, then fail with `flow_a_source_move_collision_exhausted`).

**Rationale:** Predictable, testable, avoids overwriting unrelated processed files.

### 5. Atomic move via same-directory rename where possible

**Decision:** Use `Path.rename` for cross-directory move within same filesystem; if rename fails across devices, `shutil.move`. Move Markdown first, then image; on image move failure after Markdown moved, record partial state in metadata (`source_file_status.physical_move_state = partial`, error `flow_a_source_move_partial`) and return failed result without rolling back Markdown (operator repair doc).

**Rationale:** Partial failure after publish/schedule is rare but must be visible; rolling back Markdown from `processed/` to `ready/` risks re-triggering publish confusion.

### 6. Idempotent re-run source resolution helper

**Decision:** Add shared helper `resolve_campaign_source_paths(campaign) -> (md_path, image_path | None)` used by publish, package, and schedule preflight when campaign state is `distribution_scheduled`, `distribution_complete`, or `flow_a_complete` and `source_file_status.location == processed`.

**Rationale:** Centralizes processed-path reads; avoids duplicating prefix checks in three modules.

**Behavior:** If caller passes original ready `source_relative_path` or `campaign_id`, load campaign; when processed, read from `processed_source_relative_path` for content hash checks; short-circuit to `already_*` outcomes without requiring `ready/` file.

### 7. Dry-run and failure gates

**Decision:**

- Dry-run: no lifecycle call (connector already read-only).
- Schedule failed: no lifecycle call.
- Schedule succeeded, move failed: schedule result stands; lifecycle returns `failed` with `flow_a_source_move_failed`; campaign state remains `distribution_scheduled` (not `flow_a_complete`); warnings instruct operator to repair files and retry lifecycle completion by `campaign_id`.

**Rationale:** Avoids losing scheduling work; makes repair scope explicit.

## Risks / Trade-offs

- **[Risk] Partial move leaves split state** → Mitigation: `physical_move_state` and explicit error codes; operator doc for repair.
- **[Risk] n8n/manual flows that schedule without connector skip lifecycle** → Mitigation: document that full Flow A should use connector or call `complete_flow_a_source_lifecycle` after schedule; optional future HTTP hook out of scope.
- **[Risk] `process-ready` no longer lists moved posts** → Mitigation: expected behavior; calendar/campaign metadata drives re-runs.
- **[Risk] Regression on publish idempotency** → Mitigation: dedicated tests; processed-path resolution only for post-schedule states.

## Migration Plan

1. Deploy worker with lifecycle module; run Flow A on staging post with files in `ready/`.
2. Verify files land in `processed/` and campaign metadata contains path fields.
3. Re-run Flow A connector for same calendar item; confirm skip/idempotent behavior.
4. Production: no retroactive move; existing stuck files in `ready/` can be manually moved once or re-run after a small repair utility (deferred).

**Rollback:** Revert worker image; files already in `processed/` remain valid; campaigns with updated metadata still resolve via processed paths.

## Open Questions

- None blocking proposal. Apply may add optional `POST /complete-flow-a-source-lifecycle` only if operator testing without calendar connector proves necessary (default: internal service only).
