# flow-a-operational-status

## Purpose

Read-only aggregation contract for Flow A operational observability (BL-010 / US-026 + US-027): authenticated `GET /flow-a/operational-status`, deterministic execution/campaign/calendar/LinkedIn classifications from confined on-disk evidence, stage-duration derivation, external-dependency failure aggregation, partial-result handling, safe output, and zero-mutation guarantees. Does not implement BL-011 alerting or BL-015 UI.

## Requirements

### Requirement: Authenticated operational-status read endpoint

The worker SHALL expose `GET /flow-a/operational-status` protected by API-key authentication through `Depends(require_api_key)`.

The endpoint MUST accept an optional `now_utc` query parameter in canonical UTC `YYYY-MM-DDTHH:MM:SSZ` form. Invalid values MUST return HTTP 422. When omitted, the worker MUST capture current UTC once and use that one instant for every classification and open-stage duration derivation in the response.

The response MUST include `status`, `observed_at_utc`, `read_only`, `stale_after_seconds`, `summary`, `executions`, `campaigns`, `delayed_calendar_items`, `dependency_failures`, and `data_issues`. `read_only` MUST always be `true`.

`summary` MUST include the existing US-026 counts plus:

- `stage_durations` evidence counts for how many campaigns/executions contributed duration evidence and how many stage intervals were reported;
- `dependency_failures` counts for `comfyui`, `deepseek`, `linkedin`, `github_pages_checkout`, and `unclassified`.

The endpoint MUST NOT accept filesystem paths or a dry-run parameter.

#### Scenario: Authenticated operator receives one consolidated response
- **WHEN** a client with a valid API key calls `GET /flow-a/operational-status`
- **THEN** the worker returns HTTP 200 with execution, campaign, calendar, LinkedIn, stage-duration, and dependency-failure summary evidence in one structured JSON response

#### Scenario: Endpoint requires API-key authentication
- **WHEN** a client calls `GET /flow-a/operational-status` without a valid API key
- **THEN** the worker returns HTTP 401 and does not read or mutate operational artifacts

#### Scenario: Supplied observation time is deterministic
- **WHEN** two authenticated requests use the same canonical `now_utc` and the on-disk evidence is unchanged
- **THEN** both responses use that exact `observed_at_utc` and contain identical classifications, stage durations, dependency aggregations, and ordering

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

Each execution summary MUST be restricted to safe fields: `run_id`, `trigger`, persisted `status`, derived `outcome`, `started_at`, `completed_at`, validated machine-readable error codes, and `duration_seconds` when derivable under the stage-duration rules. It MUST NOT return raw run JSON, `base_path`, content bodies, arbitrary exception text, credentials, or provider payloads.

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

#### Scenario: Failed run duration and dependency codes remain safe
- **WHEN** a failed run has valid start/completion timestamps and validated dependency error codes
- **THEN** the execution summary may include `duration_seconds` and those codes remain available for dependency aggregation without exposing raw payloads

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

### Requirement: Stage duration derivation from persisted evidence

The operational-status service SHALL derive stage and execution durations read-only from existing persisted timestamps. It MUST NOT add, persist, or require new campaign or run timing fields for US-027.

Worker execution duration:

- When a valid run record has both `started_at` and `completed_at` as canonical UTC timestamps and `completed_at` is greater than or equal to `started_at`, the execution summary MUST include integer `duration_seconds` equal to the whole-second difference.
- When either timestamp is missing, `duration_seconds` MUST be omitted without inventing clocks.
- When timestamps are present but invalid or inverted, the service MUST omit `duration_seconds` and emit a stable data issue.

Campaign lifecycle stage intervals:

- The service MUST derive completed intervals from consecutive valid `state_history` entries on included Flow A campaigns.
- For each consecutive pair, `stage` MUST be the state occupied after the earlier entry (`to_state` of the earlier entry), `started_at` MUST be the earlier `at`, `ended_at` MUST be the later `at`, `duration_seconds` MUST be the whole-second difference when ordered, and `open` MUST be `false`.
- After the last valid history entry, the service MUST report one open interval with `open=true`, `ended_at=null`, and `duration_seconds` measured from the last `at` to `observed_at_utc` when that observation time is greater than or equal to the start.
- Invalid, non-chronological, or inconsistent history entries MUST produce stable data issues and MUST NOT fabricate missing transitions.
- When both `processing_started_at` and `last_progress_at` are valid and ordered, the campaign summary MAY include supplemental `attempt_duration_seconds`. That field MUST NOT replace lifecycle `stage_durations` and MUST NOT synthesize missing history.

Each campaign summary that has derivable intervals MUST include `stage_durations` sorted by `started_at` then `stage` ascending. Duration fields MUST use whole seconds and MUST NOT expose raw history reason text or forbidden content.

#### Scenario: Completed lifecycle stage interval is reported
- **WHEN** a Flow A campaign has consecutive valid `state_history` entries entering `validated` at `T1` and leaving for `blog_publish_pending` at `T2` where `T2 >= T1`
- **THEN** `stage_durations` includes one closed interval with `stage=validated`, `started_at=T1`, `ended_at=T2`, `open=false`, and `duration_seconds` equal to the whole-second difference

#### Scenario: Open current stage uses observation time
- **WHEN** the last valid history entry entered `derivatives_pending` at `T1` and `observed_at_utc` is later than `T1`
- **THEN** `stage_durations` includes an open interval with `stage=derivatives_pending`, `ended_at=null`, `open=true`, and `duration_seconds` measured to `observed_at_utc`

#### Scenario: Execution duration is derived from run clocks
- **WHEN** a valid run record has `started_at` and `completed_at` with `completed_at` after `started_at`
- **THEN** the execution summary includes `duration_seconds` as the whole-second difference and no run metadata file is modified

#### Scenario: Inverted stage clocks are not guessed
- **WHEN** consecutive history timestamps are inverted or unparsable
- **THEN** the affected interval is omitted, a stable data issue is returned, and valid intervals from the same campaign remain available

#### Scenario: No new timing fields are persisted
- **WHEN** the endpoint derives stage and execution durations
- **THEN** it does not create or update any campaign or run timing fields on disk

### Requirement: External dependency failure aggregation

The operational-status service SHALL aggregate existing validated machine-readable failure codes into external-dependency buckets without calling ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site endpoints.

Dependency buckets MUST be exactly:

- `comfyui` for codes matching `comfyui_*` or `blog_image_generation_*`;
- `deepseek` for codes matching `deepseek_*`;
- `linkedin` for codes matching `linkedin_*` that are not assigned to `github_pages_checkout` below;
- `github_pages_checkout` for codes matching `blog_publish_*`, `blog_git_publication_*`, `checkout_*`, `linkedin_preview_validation_checkout_*`, or exactly `linkedin_article_preview_public_repo_not_configured` (evaluate these patterns before the general `linkedin_*` bucket);
- `unclassified` for any other validated failure code present in scanned failure evidence.

Classification MUST use the persisted error-code family as written. The service MUST NOT re-attribute a code to a different dependency based on inferred causal root (for example `linkedin_package_generation_failed` remains `linkedin`).

Failure evidence sources MUST be limited to already-safe validated codes from failed run records, campaign top-level errors / last-error evidence, `state_history[].error_code` when valid, and LinkedIn variant publication failure codes already collected for the campaign summary.

The response MUST include:

- `summary.dependency_failures` with integer counts per bucket including `unclassified`;
- top-level `dependency_failures` entries sorted by dependency name ascending, each listing the dependency, failure attribution count after per-artifact code dedupe, sorted validated error codes, and safe `campaign_ids` / `run_ids` when available;
- optional per-campaign `dependency_failures` listing buckets and sorted safe error codes attributed to that campaign.

Repeated identical codes on the same artifact MUST count once per response. The service MUST NOT return raw exception text, provider payloads, secrets, or content bodies. Codes that cannot be validated under the existing safe-code rules MUST NOT be classified and MUST follow existing data-issue handling.

#### Scenario: ComfyUI failure is bucketed
- **WHEN** a failed campaign or run contains validated code `blog_image_generation_comfyui_failed`
- **THEN** the response increments `summary.dependency_failures.comfyui` and lists that code under the `comfyui` dependency entry

#### Scenario: DeepSeek failure is bucketed
- **WHEN** a failed run contains validated code `deepseek_timeout`
- **THEN** the response increments `summary.dependency_failures.deepseek` and does not call DeepSeek

#### Scenario: LinkedIn API or OAuth failure is bucketed
- **WHEN** LinkedIn variant evidence contains validated code `linkedin_publish_api_error` or a campaign records `linkedin_oauth_refresh_failed`
- **THEN** those codes appear under the `linkedin` dependency bucket

#### Scenario: GitHub Pages checkout failure is bucketed
- **WHEN** a campaign records validated code `blog_publish_public_repo_not_configured` or `blog_git_publication_push_failed`
- **THEN** the response increments `summary.dependency_failures.github_pages_checkout`

#### Scenario: Unknown validated failure code remains visible as unclassified
- **WHEN** failure evidence contains a validated code that matches no dependency family
- **THEN** it increments `unclassified`, appears in the unclassified dependency entry, and is not silently dropped

#### Scenario: Dependency aggregation performs no external calls
- **WHEN** the endpoint aggregates dependency failures
- **THEN** no ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site client or command is invoked

### Requirement: Partial results and deterministic ordering

The endpoint SHALL return `status=ok` when all configured sources are present, readable, valid for this view, and contain no rejected artifact. Empty valid directories or an empty valid calendar MUST remain `ok`.

The endpoint SHALL return `status=partial` when any source is missing, unreadable, malformed, path-rejected, identifier-inconsistent, or contains invalid classification, duration, or dependency-classification evidence. Valid results from unaffected artifacts MUST still be returned.

Each problem MUST appear in `data_issues` with a stable source name, safe artifact identifier when available, and machine-readable reason. Raw exception messages and raw invalid document content MUST NOT be returned.

Ordering MUST be deterministic:

- executions by their available completion/start timestamp and then `run_id`, descending;
- campaigns by valid `updated_at` and then `campaign_id`, descending;
- delayed calendar items by `due_at_utc` and then `item_id`, ascending;
- per-campaign `stage_durations` by `started_at` and then `stage`, ascending;
- `dependency_failures` by dependency name ascending, and error codes within each entry ascending;
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

#### Scenario: Stage and dependency collections sort deterministically
- **WHEN** two authenticated requests use the same `now_utc` against unchanged evidence containing multiple stage intervals and dependency buckets
- **THEN** `stage_durations` and `dependency_failures` ordering is identical in both responses

### Requirement: Strict read-only and safe-output guarantees

Operational-status aggregation MUST NOT write or replace run, campaign, calendar, source, LinkedIn, or public-blog files.

It MUST NOT move editorial files, claim or release execution, mark stale state, reconcile calendar state, queue or publish variants, call ComfyUI, DeepSeek, LinkedIn, OAuth, or live-site endpoints, run Git commands, read environment secret values, or create observability artifacts.

The response MUST be constructed from an explicit safe-field whitelist. It MUST NOT include Markdown or draft bodies, API keys, access or refresh tokens, client secrets, authorization headers, raw external API response bodies, arbitrary environment values, or the absolute editorial base path.

Repeated calls with unchanged evidence and the same `now_utc` MUST leave the complete approved source inventory and file bytes unchanged.

#### Scenario: Observation performs zero mutation
- **WHEN** the authenticated endpoint is called over valid and invalid operational evidence
- **THEN** file inventory and bytes under runs, campaigns, calendar, editorial lifecycle folders, and LinkedIn artifact folders are unchanged

#### Scenario: Observation performs no pipeline side effect
- **WHEN** the endpoint reports stale, blocked, failed, delayed, stage-duration, or dependency-failure items
- **THEN** no lifecycle, reconciliation, recovery, publication, external API, or Git service is invoked

#### Scenario: Secrets and content bodies are excluded
- **WHEN** a source document contains a forbidden content field, token-shaped field, secret-shaped field, or raw external response
- **THEN** none of those values appears in the HTTP response and a safe data issue is returned when the artifact cannot be safely summarized

### Requirement: US-027 scope and verification

Implementation SHALL extend the existing `flow-a-operational-status` capability for US-027 stage-duration and dependency-failure observability without creating a parallel status endpoint or duplicating US-026 classification semantics.

Focused behavioral tests MUST cover completed and open stage intervals, execution durations, each dependency bucket plus unclassified codes, invalid/inverted clocks, deterministic ordering of new collections, safe output, API-key authentication, and byte-for-byte zero mutation. Existing US-026 classification, calendar-delay, LinkedIn progress, confinement, and partial-result tests MUST continue to pass without weakened assertions.

This capability MUST NOT implement BL-011 alerting or BL-015 UI behavior, MUST NOT deploy or mutate live systems as part of the change, and MUST NOT add n8n workflow changes.

Operator documentation MUST describe stage-duration derivation, dependency-bucket mapping, open-stage observation relativity, and the distinction between execution duration and lifecycle stage duration.

`docs/CURRENT-STATE.md` and product progress MUST be updated only to the level actually implemented and demonstrated. This change MUST NOT mark US-026 accepted solely because US-027 is implemented, and MUST NOT close BL-010 until US-027 is separately satisfied and accepted.

#### Scenario: US-027 regression suite passes
- **WHEN** the change is verified
- **THEN** focused operational-status tests covering stage durations and dependency failures pass, and existing US-026 operational-status assertions remain intact

#### Scenario: Out-of-scope behavior remains absent
- **WHEN** the US-027 capability is implemented
- **THEN** no alert, notification, UI, n8n workflow, background monitor, live dependency probe, or mutating recovery path is added

#### Scenario: Single consolidated status surface is preserved
- **WHEN** an authenticated operator requests Flow A operational status
- **THEN** stage durations and dependency failures are returned from `GET /flow-a/operational-status` together with the existing US-026 fields

### Requirement: US-026 scope and verification

US-026 behavior remains part of this capability and MUST continue to identify successful and failed persisted executions, blocked or stale campaigns, and delayed calendar items with the classifications defined in this spec.

Implementation SHALL preserve behavioral service and HTTP tests for successful and failed persisted executions, campaign success/failure/block/stale combinations, delayed calendar boundaries, LinkedIn progress summaries, malformed and confined path handling, API-key authentication, invalid `now_utc`, deterministic ordering, safe output, and zero mutation.

The implementation MUST preserve existing Flow A lifecycle, queue, calendar, scheduling, and LinkedIn publication behavior and tests.

US-027 stage-duration and dependency-failure requirements are specified separately in this capability and MUST NOT regress US-026 classifications. BL-011 alerting and BL-015 UI behavior remain out of scope for this capability.

Operator documentation MUST continue to explain the endpoint contract, classification rules, legacy run-record limitation, campaign lifecycle versus LinkedIn publication distinction, and read-only guarantee, and MUST additionally cover US-027 fields when implemented.

`docs/CURRENT-STATE.md` and product progress MUST be updated only to the level actually implemented and demonstrated. Proposal or code completion alone MUST NOT mark US-026 accepted or BL-010 closed; BL-010 remains incomplete until US-027 is separately satisfied and accepted.

#### Scenario: US-026 regression suite passes
- **WHEN** the change is verified
- **THEN** focused operational-status tests and existing affected Flow A regression tests pass without weakened assertions or new warnings

#### Scenario: US-026 classifications remain authoritative
- **WHEN** stage-duration and dependency-failure fields are present in the response
- **THEN** successful/failed execution, blocked/stale/in-progress campaign, and delayed-calendar classifications still follow the US-026 rules without reinterpretation
