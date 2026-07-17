## Context

US-026 is the first BL-010 observability slice. Existing worker evidence is persisted in separate artifacts:

- `metadata/runs/*.json` records successful and failed worker endpoint executions, but the current schema does not consistently contain `campaign_id` and is not complete Flow A campaign-attempt history.
- `metadata/campaigns/*.json` is authoritative for Flow A campaign identity, lifecycle state, operational source location/execution state, recovery classification, current attempt evidence, state history, LinkedIn schedule metadata, and variant publication state.
- `editorial-calendar/calendar.json` is authoritative for editorial start timing (`due_at_utc`) and calendar item status.
- `variants[].scheduled_at_utc`, `publish_after_utc`, `publish_state`, and `published_at`, plus `linkedin_distribution.anchor_utc`, are authoritative campaign-local LinkedIn timing and publication evidence. They do not mean that campaign lifecycle completion and LinkedIn API publication are the same outcome.

The current worker has authenticated FastAPI routes and read helpers for individual artifacts, but no consolidated operational read surface. The capability must run inside the worker so n8n remains an HTTP-only orchestrator under ADR-0001 and never gains direct filesystem or shell access.

## Goals / Non-Goals

**Goals:**

- Add one authenticated, read-only JSON endpoint for persisted worker execution health, Flow A campaign progress, and delayed editorial calendar items.
- Define every derived classification against existing fields and one request-level UTC observation time.
- Expose independent campaign outcome, blocked, and stale flags so a campaign can be reported precisely without collapsing different dimensions into a new lifecycle state.
- Include safe LinkedIn schedule/publication summaries that preserve the distinction between campaign `flow_a_complete`, distribution scheduling, and actual LinkedIn API publication.
- Return partial, operator-understandable results when one on-disk source is malformed or unavailable.
- Guarantee path confinement, no secret/content-body leakage, deterministic ordering, and zero mutation.

**Non-Goals:**

- Stage-duration computation, stage timing persistence, percentile metrics, or per-dependency failure breakdown (US-027).
- Alerts, notifications, background polling, health checks against external services, or BL-011 behavior.
- UI or BL-015 supervision actions.
- Recovery, reconciliation, stale-claim mutation, publication, queueing, calendar completion, file moves, Git, or external API calls.
- New persisted campaign fields, run fields, calendar statuses, lifecycle states, or `publish_state` values.
- Pretending that legacy run records can be joined to campaigns when no persisted key exists.

## Decisions

### 1. Expose one authenticated GET endpoint

Add `GET /flow-a/operational-status`, protected by `Depends(require_api_key)`. It accepts one optional query parameter, `now_utc`, in canonical `YYYY-MM-DDTHH:MM:SSZ` form. When omitted, the service captures current UTC once and uses that instant for every classification in the response.

The response contract is:

- `status`: `ok` when every configured source was read and validated, otherwise `partial`; an empty but valid source is still `ok`.
- `observed_at_utc`, `read_only: true`, and `stale_after_seconds`.
- `summary`: counts for successful/failed persisted executions; campaign totals and independent successful, failed, blocked, stale, and in-progress flags; delayed calendar items; LinkedIn variant counts by existing `publish_state`; and source-data issues.
- `executions`: safe summaries partitioned by derived `outcome`.
- `campaigns`: safe campaign progress summaries with lifecycle evidence, independent health flags/reason codes, current execution-attempt evidence, last transition/error evidence, and LinkedIn schedule/publication summary.
- `delayed_calendar_items`: safe item summaries and delay reason.
- `data_issues`: stable source, artifact identifier when safe, and machine-readable reason for malformed or unreadable inputs.

No request body or `dry_run` flag is used: observation is intrinsically read-only.

Alternatives considered:

- Extend `GET /editorial-calendar/status`: rejected because campaign and execution health are broader than calendar status.
- Add a UI: rejected because BL-015 is a later backlog item.
- Let n8n read files directly: rejected by ADR-0001 and the worker ownership boundary.
- Use POST with dry-run: rejected because there is no mutating mode to guard.

### 2. Keep persisted worker executions separate from campaign attempts

Each valid file under `metadata/runs/` is a persisted worker execution record:

- `status == "completed"` → `outcome: "successful"`.
- `status == "failed"` → `outcome: "failed"`.
- Any other or missing status is not guessed; the record is omitted from successful/failed counts and a data issue is returned.

The safe execution summary includes only `run_id`, `trigger`, `status`, `started_at`, `completed_at`, and validated machine-readable error codes. It does not expose `base_path`, content, arbitrary provider payloads, or an inferred campaign ID.

Campaign `source_file_status.execution_attempt_id`, `attempt_count`, `processing_started_at`, and `last_progress_at` are exposed as current campaign attempt evidence, not synthesized as historical run records. This is intentionally honest about the existing persistence model while satisfying US-026 with the executions that are actually recorded.

Alternative considered: synthesize one execution per `state_history` entry or `attempt_count`. Rejected because neither source records one immutable success/failure outcome per attempt and synthesis would fabricate history.

### 3. Derive campaign dimensions independently

Only valid `flow: flow_a` campaign files under `metadata/campaigns/` participate. For each campaign:

**Successful campaign lifecycle**

`successful` is true only when all are true:

- `state == "flow_a_complete"`;
- `source_file_status.location == "processed"`;
- `source_file_status.execution_state == "idle"`.

This means successful campaign lifecycle completion only. It does not claim the blog is live or all LinkedIn variants are published.

**Failed campaign**

`failed` is true when either:

- campaign `state` is `validation_failed` or `error`; or
- `source_file_status.location == "error"`.

Top-level or last-error evidence alone does not make a recovered/terminally successful campaign failed.

**Stale campaign**

`stale` is true when either:

- `execution_state == "stale"`; or
- `execution_state == "processing"` and `observed_at_utc >= last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`.

The existing validated configuration is reused (default 3600 seconds, minimum 60). `last_progress_at` is the canonical anchor; `processing_lease_expires_at` is display evidence only and never overrides the derived threshold. A processing campaign with missing or unparsable `last_progress_at` fails safe as stale with a dedicated reason.

The observability service derives staleness only; it must not invoke `detect_stale_flow_a_execution` or persist `execution_state=stale`.

**Blocked campaign**

`blocked` is true when either:

- `failed` is true; or
- existing `source_file_status.recovery_classification` is `repair_required`, `requeue_required`, or `manual_intervention_required`.

`retryable` alone is not blocked, and stale is reported independently rather than silently converted to blocked. Reasons identify the exact existing state or recovery classification. A campaign may therefore be both failed and blocked, or stale without blocked.

**In progress**

`in_progress` is true when none of successful or failed is true. It remains independently possible for an in-progress campaign to be blocked or stale.

Alternative considered: create one precedence-based `health_state`. Rejected because it would hide combinations such as failed-and-blocked or in-progress-and-stale and would resemble a new lifecycle vocabulary.

### 4. Summarize LinkedIn progress without redefining campaign completion

Each campaign summary includes:

- counts by existing `publish_state` (`pending`, `queued`, `published`, `failed`, `cancelled`, plus an invalid-data issue for unknown values);
- `linkedin_distribution.strategy` and `anchor_utc`;
- earliest pending `scheduled_at_utc`, earliest queued `publish_after_utc`, and latest valid `published_at`;
- counts of pending variants whose `scheduled_at_utc` is at or before the observation time and queued variants whose `publish_after_utc` is at or before it.

These elapsed-window counts are descriptive, not new failure/block classifications: publication requires explicit orchestration and existing sequence/cadence/enablement guards. A variant with `publish_state=failed` remains visible as LinkedIn publication failure evidence but does not retroactively make campaign lifecycle completion unsuccessful.

Alternative considered: re-run publication eligibility and dependency checks in the status endpoint. Rejected because it would duplicate publication logic, risk drift, and cross into US-027 dependency analysis.

### 5. Define delayed calendar items from the editorial due time

A calendar item is delayed when:

- its status is one of `planned`, `scheduled`, `due`, or `in_progress`; and
- `due_at_utc < observed_at_utc`.

The delay anchor is always `due_at_utc`, which represents when editorial processing should start. LinkedIn `scheduled_at_utc` and `publish_after_utc` are not calendar-delay anchors. Terminal `completed`, `skipped`, and `failed` items are not delayed. Equality is due-now, not delayed; delay begins strictly after the due instant.

Each delayed item returns `item_id`, `title`, existing `status`, `due_at_utc`, `flow_type`, `campaign_id` when present, and reason `calendar_item_past_due`. Invalid calendar structure or timestamp evidence produces a data issue rather than a guessed delay result.

Alternative considered: delay only `scheduled`/`due`. Rejected because overdue `planned` and `in_progress` items also require operator visibility, while their existing statuses remain unchanged in the response.

### 6. Whitelist output and fail visibly on bad source data

The service reads only fixed paths formed internally from `settings.base_path`:

- `metadata/runs/*.json`;
- `metadata/campaigns/*.json`;
- `editorial-calendar/calendar.json`.

There is no user-supplied path. Directory entries are accepted only as direct `.json` files; symlinks or resolved files outside their approved directory are rejected. Campaign IDs are validated against existing campaign ID rules, and filenames must match persisted IDs before inclusion.

Responses are built from explicit whitelists. They never echo raw JSON documents, absolute base paths, Markdown/draft bodies, tokens, keys, client secrets, authorization values, arbitrary environment values, or raw external API responses. Error output uses stable reason codes rather than raw exception text.

One unreadable/malformed artifact yields `status: partial`, preserves valid results from other artifacts, and adds a `data_issues` entry. Missing required source directories or calendar file are likewise visible. Deterministic sort order is: executions by timestamp then run ID descending; campaigns by `updated_at` then campaign ID descending; delayed items by `due_at_utc` then item ID ascending; issues by source then identifier then reason.

Alternative considered: fail the whole endpoint on the first invalid file. Rejected because a consolidated operational view must still expose unaffected health evidence.

### 7. Enforce read-only behavior structurally

Implement a dedicated aggregation module using read-only file operations and pure derivation helpers. It must not import or call metadata writers, calendar savers, queue/lifecycle mutators, publication services, Git helpers, HTTP clients, or external dependency clients.

Tests snapshot file inventories, bytes, and metadata timestamps before and after repeated calls. The endpoint performs no opportunistic stale-state persistence, normalization, reconciliation, or repair. `read_only` is always true, including partial results.

## Risks / Trade-offs

- **[Risk] `metadata/runs/` is not complete Flow A attempt history and lacks reliable campaign linkage.** → Label it as persisted worker execution records, expose campaign attempt evidence separately, and defer richer immutable attempt telemetry to a future approved change.
- **[Risk] A derived stale result differs from the persisted `execution_state`.** → Return both persisted evidence and derived stale reasons; use the canonical `last_progress_at` rule and never mutate during observation.
- **[Risk] Malformed historical metadata could leak arbitrary text.** → Use field whitelists and stable reason-code validation; never echo raw documents or exceptions.
- **[Risk] Full-directory aggregation grows with history.** → Keep parsing linear and summaries compact. Pagination/retention is not added without demonstrated scale pressure and a separate contract decision.
- **[Risk] Operators read elapsed LinkedIn windows as guaranteed publication failures.** → Label them as elapsed schedule/queue windows and preserve the explicit-orchestration, sequence, cadence, and enablement caveat.
- **[Trade-off] Partial results are more useful but not transactionally consistent across files.** → Capture one observation time, read each file once, expose source issues, and make no cross-file correctness claim beyond persisted identifiers.

## Migration Plan

1. Add the new capability spec and implementation behind the existing worker API-key boundary.
2. Add focused service and HTTP tests, including byte-for-byte no-mutation checks and existing Flow A regression tests.
3. Update operator documentation and `docs/CURRENT-STATE.md` after implementation; mark US-026 progress only after its business outcome is demonstrated and accepted.
4. Deploy through the existing worker Docker process only after separate approval, then validate an authenticated read against controlled on-disk evidence.

Rollback removes the route and aggregation module. No data migration or rollback of persisted state is required because the capability writes nothing and adds no schema fields.

## Open Questions

None required for proposal approval. The design deliberately reports only evidence that the current schemas can support without inventing history or adding observability writes.
