## Context

Flow A real execution (`execute_due_editorial_calendar_flow_a` with `dry_run=false`) runs queue acceptance → publish → package → schedule → source lifecycle completion. Campaign metadata and physical source files reach terminal `flow_a_complete` / `processed/`, but `editorial-calendar/calendar.json` is intentionally immutable per the current execution-connector spec. The first production run exposed the gap: calendar items stay `scheduled` with ready paths, so `plan_editorial_calendar_due` continues selecting them and `resolve_source_document` rejects them with `calendar_source_not_found`.

The post-04 calendar item already contains `campaign_id=flow-a-2026-07-10-a-bounded-context-is-not-a-folder`. Reconciliation must close it using that authoritative identity even though `blog-posts/ready/04-a-bounded-context-is-not-a-folder.md` no longer exists.

The planner already excludes `status=completed` from due selection (`DUE_STATUSES = {scheduled, due}`). The fix is to persist terminal calendar state after full Flow A success and to reconcile stale scheduled items when a resolvable `flow_a_complete` campaign exists — **before** treating missing ready sources as terminal rejection.

Calendar I/O today is read-only in `editorial_calendar_plan.py` (`load_calendar` only). Atomic JSON replace exists elsewhere (`linkedin_token_store._atomic_write_json`). No database or distributed lock is available or desired.

## Goals / Non-Goals

**Goals:**

- Close the calendar item only after the full Flow A contract succeeds: queue acceptance, claim, publish (including image remediation/handoff/validation), package, schedule, lifecycle completion, campaign `flow_a_complete`, source in `processed/`.
- Persist completion using canonical structured fields; extend schema minimally for completion facts not representable today.
- Reconcile stale calendar state for already-complete campaigns without re-running publication side effects.
- Use `campaign_id` as the authoritative reconciliation identity; allow legacy source-path fallback only for historical items genuinely lacking `campaign_id`.
- Run reconciliation before missing-source rejection in the executor.
- Never mutate `notes` on completion or reconciliation.
- Define precise semantics for failure, partial success, calendar-write failure, ambiguous campaign resolution, conflicting terminal facts, and idempotent no-write re-execution.
- Use atomic file replacement for `calendar.json`; preserve unrelated items byte-for-byte where practical.

**Non-Goals:**

- LinkedIn publication, n8n, cron, calendar database, ComfyUI/image changes, GitHub auto-push, broad calendar redesign, or migration of unrelated historical entries.
- Using `source_relative_path` as the normal reconciliation identity.
- Globally suppressing `calendar_source_not_found` for scheduled items without a resolvable completed campaign.

## Decisions

### 1. Lifecycle boundary for calendar completion

**Decision:** Invoke calendar completion only when `complete_flow_a_source_lifecycle` returns success (`source_lifecycle_status=completed` or idempotent skip equivalent) **and** campaign metadata confirms `state=flow_a_complete` with `source_file_status.location=processed`.

**Rationale:** Matches operator expectation that “Flow A finished” means blog published, derivatives scheduled, and source consumed. Aligns with existing connector rule that lifecycle failure leaves `execution_status=executed` but does not imply full completion.

**Alternative considered:** Complete calendar after scheduling success (before lifecycle move). Rejected — leaves source in `queued/` and contradicts “full lifecycle” requirement.

### 2. Campaign identity is authoritative for reconciliation

**Decision:** The canonical reconciliation identity MUST be `campaign_id`.

For a calendar item associated with Flow A:

1. If the calendar item contains `campaign_id`, use it as the authoritative lookup key.
2. Load exactly that campaign.
3. Verify that:
   - the campaign exists;
   - its campaign ID matches exactly;
   - its source/public identity is consistent with the calendar item;
   - its state is `flow_a_complete`;
   - its final source location is `processed`;
   - its lifecycle is complete.
4. Only then may the calendar item be reconciled to terminal `completed`.

Do **not** use `source_relative_path` as the normal reconciliation identity.

**Legacy fallback (backward compatibility only):** When `campaign_id` is genuinely absent on a historical calendar item, the executor MAY resolve by normalized ready `source_relative_path` against **completed Flow A campaigns only**. The fallback MUST:

- search only `flow_a_complete` campaigns;
- require exactly one unambiguous match;
- verify expected source/public identity consistency;
- perform no mutation when zero or multiple matches exist;
- return deterministic error `calendar_completion_campaign_unresolved`;
- never select the “first” match;
- never infer completion from the presence of a processed file alone.

**Rationale:** The post-04 item already has `campaign_id`; stale reconciliation must not depend on ready-file existence. Source-path lookup is a narrow compatibility path for pre-`campaign_id` history.

### 3. Reconciliation ordering in the executor

**Decision:** For each due/scheduled Flow A calendar item, the executor MUST evaluate campaign reconciliation **before** rejecting or skipping the item because its ready source is missing.

Ordering:

1. Inspect whether the item has an associated campaign identity (`campaign_id` first; legacy source-path fallback only when `campaign_id` is absent).
2. Determine whether that campaign is already `flow_a_complete` with valid lifecycle evidence.
3. If complete and lifecycle evidence is valid, reconcile the calendar item to terminal `completed`.
4. Return an idempotent reconciliation result.
5. Do **not** attempt normal source selection, validation, publication, image generation, packaging, scheduling, lifecycle operations, or attempt-count increment.

Only when no completed campaign can be resolved should existing source-selection and missing-source diagnostics run.

**Planner interaction:** Terminal `status=completed` items are excluded from due selection **before** source existence validation. After successful reconciliation, the item must not be returned as due, selected, rejected, or produce `calendar_source_not_found`. Genuinely scheduled items without a completed campaign retain existing missing-source behavior.

**Rationale:** Prevents stale completed campaigns from continuing to emit `calendar_source_not_found` when ready files are gone.

### 4. Calendar item terminal shape and field ownership

**Decision:** Keep `schema_version` `"1"` for read compatibility. On completion:

| Field | Role |
|-------|------|
| `status` | **Canonical** — set to `completed` |
| `campaign_id` | **Canonical** — authoritative reconciliation identity; set or confirmed from resolved campaign |
| `completed_at_utc` | **Canonical** — UTC `Z` timestamp of first terminal close; set once, never rewritten on idempotent retry |
| `processed_source_relative_path` | **Canonical** — final processed Markdown path |
| `source_relative_path` | **Canonical audit** — preserved as original explicit ready path |
| `notes` | **Immutable** — preserved byte-for-byte; never appended or rewritten by completion/reconciliation |
| `item_id`, `title`, `due_at_utc`, `flow_type`, `content_mode`, `source_folder`, `target_audience`, `topic_theme` | Preserved unchanged |
| `flow_a_completion` | **Summary evidence object** — operational facts at close/reconcile time; does not duplicate canonical item fields |

`flow_a_completion` MUST include at minimum:

- `campaign_state`
- `execution_status`
- `source_lifecycle_status`
- `blog_publish_status`
- `public_url` (nullable)
- `linkedin_package_status`
- `linkedin_distribution_status`

`flow_a_completion` MUST NOT duplicate `campaign_id`, `processed_source_relative_path`, or `completed_at_utc` from the parent item. It MUST NOT state or imply that LinkedIn variants were published; it may state only that package/distribution was scheduled.

**Rationale:** Machine-testable completion facts without polluting operator `notes`. Clear separation between canonical item fields and summary evidence.

### 5. Notes remain untouched

**Decision:** Completion and reconciliation MUST NOT append, prepend, or rewrite `notes`. Store all completion evidence only in canonical structured fields (`status`, `completed_at_utc`, `processed_source_relative_path`, `flow_a_completion`) and existing safe item fields (`campaign_id`).

**Alternative considered:** Append `[reconciled …]` to `notes`. **Rejected** — operator notes are editorial intent, not operational audit.

### 6. Where reconciliation runs

**Decision:** Reconciliation runs inside `execute_due_editorial_calendar_flow_a` per decision 3 ordering. Planner remains read-only; no separate reconciliation endpoint in this change.

**Rationale:** Smallest deterministic fix; executor already loads calendar and campaign; avoids planner mutating state.

### 7. Failure and partial-success calendar semantics

| Flow A outcome | Calendar action |
|----------------|-----------------|
| Failure before lifecycle completion (publish/package/schedule/lifecycle fail, queue fail) | Do **not** set `completed`; leave `scheduled`/`due` (or existing status) |
| Schedule success, lifecycle failure | Do **not** complete; aligns with `source_lifecycle_status=failed` / `repair_required` |
| Campaign `flow_a_complete` but calendar write fails | Do **not** roll back publication; item `calendar_update_status=failed`, error `calendar_completion_write_failed`; top-level `status=partial` when otherwise successful |
| Dry-run | No calendar writes (`read_only=true`) |
| Real execution without `calendar.json` persistence | No calendar write (`read_only=true`) |
| Real execution with successful `save_calendar_atomic` | Calendar persisted (`read_only=false`) |
| Ambiguous/missing campaign on reconciliation | No calendar mutation; error `calendar_completion_campaign_unresolved` |
| Completed item with conflicting terminal facts | No silent overwrite; error `calendar_completion_facts_conflict` |

**Decision:** Do not introduce calendar `status=failed` for Flow A execution failures in this change — scheduled items remain retryable per existing recovery semantics.

### 8. Calendar persistence failure response

**Decision:** Item-level fields: `calendar_update_status` (`completed`, `reconciled`, `skipped_already_completed`, `failed`, `not_applicable`), `calendar_update_errors[]` (or existing item `errors` for stable codes). Top-level execution `status` becomes `partial` when at least one item fully executed Flow A but calendar persistence failed. Campaign and filesystem state remain authoritative for idempotency.

**Recovery:** Operator re-runs executor with `dry_run=false`; reconciliation/completion path updates only the calendar item without republishing, re-packaging, re-scheduling, lifecycle moves, or ComfyUI calls.

### 9. Atomic write and concurrency

**Decision:** Add `save_calendar_atomic(base_path, calendar, *, expected_fingerprint=None)` in `editorial_calendar_plan.py`:

1. Validate full document via existing `load_calendar` validation helpers.
2. Set `updated_at_utc` to write timestamp (canonical `Z`).
3. Capture a stable pre-mutation fingerprint of on-disk `calendar.json` (raw-file SHA-256 hex digest).
4. Write to a uniquely named temporary file in the same directory (for example `.calendar.json.<pid>.<uuid>.tmp`), `json.dumps(..., indent=2) + "\n"`, with flush and `fsync`.
5. Immediately before `os.replace`, verify the on-disk calendar fingerprint still matches the captured fingerprint.
6. Atomically replace via `os.replace`, preserve original mode where safe, and `fsync` the parent directory where supported.
7. On validation failure, fingerprint mismatch, write/fsync failure, or replace failure before success: leave the original `calendar.json` valid and untouched; clean up any temporary file.

**Concurrency:** Optimistic concurrency without a database, distributed lock, or queue service. If the calendar file changed between read and replace, do not overwrite another writer's changes; return deterministic error `calendar_completion_concurrent_update`. Distinguish from `calendar_completion_write_failed` (filesystem/replace failure) and `calendar_completion_facts_conflict` (conflicting terminal completion facts within the target item). After Flow A success with a concurrent calendar conflict, keep campaign `flow_a_complete`, return top-level `partial`, and allow calendar-only retry on reconciliation without republication side effects.

**Item lookup:** Match by `item_id` only. Missing item → `calendar_item_not_found`. Duplicate IDs → rejected at validation (existing `load_calendar` rule).

### 10. Idempotent completion and no-write reconciliation

**Decision:** When the calendar item is already `status=completed` with equivalent completion facts:

- Perform **no** calendar-file write.
- Do **not** update `completed_at_utc`.
- Do **not** append history or mutate `notes`.
- Do **not** reorder unrelated items.
- Do **not** rewrite the calendar file merely to produce equivalent JSON.
- Do **not** create a duplicate completion event.
- Return `calendar_update_status=skipped_already_completed` with an idempotent no-op/reconciled result.

When the item is `completed` but contains **conflicting** completion facts (for example mismatched `campaign_id`, `processed_source_relative_path`, or `flow_a_completion` summary incompatible with the resolved campaign), do **not** silently overwrite. Return deterministic error `calendar_completion_facts_conflict` requiring operator review.

Equivalence comparison MUST cover canonical completion fields and `flow_a_completion` summary evidence.

### 11. Response distinctions

Use existing `EditorialCalendarFlowAItemResult` / execution response structures. Distinguish via `execution_status`, `calendar_update_status`, and stable error codes:

| Outcome | Signals |
|---------|---------|
| Normal Flow A completed and calendar closed | `execution_status=executed`, `calendar_update_status=completed` |
| Already-complete campaign reconciled into stale calendar | `execution_status=reconciled`, `calendar_update_status=reconciled` |
| Already-completed calendar, equivalent facts | `execution_status=reconciled` or `skipped_existing_campaign` per existing skip taxonomy, `calendar_update_status=skipped_already_completed` |
| Flow A succeeded, calendar persistence failed | top-level `status=partial`, `calendar_update_status=failed`, `calendar_completion_write_failed` |
| Calendar file changed concurrently during persistence | top-level `status=partial` when Flow A otherwise succeeded; `calendar_completion_concurrent_update`; no overwrite of concurrent changes; calendar-only retry allowed |
| Campaign resolution ambiguous or missing | `calendar_update_status=failed` or `not_applicable` with `calendar_completion_campaign_unresolved`; no Flow A side effects |
| Conflicting existing terminal calendar facts | `calendar_completion_facts_conflict`; no silent overwrite |

### 12. Planner behavior

**Decision:** No planner mutation logic required beyond verifying that `status=completed` items are excluded **before** `resolve_source_document`. Add regression tests confirming completed items never reach source validation and genuinely missing scheduled sources without a completed campaign still return `calendar_source_not_found`.

### 13. HTTP and security

- `POST /editorial-calendar/execute-flow-a-due` remains API-key protected.
- Calendar write occurs only in real execution path after successful lifecycle, or in reconciliation path without Flow A side effects.
- Responses MUST NOT include secrets; calendar completion summary uses existing safe result fields.

## Risks / Trade-offs

- **[Risk] Concurrent executor invocations could lose calendar updates** → Mitigation: optimistic raw-file SHA-256 fingerprint check immediately before atomic replace; conflicting writers receive `calendar_completion_concurrent_update` without overwriting on-disk state; atomic replace and temp-file cleanup prevent corrupt JSON.
- **[Risk] Historical items without `campaign_id` and ambiguous source paths cannot auto-reconcile** → Mitigation: deterministic `calendar_completion_campaign_unresolved`; operator adds `campaign_id` or resolves manually.
- **[Risk] Calendar write failure leaves operational drift** → Mitigation: explicit `partial` + `calendar_completion_write_failed`; calendar-only retry on reconciliation path.
- **[Trade-off] Original ready path retained while processed path is separate** → Status gate and `campaign_id` reconciliation are sufficient; planner must not treat missing ready file as failure once item is `completed`.

## Migration Plan

1. Deploy worker with calendar completion and reconciliation logic.
2. Existing `calendar.json` files remain valid (`schema_version` `"1"`); new fields appear only on completed items.
3. For stale item `04-a-bounded-context-is-not-a-folder` with `campaign_id=flow-a-2026-07-10-a-bounded-context-is-not-a-folder`: run `execute-flow-a-due` with `dry_run=false` to reconcile by `campaign_id` without republishing, even though the ready source is gone.
4. Rollback: revert worker; calendar files with new optional fields remain readable by older planner (extra fields ignored).
