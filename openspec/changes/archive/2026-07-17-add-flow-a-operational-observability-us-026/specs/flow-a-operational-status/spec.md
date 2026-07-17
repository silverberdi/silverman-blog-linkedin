## ADDED Requirements

### Requirement: Authenticated operational-status read endpoint

The worker SHALL expose `GET /flow-a/operational-status` protected by API-key authentication through `Depends(require_api_key)`.

The endpoint MUST accept an optional `now_utc` query parameter in canonical UTC `YYYY-MM-DDTHH:MM:SSZ` form. Invalid values MUST return HTTP 422. When omitted, the worker MUST capture current UTC once and use that one instant for every classification in the response.

The response MUST include `status`, `observed_at_utc`, `read_only`, `stale_after_seconds`, `summary`, `executions`, `campaigns`, `delayed_calendar_items`, and `data_issues`. `read_only` MUST always be `true`.

The endpoint MUST NOT accept filesystem paths or a dry-run parameter.

#### Scenario: Authenticated operator receives one consolidated response
- **WHEN** a client with a valid API key calls `GET /flow-a/operational-status`
- **THEN** the worker returns HTTP 200 with execution, campaign, calendar, and LinkedIn summary evidence in one structured JSON response

#### Scenario: Endpoint requires API-key authentication
- **WHEN** a client calls `GET /flow-a/operational-status` without a valid API key
- **THEN** the worker returns HTTP 401 and does not read or mutate operational artifacts

#### Scenario: Supplied observation time is deterministic
- **WHEN** two authenticated requests use the same canonical `now_utc` and the on-disk evidence is unchanged
- **THEN** both responses use that exact `observed_at_utc` and contain identical classifications and ordering

### Requirement: Authoritative and confined data sources

The operational-status service SHALL read only these fixed locations under the configured editorial base:

- direct `.json` files under `metadata/runs/`;
- direct `.json` files under `metadata/campaigns/`;
- `editorial-calendar/calendar.json`.

Campaign LinkedIn evidence MUST be read from existing campaign fields, including `linkedin_distribution` and `variants[]` schedule, queue, publication-state, and publication-time fields.

The service MUST reject symlinks or resolved files outside the approved source directory, MUST NOT recurse into arbitrary paths, and MUST NOT use any user-controlled value to construct a filesystem path.

Only campaign files with a valid canonical campaign ID, a filename matching the persisted `campaign_id`, and `flow: flow_a` MUST contribute to Flow A campaign results.

#### Scenario: Reads remain under the configured editorial base
- **WHEN** the endpoint aggregates operational status
- **THEN** every filesystem read resolves to one of the fixed run, campaign, or calendar locations under the configured editorial base

#### Scenario: Escaping symlink is rejected
- **WHEN** a direct source-directory entry is a symlink whose resolved target is outside its approved directory
- **THEN** the entry is not read, a stable path-confinement data issue is returned, and aggregation continues for valid artifacts

#### Scenario: Non-Flow-A campaign is excluded
- **WHEN** `metadata/campaigns/` contains a valid campaign document with `flow` other than `flow_a`
- **THEN** that document does not appear in the Flow A campaign list or campaign counts

### Requirement: Persisted worker execution classification

Each valid `metadata/runs/*.json` document SHALL be treated as one persisted worker execution record.

Execution outcomes MUST be derived exactly as follows:

- persisted `status` `completed` → `outcome` `successful`;
- persisted `status` `failed` → `outcome` `failed`;
- missing or any other persisted status → no successful or failed classification and a stable data issue.

The service MUST NOT infer a campaign link when the run record does not contain a valid persisted campaign identifier. It MUST NOT synthesize historical executions from campaign `attempt_count` or `state_history`.

Each execution summary MUST be restricted to safe fields: `run_id`, `trigger`, persisted `status`, derived `outcome`, `started_at`, `completed_at`, and validated machine-readable error codes. It MUST NOT return raw run JSON, `base_path`, content bodies, arbitrary exception text, credentials, or provider payloads.

#### Scenario: Completed run is successful
- **WHEN** a valid run record has `status` `completed`
- **THEN** it appears once with `outcome` `successful` and increments the successful-execution count

#### Scenario: Failed run is failed
- **WHEN** a valid run record has `status` `failed`
- **THEN** it appears once with `outcome` `failed`, includes only safe machine-readable error codes, and increments the failed-execution count

#### Scenario: Unknown run status is not guessed
- **WHEN** a run record has a missing or unsupported `status`
- **THEN** it increments neither successful nor failed execution counts and produces a stable data issue

#### Scenario: Campaign attempts are not fabricated as run history
- **WHEN** a campaign has `attempt_count` greater than one but no corresponding immutable run records
- **THEN** the campaign exposes its current attempt evidence only and the endpoint does not create synthetic successful or failed execution entries

### Requirement: Flow A campaign outcome classification

For each included Flow A campaign, the endpoint SHALL expose independent boolean fields `successful`, `failed`, `blocked`, `stale`, and `in_progress`, plus stable `health_reasons`.

`successful` MUST be true only when campaign `state` is `flow_a_complete`, `source_file_status.location` is `processed`, and `source_file_status.execution_state` is `idle`. This classification MUST mean successful campaign lifecycle completion only and MUST NOT claim live-site publication or LinkedIn API publication.

`failed` MUST be true when campaign `state` is `validation_failed` or `error`, or when `source_file_status.location` is `error`. Historical top-level errors or `last_error` alone MUST NOT mark a recovered successfully completed campaign failed.

`blocked` MUST be true when `failed` is true or when existing `source_file_status.recovery_classification` is `repair_required`, `requeue_required`, or `manual_intervention_required`. `retryable` alone MUST NOT mark a campaign blocked.

`in_progress` MUST be true exactly when neither `successful` nor `failed` is true. Blocked and stale MUST remain independent dimensions, so an in-progress campaign can also be blocked or stale.

#### Scenario: Processed lifecycle completion is successful but not LinkedIn-published
- **WHEN** a campaign has `state=flow_a_complete`, `location=processed`, `execution_state=idle`, and all variants remain `pending`
- **THEN** `successful` is true, `failed` and `in_progress` are false, and the response does not claim any LinkedIn variant was published

#### Scenario: Error-folder campaign is failed and blocked
- **WHEN** a campaign has `source_file_status.location=error`
- **THEN** `failed` and `blocked` are true with reasons identifying the existing error location

#### Scenario: Repair-required campaign is blocked but still in progress
- **WHEN** a non-failure-state campaign has `recovery_classification=repair_required`
- **THEN** `blocked` and `in_progress` are true and the response preserves the campaign lifecycle state without inventing a new state

#### Scenario: Retryable idle campaign is not automatically blocked
- **WHEN** an unfinished campaign is queued and idle with `recovery_classification=retryable`
- **THEN** `in_progress` is true and `blocked` is false

### Requirement: Read-only stale campaign derivation

Campaign staleness SHALL reuse `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`, including its existing default of 3600 seconds and minimum of 60 seconds.

`stale` MUST be true when:

- persisted `source_file_status.execution_state` is `stale`; or
- persisted execution state is `processing` and `observed_at_utc` is greater than or equal to `last_progress_at + stale_after_seconds`.

`last_progress_at` MUST be the canonical anchor. `processing_lease_expires_at` MUST NOT override the derived threshold. A processing campaign whose `last_progress_at` is missing or unparsable MUST fail safe as stale with a stable evidence reason.

The service MUST NOT call stale-detection mutators and MUST NOT persist an `execution_state` transition while observing.

#### Scenario: Processing becomes stale at the inactivity threshold
- **WHEN** a campaign is `processing` and `observed_at_utc` equals `last_progress_at + stale_after_seconds`
- **THEN** the response reports `stale=true` with the canonical anchor and threshold while the campaign file remains byte-for-byte unchanged

#### Scenario: Divergent lease does not change stale result
- **WHEN** `processing_lease_expires_at` differs from `last_progress_at + stale_after_seconds`
- **THEN** the endpoint classifies staleness from `last_progress_at` and reports the persisted lease only as evidence if it is included

#### Scenario: Missing progress clock fails safe
- **WHEN** a campaign has `execution_state=processing` and no valid `last_progress_at`
- **THEN** the endpoint reports `stale=true` with a stable missing-or-invalid-clock reason and performs no metadata repair

### Requirement: LinkedIn schedule and publication progress summary

Each campaign summary SHALL aggregate existing `variants[].publish_state` values without changing them.

The response MUST include counts for existing states `pending`, `queued`, `published`, `failed`, and `cancelled` when present. Unknown values MUST produce a data issue and MUST NOT be converted to a new state.

The summary MUST include existing `linkedin_distribution.strategy` and `anchor_utc` when present, the earliest valid pending `scheduled_at_utc`, earliest valid queued `publish_after_utc`, and latest valid published `published_at`.

The endpoint MUST count:

- pending variants with `scheduled_at_utc <= observed_at_utc` as elapsed scheduled windows;
- queued variants with `publish_after_utc <= observed_at_utc` as elapsed queue windows.

Elapsed windows MUST be descriptive only. They MUST NOT be reported as automatic publication failure or campaign lifecycle failure because explicit orchestration and existing sequence, cadence, supervision, enablement, and credential guards still apply.

The service MUST NOT execute or duplicate LinkedIn publication eligibility, sequence, cadence, OAuth, or dependency checks.

#### Scenario: Published and pending variants remain distinct
- **WHEN** a successful campaign lifecycle has one `published` variant and three `pending` variants
- **THEN** the campaign remains lifecycle-successful and the LinkedIn summary reports the exact existing publication-state counts without claiming all variants published

#### Scenario: Elapsed pending schedule is descriptive
- **WHEN** a `pending` variant has `scheduled_at_utc` at or before `observed_at_utc`
- **THEN** the elapsed-scheduled-window count increases while the variant remains `pending` and no publication-failure or blocked-campaign state is invented

#### Scenario: Publication failure remains visible
- **WHEN** a campaign contains a variant with `publish_state=failed`
- **THEN** the LinkedIn summary includes the failed count and safe stored failure code evidence without changing campaign lifecycle outcome

### Requirement: Delayed editorial calendar classification

The endpoint SHALL classify a calendar item as delayed only when its existing `status` is `planned`, `scheduled`, `due`, or `in_progress` and its canonical `due_at_utc` is strictly earlier than `observed_at_utc`.

The calendar delay anchor MUST be `due_at_utc`, which represents editorial processing start. LinkedIn `scheduled_at_utc`, `publish_after_utc`, and cadence timestamps MUST NOT be used as calendar delay anchors.

Items with existing terminal status `completed`, `skipped`, or `failed` MUST NOT be classified as delayed. An item whose `due_at_utc` equals `observed_at_utc` is due now and MUST NOT yet be classified as delayed.

Each delayed summary MUST include only `item_id`, `title`, existing `status`, `due_at_utc`, `flow_type`, existing `campaign_id` when present, and stable reason `calendar_item_past_due`.

#### Scenario: Scheduled item past its due time is delayed
- **WHEN** a calendar item has `status=scheduled` and `due_at_utc < observed_at_utc`
- **THEN** it appears once in `delayed_calendar_items` with reason `calendar_item_past_due`

#### Scenario: In-progress overdue item remains visible
- **WHEN** a calendar item has `status=in_progress` and its due time has passed
- **THEN** it is classified as delayed without changing its existing calendar status

#### Scenario: Exact due instant is not delayed
- **WHEN** a non-terminal item's `due_at_utc` equals `observed_at_utc`
- **THEN** the item is not included in delayed-calendar counts

#### Scenario: Completed item is never delayed
- **WHEN** a calendar item has `status=completed` and a past `due_at_utc`
- **THEN** it is excluded from delayed-calendar results

### Requirement: Partial results and deterministic ordering

The endpoint SHALL return `status=ok` when all configured sources are present, readable, valid for this view, and contain no rejected artifact. Empty valid directories or an empty valid calendar MUST remain `ok`.

The endpoint SHALL return `status=partial` when any source is missing, unreadable, malformed, path-rejected, identifier-inconsistent, or contains invalid classification evidence. Valid results from unaffected artifacts MUST still be returned.

Each problem MUST appear in `data_issues` with a stable source name, safe artifact identifier when available, and machine-readable reason. Raw exception messages and raw invalid document content MUST NOT be returned.

Ordering MUST be deterministic:

- executions by their available completion/start timestamp and then `run_id`, descending;
- campaigns by valid `updated_at` and then `campaign_id`, descending;
- delayed calendar items by `due_at_utc` and then `item_id`, ascending;
- data issues by source, identifier, and reason, ascending.

#### Scenario: One malformed campaign does not hide valid status
- **WHEN** one campaign JSON file is malformed and another is valid
- **THEN** the response is `partial`, includes a stable issue for the malformed file, and still includes the valid campaign

#### Scenario: Missing calendar is explicit
- **WHEN** `editorial-calendar/calendar.json` is absent
- **THEN** the response is `partial`, delayed-calendar results are empty, and `data_issues` includes `calendar_file_not_found`

#### Scenario: Empty valid evidence is healthy input
- **WHEN** run and campaign directories are readable but empty and the calendar is valid with no items
- **THEN** the response is `ok` with zero counts and no data issues

### Requirement: Strict read-only and safe-output guarantees

Operational-status aggregation MUST NOT write or replace run, campaign, calendar, source, LinkedIn, or public-blog files.

It MUST NOT move editorial files, claim or release execution, mark stale state, reconcile calendar state, queue or publish variants, call ComfyUI, DeepSeek, LinkedIn, OAuth, or live-site endpoints, run Git commands, read environment secret values, or create observability artifacts.

The response MUST be constructed from an explicit safe-field whitelist. It MUST NOT include Markdown or draft bodies, API keys, access or refresh tokens, client secrets, authorization headers, raw external API response bodies, arbitrary environment values, or the absolute editorial base path.

Repeated calls with unchanged evidence and the same `now_utc` MUST leave the complete approved source inventory and file bytes unchanged.

#### Scenario: Observation performs zero mutation
- **WHEN** the authenticated endpoint is called over valid and invalid operational evidence
- **THEN** file inventory and bytes under runs, campaigns, calendar, editorial lifecycle folders, and LinkedIn artifact folders are unchanged

#### Scenario: Observation performs no pipeline side effect
- **WHEN** the endpoint reports stale, blocked, failed, or delayed items
- **THEN** no lifecycle, reconciliation, recovery, publication, external API, or Git service is invoked

#### Scenario: Secrets and content bodies are excluded
- **WHEN** a source document contains a forbidden content field, token-shaped field, secret-shaped field, or raw external response
- **THEN** none of those values appears in the HTTP response and a safe data issue is returned when the artifact cannot be safely summarized

### Requirement: US-026 scope and verification

Implementation SHALL include behavioral service and HTTP tests for successful and failed persisted executions, campaign success/failure/block/stale combinations, delayed calendar boundaries, LinkedIn progress summaries, malformed and confined path handling, API-key authentication, invalid `now_utc`, deterministic ordering, safe output, and zero mutation.

The implementation MUST preserve existing Flow A lifecycle, queue, calendar, scheduling, and LinkedIn publication behavior and tests.

This capability MUST NOT implement US-027 stage durations or external-dependency failure breakdown, BL-011 alerting, or BL-015 UI behavior.

Operator documentation MUST explain the endpoint contract, classification rules, legacy run-record limitation, campaign lifecycle versus LinkedIn publication distinction, and read-only guarantee.

`docs/CURRENT-STATE.md` and product progress MUST be updated only to the level actually implemented and demonstrated. Proposal or code completion alone MUST NOT mark US-026 accepted or BL-010 closed; BL-010 remains incomplete until US-027 is separately satisfied and accepted.

#### Scenario: US-026 regression suite passes
- **WHEN** the change is verified
- **THEN** focused operational-status tests and existing affected Flow A regression tests pass without weakened assertions or new warnings

#### Scenario: Out-of-scope behavior remains absent
- **WHEN** the US-026 capability is implemented
- **THEN** no stage-duration fields, dependency-failure aggregation, alerts, notifications, UI, n8n workflow, or background monitor is added
