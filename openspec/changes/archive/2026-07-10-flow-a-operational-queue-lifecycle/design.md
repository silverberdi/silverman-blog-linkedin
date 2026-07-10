## Context

Flow A is implemented and deployed. The editorial calendar connector (`editorial_calendar_flow_a_execute`) runs publish → package → schedule → source lifecycle completion. Sources currently live in `blog-posts/ready/` until successful completion moves them to `blog-posts/processed/`. Campaign metadata (`flow-a-lifecycle`) tracks pipeline `state` and `source_file_status.location` (`ready` | `processed` | `error`) but cannot express accepted-but-not-started work, active execution ownership, or recoverable vs terminal failures.

Constraints:

- Worker owns file I/O over HTTP boundary only (ADR-0001); no n8n Execute Command.
- Editorial calendar remains read-only; `calendar.json` is not modified by this change.
- Existing idempotency keys for blog publish, derivatives, and scheduling must not be duplicated on retry.
- Real LinkedIn publication remains disabled.
- Filesystem-oriented single-worker model — no broker, database queue, or distributed lease infrastructure.
- Tests use temporary editorial layouts; no production server changes during implementation.

Established behavior to preserve: blog publishing, image handoff, publish-date safety, article preview metadata, derivative generation, distribution scheduling, `flow_a_complete`, and path traceability fields from `flow-a-source-lifecycle-completion`.

## Goals / Non-Goals

**Goals:**

- Formalize operational lifecycle: physical `ready` → `queued` → (`processed` | `error`) with logical `processing`.
- Define queue acceptance boundary tied to editorial calendar due items.
- Implement minimal execution claim with stale detection suitable for crash recovery.
- Classify failures and recovery actions deterministically for operators and a future console.
- Preserve backward compatibility for legacy campaigns and existing successful Flow A paths.
- Require comprehensive automated tests (specified in tasks; not written in propose phase).

**Non-Goals:**

- Operations console UI, n8n activation, cron/systemd, LinkedIn publication APIs.
- `calendar.json` edits, calendar-model redesign, public blog repo Git operations.
- Renaming `ready/` to `inbox/`, physical `processing/` folder, database/Redis queue.
- Retroactive migration of production sources or campaigns during proposal.
- Deployment tasks unless minimal worker folder-layout documentation is required post-implementation.

## Decisions

### 1. Canonical state model — two dimensions plus campaign pipeline state

**Decision:** Use three related but separate vocabularies:

| Dimension | Field | Values | Meaning |
|-----------|-------|--------|---------|
| Physical location | `source_file_status.location` | `ready`, `queued`, `processed`, `error` | Where Markdown (and companion image policy) resides on disk |
| Execution | `source_file_status.execution_state` | `idle`, `processing`, `stale` | Whether worker owns an active attempt (`idle` when not executing; `stale` when inactivity threshold exceeded) |
| Pipeline | campaign `state` | existing `flow-a-lifecycle` values | Publish/package/schedule progression (`ready` … `flow_a_complete`) |

`processing` is **not** a physical folder and **not** a `location` value. When execution begins, `location` stays `queued` while `execution_state` becomes `processing`.

**Rationale:** Avoids overloading `location` or campaign `state` with operational queue semantics. A future console can derive display state: `ready` (location=ready), `queued` (location=queued, execution=idle), `processing` (location=queued, execution=processing), `processed`, `error`, plus `stale` overlay.

**Alternative considered:** Physical `blog-posts/processing/` folder. Rejected — adds move churn, complicates partial-failure recovery, and duplicates metadata already needed for progress tracking.

**Alternative considered:** Rename `ready/` to `inbox/`. Rejected — breaks configs, tests, docs, and operator workflows without compelling benefit.

### 2. Allowed transitions

**Decision:** Normative transition table:

| From (location / execution) | Event | To | Physical move? |
|----------------------------|-------|-----|----------------|
| ready / idle | queue acceptance success | queued / idle | yes: ready→queued (+ image) |
| ready / idle | intake rejection (no calendar) | ready / idle | no |
| ready / idle | intake validation failure (deterministic, calendar-selected) | error / idle | yes: ready→error |
| queued / idle | claim + start execution | queued / processing | no |
| queued / processing | Flow A success + lifecycle complete | processed / idle | yes: queued→processed (+ image) |
| queued / processing | transient runtime failure | queued / idle | no |
| queued / processing | deterministic non-retryable failure before external side effects | error / idle | yes: queued→error (+ image) |
| queued / processing | failure after durable external side effects | queued / idle | no (repair in queued) |
| queued / processing | stale inactivity detected | queued / stale | no |
| queued / stale | reclaim on retry | queued / processing | no |
| error / idle | requeue | queued / idle | yes: error→queued (+ image) |
| processed / idle | idempotent re-run | processed / idle | no |
| any | invalid transition | rejected | no |

Campaign `state` transitions remain governed by `flow-a-lifecycle`; queue lifecycle does not replace pipeline states.

**Rationale:** Matches user-requested lifecycle while keeping partial side effects recoverable in `queued/`.

### 3. Queue acceptance boundary and move/metadata protocol

**Decision:** Queue acceptance (`accept_flow_a_source_for_queue`) runs as **stage 0** inside `execute_due_editorial_calendar_flow_a` (real mode) or reports a would-accept decision (dry-run).

**Canonical queue-acceptance protocol** (one protocol; no competing move-first vs metadata-first variants):

1. Resolve calendar and campaign identity (`campaign_id`, `source_content_sha256`, slug fields).
2. Perform safe minimum intake checks (calendar eligibility, path confinement, regular file, non-hidden artifact).
3. Prepare the intended metadata transition in memory without persisting `source_file_status.location=queued` or other false physical state.
4. Move Markdown from `ready/` to `queued/` preserving the original editorial filename (same basename).
5. Move the companion image if present beside the source in `ready/`.
6. Persist campaign metadata reflecting the actual observed move results (including partial image failure).
7. Return `completed`, `partial`, `failed`, or `repair_required` status.

**Pre-persistence rule:** MUST NOT persist `source_file_status.location=queued` before the Markdown file is physically accepted into `blog-posts/queued/`.

**Reconciliation cases:**

| Situation | Detection | Recovery |
|-----------|-----------|----------|
| Markdown in `queued/`, metadata still `ready` | physical file at `queued_source_relative_path`, metadata not updated | `repair_required`; metadata write reconciles to `queued` |
| Markdown moved, image move failed | `physical_move_state=partial` | `repair_required`; record which paths succeeded |
| Campaign metadata `queued`, physical queued source missing | metadata says queued, file absent | `repair_required`; operator repair |
| Lost queue-acceptance response, retry | same campaign + same hash, destination exists | idempotent `skipped_already_queued` / `completed` |

**Full editorial validation** (`validate_ready_post`) runs **after** acceptance at processing start (before `publish_blog_post`), not before the physical queue move.

**Sources without eligible calendar item:** remain untouched in `ready/`; queue acceptance is not attempted.

**Rationale:** Calendar drives responsibility transfer; light intake avoids queuing garbage; full validation still gates publish without blocking inbox inspection; metadata reflects observed physical state only after moves complete.

### 4. Editorial identity preservation and collision handling

**Decision:** Queue acceptance MUST preserve the original editorial filename when moving `ready/` → `queued/`. The source filename contributes to `source_slug`, `public_slug`, campaign identity, public paths, and idempotency. Automatic suffix renaming (for example `<stem>-queued-<n>.md`) MUST NOT occur for `queued/` acceptance.

**Queued destination collision policy:**

| Condition | Behavior |
|-----------|----------|
| Destination exists, same `campaign_id`, same `source_content_sha256` | Idempotent acceptance (`skipped_already_queued` / `completed`); no overwrite |
| Destination exists for different content, different campaign, or cannot be safely reconciled | Reject with stable error `flow_a_queue_destination_collision`; `recovery_classification=repair_required` |
| Unrelated content at destination | Never overwrite |

**Processed and error folders:** Collision suffixes (`-processed-<n>`, `-error-<n>`) MAY remain for compatibility when a free basename is unavailable. Physical suffixes MUST NOT change persisted logical `source_slug`, `public_slug`, `campaign_id`, or public URL identity — metadata retains canonical slug fields from the original editorial filename.

**Rationale:** Editorial identity must remain stable across operational moves; physical path suffixes are operational artifacts only.

### 5. Coordinated Markdown and image movement

**Decision:** Markdown and companion image movement is **coordinated but not transactionally atomic** as a pair.

- Each individual same-filesystem `rename` (or `shutil.move` fallback) MAY be atomic.
- Markdown is the primary source file; move Markdown first, then companion image when present.
- Every successful and failed component move MUST be recorded.
- Partial movement MUST set `physical_move_state=partial` and `recovery_classification=repair_required`.
- No source MUST be silently lost.
- Path confinement and no-overwrite guarantees apply to all moves.

**Rationale:** Filesystems cannot atomically move two files as one transaction; coordinated recording enables repair without pretending pair-level atomicity.

### 6. Execution ownership, stale detection, and duplicate prevention

**Decision:** Minimal claim record on `source_file_status`:

```json
{
  "execution_attempt_id": "<uuid>",
  "attempt_count": 1,
  "processing_claimed_at": "2026-07-10T14:30:00Z",
  "processing_started_at": "2026-07-10T14:30:01Z",
  "last_progress_at": "2026-07-10T14:30:45Z",
  "processing_lease_expires_at": "2026-07-10T15:30:45Z"
}
```

**Canonical stale-detection rule (single source of truth):**

- `last_progress_at` is persisted when the claim is created and after every completed Flow A stage boundary (publish, package, schedule, lifecycle completion).
- A processing claim is stale when: `now >= last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`.
- `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` defines the allowed **inactivity period**, not maximum total execution duration.
- `processing_lease_expires_at` is a **derived convenience field** equal to `last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`, updated together with `last_progress_at`. Stale detection MUST NOT use a separately maintained lease that diverges from `last_progress_at`.
- Stale detection sets `execution_state=stale` and `recovery_classification=retryable` without moving files.

**Configuration:** `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` MUST fail fast at load time if not a positive integer. Minimum allowed value: **60** seconds. Default: **3600**. Invalid values MUST raise a configuration error (stable error code such as `flow_a_processing_stale_seconds_invalid`).

**Claim behavior:**

- `claim_flow_a_execution(campaign_id)` sets `execution_state=processing`, generates new `execution_attempt_id`, increments `attempt_count`, sets `last_progress_at` and derived `processing_lease_expires_at`.
- Duplicate prevention: reject new claim when `execution_state=processing` and claim is not stale; allow reclaim when `stale`.
- `source_content_sha256` and `campaign_id` remain authoritative identity.

**Rationale:** One clock eliminates contradictory stale calculation; derived lease field aids operator readability without becoming a second source of truth.

### 7. Claim release ownership on terminal success

**Decision:**

- `complete_flow_a_source_lifecycle` atomically/logically finishes the terminal operational transition: sets `source_file_status.location=processed`, `execution_state=idle`, and related processed metadata.
- `release_flow_a_execution` is used for recoverable or failed **non-terminal** execution exits (transient failure, stale reclaim preparation, abandoned attempt cleanup).
- If the connector invokes `release_flow_a_execution` after successful lifecycle completion for defensive cleanup, it MUST be explicitly idempotent and return a no-op / `already_released` result without altering terminal state.

**Rationale:** Avoids two components independently closing the same execution claim.

### 8. Canonical recovery classification vocabulary

**Decision:** `source_file_status.recovery_classification` MUST use exactly these values:

| Value | Meaning |
|-------|---------|
| `no_action` | No operator action required; ready to proceed or already terminal |
| `retryable` | Automatic or scheduled retry expected (transient failure, stale reclaim) |
| `repair_required` | Physical/metadata mismatch or partial move; operator or repair tooling must reconcile |
| `requeue_required` | Terminal error state; explicit requeue needed before re-execution |
| `manual_intervention_required` | Active processing claim not stale; do not double-claim; operator decides |

Undocumented variants (for example `manual_intervention` without `_required`) MUST NOT be used.

### 9. Crash and stale-work recovery

**Decision:** Deterministic recovery classifications:

| Situation | Detection | Classification | Next action |
|-----------|-----------|----------------|-------------|
| Queued, never started | location=queued, execution=idle, no pipeline progress | `no_action` | Run Flow A |
| Processing, not stale | execution=processing, now < last_progress_at + stale_seconds | `manual_intervention_required` | Do not double-claim |
| Processing, stale | execution=processing, now ≥ last_progress_at + stale_seconds | `retryable` | Reclaim; resume idempotently |
| Metadata processing, file missing | execution=processing, queued file absent | `repair_required` | Operator repair paths |
| location=queued, campaign `flow_a_complete` | state mismatch | `repair_required` | Run lifecycle completion repair |
| Partial external side effects | pipeline state > validated, execution failed | `retryable` or `repair_required` by stage | Idempotent resume |
| Final move to processed failed | `distribution_scheduled`, physical_move_state partial/failed | `repair_required` | Existing lifecycle repair |
| error location | terminal failure recorded | `requeue_required` | `requeue_flow_a_source_from_error` |

Stale threshold configurable via environment variable; no heartbeat loop — `last_progress_at` updated synchronously at stage boundaries.

### 10. Retry and idempotency semantics

**Decision:**

- **Retry same attempt (after transient failure):** `release_flow_a_execution` sets `execution_state=idle`; source stays in `queued/`; downstream services use existing idempotency keys.
- **New execution attempt:** Increment `attempt_count`, new `execution_attempt_id` on reclaim after stale or explicit retry.
- **Requeue from error:** Physical move error→queued preserving original editorial filename; preserve `campaign_id`, `original_source_relative_path`, `source_content_sha256`, `source_slug`, `public_slug`; reset `execution_state=idle`; append `state_history` reason `requeued_from_error`; MUST NOT erase `blog_publish`, `variants`, scheduling, or `state_history` evidence — idempotent resume applies.
- **Rerun processed / flow_a_complete:** Existing skip semantics; no duplicate artifacts.
- **Partially completed campaign in queued:** Resume from last successful pipeline `state`; do not recreate campaign document.

### 11. Intake failure movement policy

**Decision:** Deterministic rules (no ambiguous "per policy" language):

| Failure category | Physical move | Queue acceptance attempted? | Failure metadata |
|------------------|---------------|----------------------------|------------------|
| No calendar match | none; stay in `ready/` | no | only if campaign safely identifiable |
| Missing source, path traversal, out-of-confinement, non-regular file, unresolvable path | none | no (or fails before move) | only when campaign record safely identified/created |
| Calendar-selected source failing deterministic intake/content validation before acceptance | `ready/` → `error/` | attempted, rejected | persisted on campaign |
| Post-acceptance editorial validation failure | `queued/` → `error/` | already completed | persisted on campaign |
| Unsafe or nonexistent paths | never move to `error/` | no | no false campaign state |

Failure metadata is persisted only when a valid campaign record can be safely identified or created. No "optional campaign" ambiguity.

### 12. Post-side-effect failure policy

**Decision:** Separate handling before and after durable external side effects:

| Phase | Deterministic non-retryable failure | Physical move to `error/`? |
|-------|-------------------------------------|---------------------------|
| Before blog publish | allowed | yes (`queued/` → `error/`) |
| After blog publish | normally not via generic deterministic rule | no; stay `queued/`, `repair_required` |
| After derivative generation | normally not via generic deterministic rule | no; stay `queued/`, `repair_required` |
| After scheduling / final move failure | lifecycle repair rule | no; stay `queued/` or partial processed, `repair_required` |

Moving a post-side-effect source to `error/` requires a specific safe rule outside the generic pre-publish deterministic-failure path, not the default.

Requeue from error MUST NOT erase blog publish, package, variant, scheduling, or state-history evidence.

### 13. Error-folder policy summary

| Failure class | Physical move to `error/`? | Stay in `queued/`? | Stay in `ready/`? |
|---------------|---------------------------|--------------------|-------------------|
| Pre-queue intake (no calendar match) | no | no | yes |
| Pre-queue path safety (missing, traversal, non-regular) | no | no | yes |
| Pre-queue deterministic validation (calendar-selected) | yes | no | no |
| Post-queue editorial validation (deterministic) | yes | no | no |
| Transient (network, dependency timeout) | no | yes | no |
| Post side-effect failure (publish/package/schedule) | no (default) | yes | no |
| Final move to processed failed | no | yes | no |
| Stale/crashed processing | no | yes | no |

### 14. Metadata evolution (additive)

**Decision:** Add to campaign document and `source_file_status`:

- `queued_source_relative_path`, `queued_image_relative_path`
- `error_source_relative_path`, `error_image_relative_path`
- `queued_at`, `last_transition_at`
- `execution_state`, `recovery_classification` (canonical enum)
- `last_error`: `{ category, error_code, reason, at, last_successful_stage, attempt_id }`
- Execution attempt fields (section 6)

Legacy compatibility:

- Missing queue fields + `location=processed` → treat as direct ready→processed completion.
- Missing queue fields + file in `ready/` → queue on next real execution.
- `source_relative_path` remains active resolution path; updated on each physical move.
- `original_source_relative_path` immutable after first set.
- `source_slug` and `public_slug` immutable after first set regardless of physical collision suffixes in `processed/` or `error/`.

### 15. Filesystem safety

**Decision:** Shared coordinated source move helper:

- Path traversal protection via resolved-path confinement (existing patterns).
- Same-filesystem `rename`, fallback `shutil.move`.
- Move Markdown first, then image; record partial state on image failure.
- Queued folder: no suffix allocation; collision rejection per section 4.
- Processed/error folders: suffix `-processed-<n>`, `-error-<n>` when required; logical identity unchanged.
- Missing companion image: proceed with Markdown only; `queued_image_relative_path` null.
- Repeated move/idempotent: if source already at destination with same identity, skip with `already_at_destination`.
- Hidden artifacts: ignore `.DS_Store`, `._*`, and any basename starting with `.` in scanners and queue candidacy.

### 16. Calendar compatibility and already-queued connector behavior

**Decision:**

- Calendar selects ready source; connector queue-accepts then executes in one command (two explicit internal stages).
- Queued item remains executable after original calendar time passes.
- Calendar metadata changes after acceptance do not cancel queued work.
- `calendar.json` never modified.

**Already-queued campaign on later connector invocation** (calendar still references original ready path):

The connector MUST:

1. Resolve existing campaign by persisted `campaign_id` before requiring the calendar source path to exist in `ready/`.
2. Match the calendar's original source path against `original_source_relative_path` (or first `source_relative_path` when original not yet set).
3. Recognize `source_file_status.location=queued`.
4. Return `queue_acceptance_status=skipped_already_queued`.
5. Use `queued_source_relative_path` as the active path.
6. Claim or reclaim execution according to execution state (including stale reclaim).
7. Resume from persisted Flow A pipeline `state`.
8. NOT move the source back to `ready/`.
9. NOT create a duplicate campaign.
10. NOT require the original ready file to exist.

Applies to: transient failure followed by later invocation; stale claim followed by reclaim; `distribution_scheduled` campaign in `queued/` requiring only lifecycle completion; already-queued source after original due time.

### 17. Compatibility with current Flow A

**Decision:**

- Add `blog-posts/queued/` to `EXPECTED_FOLDERS`.
- Existing `processed/` sources and `flow_a_complete` campaigns: no action.
- Legacy campaigns without queue metadata: readable; path resolution uses `processed_source_relative_path` or `source_relative_path`.
- Dry-run: reports `would_queue_accept` per item; no physical moves, no claims, no metadata writes.
- Tests/fixtures assuming ready→processed: updated to ready→queued→processed in implementation phase.

## HTTP boundary, configuration, and security

- No new HTTP endpoint required; queue acceptance and requeue are internal services called from the existing Flow A connector (and callable from tests).
- `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`: positive integer, minimum 60, default 3600; fail-fast on invalid value.
- Folder validation must include `blog-posts/queued` before queue operations.
- Responses and metadata must not expose secrets; error objects use stable `error_code` values only.

## Risks / Trade-offs

- **[Risk] Split state if metadata write fails after move** → Mitigation: repair classifications, `physical_move_state`, reconciliation protocol; file in `queued/` is physical source of truth until metadata catches up.
- **[Risk] Double execution if stale threshold too short** → Mitigation: conservative default (1h); minimum 60s; `last_progress_at` refreshed at each stage boundary.
- **[Risk] Legacy tests assume ready-only paths** → Mitigation: dedicated compatibility tests; update fixtures in implementation tasks.
- **[Risk] Operators confuse ready vs queued** → Mitigation: workflow doc table; metadata fields derivable by future console.
- **[Risk] Requeue with existing side effects** → Mitigation: idempotent downstream contracts; requeue does not reset publish/variant records.

## Migration Plan

1. Deploy worker with `blog-posts/queued/` in expected folders.
2. New Flow A runs: ready → queued → processing → processed.
3. Existing `ready/` posts: picked up on next due calendar execution via queue acceptance.
4. Existing `processed/` campaigns: unchanged; no backfill.
5. **Rollback:** Revert worker; files in `queued/` may need manual move to `ready/` or `processed`; campaigns with queue metadata remain readable.

## Open Questions

- None blocking proposal. Apply may add optional `POST /requeue-flow-a-source` only if operator testing without calendar connector proves necessary (default: internal service only).
