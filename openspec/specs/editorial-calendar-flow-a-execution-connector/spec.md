# editorial-calendar-flow-a-execution-connector

## Purpose

Flow A execution connector for the `silverman-blog-linkedin` HTTP worker: consumes read-only planner output from `editorial-calendar-orchestration` and simulates or executes publish → generate LinkedIn package → schedule LinkedIn distribution for eligible Flow A items. Dry-run default; persists terminal `calendar.json` updates after successful full Flow A lifecycle completion or reconciliation of an already `flow_a_complete` campaign; no n8n activation, cron, or LinkedIn real publication. Staged rollout step 2 only.

## Requirements

### Requirement: Flow A execution connector distinct from planning and LinkedIn publication

The worker SHALL provide a Flow A execution connector that consumes output from `plan_editorial_calendar_due()` and either simulates or executes the publish → generate LinkedIn package → schedule LinkedIn distribution sequence.

Editorial calendar planning (`editorial-calendar-orchestration`) MUST remain read-only and MUST NOT be modified by this capability.

LinkedIn real publication (`publish_linkedin_due_variants`, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`) MUST NOT be invoked by this capability.

Campaign LinkedIn distribution scheduling (`schedule_linkedin_distribution`, `linkedin_distribution.scheduled_at_utc`) remains the authority for per-variant publish timing within a campaign; this connector invokes scheduling as part of Flow A execution only.

On successful real execution with full lifecycle completion, this connector MUST persist terminal calendar state via `save_calendar_atomic` as defined in `editorial-calendar-orchestration`.

Before honoring planner missing-source rejection for a due Flow A item, this connector MUST evaluate campaign reconciliation per the reconciliation ordering requirement.

#### Scenario: Connector does not call LinkedIn publication

- **WHEN** `execute_due_editorial_calendar_flow_a` runs in real execution mode
- **THEN** no code path calls `publish_linkedin_due_variants` or LinkedIn publication APIs

#### Scenario: Dry-run does not modify calendar.json

- **WHEN** `execute_due_editorial_calendar_flow_a` completes with `dry_run=true`
- **THEN** `editorial-calendar/calendar.json` content is unchanged from before the invocation

#### Scenario: Successful real execution updates calendar item on completion

- **WHEN** `execute_due_editorial_calendar_flow_a` completes a full Flow A lifecycle successfully with `dry_run=false`
- **THEN** the matching calendar item is persisted as `status=completed`, `notes` unchanged, and unrelated calendar items are unchanged
### Requirement: Execution service entry point

The worker SHALL expose `execute_due_editorial_calendar_flow_a(base_path, *, now_utc=None, dry_run=True, limit=None, git_publication=False)` returning a structured `EditorialCalendarFlowAExecutionResult` serializable to JSON.

The entry point MUST call `plan_editorial_calendar_due(base_path, now_utc=now_utc)` as its first step.

When planner returns `calendar_missing`, `calendar_invalid`, or `no_due_items`, the execution result MUST reflect that planner status without invoking publish, package, or schedule services.

During real execution (`dry_run=false`), when `git_publication` is `true`, the connector MUST pass `git_publication=True` to `publish_blog_post` for each eligible item.

When `git_publication` is `false` or omitted, the connector MUST call `publish_blog_post` without Git publication regardless of `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED`.

The result MUST include: `status`, `dry_run`, `now_utc`, `calendar_path`, `items`, `counts`, `errors`, `warnings`, and `read_only`.

Top-level `read_only` MUST be `true` when no `calendar.json` persistence occurred during the invocation.

Top-level `read_only` MUST be `false` only when `save_calendar_atomic` successfully persisted at least one calendar mutation in real execution mode.

Top-level `read_only` MUST NOT be inferred solely from `dry_run`; dry-run reconciliation previews, idempotent no-write reconciliation, unresolved reconciliation, conflicting reconciliation, Flow A failures before calendar persistence, and calendar persistence failures MUST leave `read_only=true`.

#### Scenario: Dry-run reconciliation preview stays read-only

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true` and would reconcile a stale calendar item
- **THEN** `read_only` is `true` and `calendar.json` is unchanged

#### Scenario: Real execution without calendar persistence stays read-only

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=false` but no item persists `calendar.json` (for example publish failure or calendar write failure)
- **THEN** `read_only` is `true`

#### Scenario: Real execution with calendar persistence is not read-only

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=false` and `save_calendar_atomic` succeeds for at least one item
- **THEN** `read_only` is `false`

#### Scenario: Missing calendar produces no execution

- **WHEN** `execute_due_editorial_calendar_flow_a` is called and the planner returns `calendar_missing`
- **THEN** the execution result reflects `calendar_missing`, `items` is empty, and no downstream services are called

#### Scenario: No due items produces no execution

- **WHEN** the planner returns `no_due_items`
- **THEN** the execution result reflects `no_due_items`, `items` is empty, and no downstream services are called

#### Scenario: Git opt-in passed to publish during real execution

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=false`, `git_publication=true`, and Git publication is enabled
- **THEN** `publish_blog_post` is invoked with `git_publication=True` for eligible items

#### Scenario: Git opt-in ignored during dry-run

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true` and `git_publication=true`
- **THEN** `publish_blog_post` is not invoked and no `git` operations occur
### Requirement: Dry-run default and safety

`dry_run` MUST default to `true` at the service entry point and HTTP endpoint.

When `dry_run` is `true`, the connector MUST:

- Call the planner
- Evaluate per-item execution eligibility
- Return structured decisions per item (MAY include `planned_flow_steps`)
- NOT call `publish_blog_post`, `generate_linkedin_package`, or `schedule_linkedin_distribution`
- NOT write campaign metadata, run metadata, or public blog repository content
- NOT move editorial files
- NOT simulate successful downstream outputs (no fabricated `campaign_id`, `source_public_url`, package IDs, or schedule slots in item results)

#### Scenario: Dry-run does not write or call downstream services

- **WHEN** `execute_due_editorial_calendar_flow_a` is called with `dry_run=true` and the planner selects one eligible Flow A item
- **THEN** the result includes a per-item decision, `read_only` is `true`, no campaign or run metadata files are created or modified, and publish/package/schedule functions are not invoked

#### Scenario: Dry-run eligible item reports would-execute decision

- **WHEN** `dry_run=true` and a due item is Flow A eligible with `review_required=false` and `selection_status=selected`
- **THEN** the item result indicates it would execute Flow A steps without performing them and does not include simulated downstream success outputs
### Requirement: Connector does not block on missing generatable PNG or image before publish

The connector MUST NOT invoke blocking full `validate_ready_post()` before `publish_blog_post` for eligible real-execution items.

Pre-generation validation and full validation MUST be owned by `publish_blog_post` per `worker-blog-publishing-endpoint`.

The connector MUST NOT fail an item with `ready_post_image_missing` before `publish_blog_post` when the source is Markdown-only with absent, empty, or canonical frontmatter `image` and automatic generation is eligible.

#### Scenario: Markdown-only queued source reaches publish without connector image failure

- **WHEN** real execution queue-accepts Markdown-only `blog-posts/ready/01-example.md` to `blog-posts/queued/01-example.md` with absent `image` and no PNG
- **THEN** the connector invokes `publish_blog_post` without prior full validation failure and does not record `ready_post_image_missing` at the connector validation step

#### Scenario: Connector does not stub away validation in integration tests

- **WHEN** integration tests prove the Markdown-only connector path
- **THEN** tests MUST NOT patch or autouse-stub `validate_ready_post` or `validate_ready_post_pre_generation` for assertions on that path
### Requirement: Image-related failure claim-release matrix

For image-related `publish_blog_post` failures after `claim_flow_a_execution`, the connector MUST apply exactly one claim-release path per case:

| Failure class | `release_flow_a_execution` | Notes |
|---------------|---------------------------|-------|
| ComfyUI transient (`blog_image_generation_*` retryable) | Exactly once | No downstream steps |
| Local write/patch inconsistency or active-folder backfill failure | Exactly once when claim `processing` | `retryable` or `repair_required`; no handoff or publish |
| Public handoff after full validation | Exactly once | `repair_required`; preserve editorial PNG |
| Hash metadata persistence failure | Exactly once when applicable | No handoff or publish |
| Deterministic pre/full validation before handoff with error move | Error move owns closure | Connector MUST NOT redundantly release |
| Error move or metadata failure during deterministic move | Per `repair_required` policy | No redundant release |

The connector MUST NOT invoke `generate_linkedin_package`, `schedule_linkedin_distribution`, or `complete_flow_a_source_lifecycle` on any image-related publish failure.

Integration tests MUST assert persisted campaign state and exact `release_flow_a_execution` call count for representative failure classes.

#### Scenario: ComfyUI transient failure releases claim once

- **WHEN** `publish_blog_post` fails with `blog_image_generation_timeout` after claim
- **THEN** connector calls `release_flow_a_execution` exactly once, leaves source in `queued/`, and does not invoke downstream steps

#### Scenario: Handoff failure releases claim once

- **WHEN** `publish_blog_post` fails with `blog_image_public_asset_handoff_failed` after full validation
- **THEN** connector calls `release_flow_a_execution` exactly once, sets `repair_required`, and does not invoke downstream steps

#### Scenario: Deterministic validation error move does not double-release

- **WHEN** post-acceptance editorial validation error move closes the claim while moving source to `error/`
- **THEN** connector does not call `release_flow_a_execution` again
### Requirement: Real execution Flow A sequence with result chaining

When `dry_run` is `false`, the connector MUST execute Flow A only for items where:

- Planner `selection_status` is `selected`
- `review_required` is `false`
- `flow_type` is `flow_a_ready_blog_post` and `content_mode` is `user_provided_approved_blog`
- Item is not skipped per existing-campaign or other skip rules

For each eligible item, the connector MUST invoke internal services in strict order:

0. `accept_flow_a_source_for_queue` (canonical spec `flow-a-operational-queue-lifecycle`) when source is in `blog-posts/ready/`; or resolve already-queued campaign per already-queued connector requirement when source has previously been accepted
1. `claim_flow_a_execution` then `publish_blog_post` — which owns pre-generation validation, editorial image remediation, authorized hash reconciliation, full validation, public handoff, and blog publication
2. `generate_linkedin_package`
3. `schedule_linkedin_distribution`
4. `complete_flow_a_source_lifecycle` (canonical spec `flow-a-source-lifecycle-completion`) — terminal completion sets `location=processed` and `execution_state=idle`
5. `release_flow_a_execution` ONLY on recoverable or failed non-terminal exits not already closed by error move; if invoked after successful lifecycle completion it MUST be idempotent (`already_released`)

The connector MUST NOT call `validate_ready_post()` or `validate_ready_post_pre_generation()` as a separate blocking step before `publish_blog_post`.

Each subsequent step MUST use the actual result object from the immediately prior step as its primary input source:

- After queue acceptance or already-queued resolution: publish MUST use `campaign_id` and active queued `source_relative_path` from acceptance or skip result
- After publish: `generate_linkedin_package` MUST prefer `campaign_id` from the publish result; when absent, MUST use `source_relative_path` from the publish result. Calendar `site_url` and other supported calendar fields MAY be passed when present.
- After package: `schedule_linkedin_distribution` MUST prefer `campaign_id` from the package result; when absent, MUST use `source_relative_path` from the package result. Calendar `strategy` MAY be passed when present and supported.
- After schedule: `complete_flow_a_source_lifecycle` MUST prefer `campaign_id` from the schedule result; when absent, MUST use `source_relative_path` from the schedule result.

The publish step result (`BlogPublishResult`) is the source of truth for resolved `campaign_id`, `source_public_url`, published blog path (`source_relative_path`), and blog publish status. Calendar hints MUST NOT override resolved publish/package outputs for subsequent steps.

The connector MUST preserve existing idempotency behavior of downstream services.

Lifecycle completion MUST NOT run when `schedule_linkedin_distribution` fails.

When scheduling succeeds but lifecycle completion fails, item `execution_status` MUST remain `executed` (scheduling succeeded) and item results MUST include `source_lifecycle_status` `failed` with lifecycle `errors[]` and `warnings[]` merged without exposing secrets.

When lifecycle completion succeeds or skips as already processed, item results MUST include `source_lifecycle_status` `completed` or `skipped`.

Item results MUST include `queue_acceptance_status` (`completed`, `skipped_already_queued`, `failed`, `partial`, `repair_required`) when queue stage runs.

When `publish_blog_post` fails with pre-generation or full validation errors before public handoff after queue acceptance, the connector MUST apply existing post-acceptance editorial validation failure policy (move to `error/` when deterministic) and MUST NOT redundantly release a claim already closed by error move.

When `publish_blog_post` fails with ComfyUI transient errors, the connector MUST apply retryable queued policy, call `release_flow_a_execution` exactly once, and MUST NOT classify the failure as `ready_post_image_missing`.

When `publish_blog_post` fails with public handoff errors after full validation, the connector MUST apply `repair_required` queued policy, call `release_flow_a_execution` exactly once, and preserve editorial PNG evidence.

#### Scenario: Real mode Markdown-only executes remediation inside publish

- **WHEN** `dry_run=false`, one eligible due Flow A item exists with Markdown-only source in `blog-posts/ready/` (absent `image`), queue acceptance succeeds, and ComfyUI generation is enabled
- **THEN** `publish_blog_post` is invoked with queued `source_relative_path`, editorial remediation and handoff run inside publish in staged order, blog publication proceeds on success, and lifecycle completion moves both queued Markdown and generated PNG to `blog-posts/processed/`

#### Scenario: Real mode executes queue acceptance then Flow A sequence

- **WHEN** `dry_run=false`, one eligible due Flow A item exists with source in `blog-posts/ready/`, and no skip rule applies
- **THEN** `accept_flow_a_source_for_queue`, `publish_blog_post`, `generate_linkedin_package`, `schedule_linkedin_distribution`, and `complete_flow_a_source_lifecycle` are invoked in order, the source ends under `blog-posts/processed/`, and the item `execution_status` is `executed` when scheduling succeeds

#### Scenario: Real mode uses internal services not HTTP self-calls

- **WHEN** real execution runs for an eligible item
- **THEN** the connector invokes Python service functions directly rather than HTTP loopback to worker endpoints

#### Scenario: Schedule failure skips lifecycle completion

- **WHEN** `schedule_linkedin_distribution` fails for an item in real execution mode after queue acceptance
- **THEN** `complete_flow_a_source_lifecycle` is not invoked and source files remain in `blog-posts/queued/`

#### Scenario: ComfyUI failure keeps source in queued with single release

- **WHEN** `publish_blog_post` fails with `blog_image_generation_timeout` after queue acceptance
- **THEN** the connector does not invoke lifecycle completion, source remains in `blog-posts/queued/`, `release_flow_a_execution` is called exactly once, and generated partial artifacts are preserved when present

### Requirement: Flow A calendar completion after lifecycle success

When `dry_run` is `false` and a due Flow A item completes the full execution contract — queue acceptance, processing claim, `publish_blog_post` (including image remediation, hash reconciliation, full validation, public handoff, and blog publication), `generate_linkedin_package`, `schedule_linkedin_distribution`, and `complete_flow_a_source_lifecycle` with campaign `state=flow_a_complete` and `source_file_status.location=processed` — the connector MUST persist terminal calendar state for that item.

Calendar completion MUST occur only after lifecycle completion succeeds. It MUST NOT run after scheduling alone, after publish alone, or when `source_lifecycle_status` is `failed`.

The connector MUST call `complete_flow_a_calendar_item` followed by `save_calendar_atomic` only when `complete_flow_a_calendar_item` indicates a persistable mutation.

The persisted item MUST have canonical fields `status=completed`, preserved original `source_relative_path`, resolved `campaign_id`, `completed_at_utc`, `processed_source_relative_path`, and `flow_a_completion` summary evidence. `notes` MUST remain byte-for-byte unchanged.

The `flow_a_completion` summary MUST record `campaign_state`, `execution_status`, `source_lifecycle_status`, `blog_publish_status`, `public_url` when available, `linkedin_package_status`, and `linkedin_distribution_status`. It MUST NOT duplicate parent-item canonical fields. It MUST NOT claim LinkedIn was published.

#### Scenario: Successful Flow A closes calendar item

- **WHEN** real execution completes lifecycle with campaign `flow_a_complete` and source under `blog-posts/processed/`
- **THEN** the matching calendar item becomes `status=completed` with completion fields persisted, `notes` unchanged, and original ready `source_relative_path` preserved

#### Scenario: Lifecycle failure does not complete calendar

- **WHEN** scheduling succeeds but `complete_flow_a_source_lifecycle` fails
- **THEN** the calendar item remains `scheduled` or `due` and is not marked `completed`

#### Scenario: Publish failure does not complete calendar

- **WHEN** `publish_blog_post` fails before lifecycle completion
- **THEN** the calendar item is not marked `completed`

#### Scenario: Notes unchanged on normal completion

- **WHEN** real execution completes lifecycle and persists calendar completion
- **THEN** the calendar item `notes` field is byte-for-byte identical to its pre-completion value

### Requirement: Flow A calendar completion failure semantics

When any Flow A stage fails before full lifecycle completion, the connector MUST NOT mark the calendar item `completed`.

When Flow A fails, the connector MUST preserve campaign failure evidence in existing execution item results and MUST NOT fabricate successful calendar completion.

Calendar item `status` MUST remain `scheduled` or `due` unless already terminal for unrelated reasons.

#### Scenario: Schedule failure leaves calendar schedulable

- **WHEN** `schedule_linkedin_distribution` fails
- **THEN** the calendar item remains due-selectable and is not marked `completed`

### Requirement: Calendar persistence failure after Flow A success

When campaign and physical source lifecycle complete successfully but calendar persistence fails, the connector MUST NOT roll back or duplicate publication, package, scheduling, or lifecycle side effects.

The item result MUST include `calendar_update_status=failed` and error code `calendar_completion_write_failed`.

The top-level execution `status` MUST be `partial` when Flow A execution otherwise succeeded but calendar persistence failed.

Campaign metadata MUST remain `flow_a_complete`.

A subsequent idempotent executor invocation MUST complete only the calendar item without republishing, re-packaging, re-scheduling, lifecycle moves, ComfyUI calls, or attempt-count increment.

#### Scenario: Calendar write failure returns partial result

- **WHEN** lifecycle completes successfully but `save_calendar_atomic` fails
- **THEN** the response has top-level `status=partial`, item `calendar_update_status=failed`, error `calendar_completion_write_failed`, and no duplicate blog publish occurs on retry

#### Scenario: Calendar-only retry after write failure

- **WHEN** Flow A previously completed with `flow_a_complete` but calendar persistence failed, and the operator re-runs the executor with `dry_run=false`
- **THEN** the connector reconciles or completes only the calendar item without Flow A side effects

### Requirement: Reconciliation ordering before missing-source rejection

For each due or scheduled Flow A calendar item processed by `execute_due_editorial_calendar_flow_a`, the connector MUST evaluate campaign reconciliation before rejecting or skipping the item because its ready source is missing.

Reconciliation ordering MUST be:

1. Inspect associated campaign identity (`campaign_id` when present; legacy source-path fallback only when `campaign_id` is absent per the legacy fallback requirement).
2. Determine whether the resolved campaign is `flow_a_complete` with valid lifecycle evidence.
3. If complete and lifecycle evidence is valid, reconcile the calendar item to terminal `completed`.
4. Return an idempotent reconciliation result.
5. Skip normal source selection, validation, publication, image generation, packaging, scheduling, lifecycle operations, and attempt-count increment.

Only when no completed campaign can be resolved MUST the connector apply existing source-selection and missing-source diagnostics.

After successful reconciliation, the item MUST NOT be returned as due on subsequent planner runs, MUST NOT be selected, MUST NOT be rejected, and MUST NOT produce `calendar_source_not_found`.

Genuinely scheduled items without a resolvable completed campaign MUST retain existing missing-source behavior including `calendar_source_not_found`.

#### Scenario: Reconciliation occurs before missing-source rejection

- **WHEN** a due Flow A item references a missing ready source but contains `campaign_id` for a `flow_a_complete` campaign with processed lifecycle evidence
- **THEN** the executor reconciles the calendar item before applying missing-source rejection and does not emit `calendar_source_not_found` for that item

#### Scenario: Stale completed campaign does not emit calendar_source_not_found

- **WHEN** campaign `flow-a-2026-07-10-a-bounded-context-is-not-a-folder` is `flow_a_complete`, the ready source no longer exists, and the calendar item remains `scheduled` with matching `campaign_id`
- **THEN** reconciliation closes the calendar item without `calendar_source_not_found`

#### Scenario: Genuine missing source without completed campaign still rejected

- **WHEN** a scheduled Flow A item has no resolvable completed campaign and its ready source is missing
- **THEN** existing missing-source diagnostics including `calendar_source_not_found` still apply

#### Scenario: Reconciliation performs no Flow A side effects

- **WHEN** reconciliation closes a stale calendar item for an already `flow_a_complete` campaign
- **THEN** the connector does not call ComfyUI, handoff, publish, package, schedule, lifecycle services, or increment attempt count

### Requirement: Authoritative campaign_id reconciliation

When reconciling a Flow A calendar item to terminal `completed`, the connector MUST use `campaign_id` as the authoritative reconciliation identity when the calendar item contains `campaign_id`.

The connector MUST:

1. Load exactly that campaign.
2. Verify the campaign exists, its ID matches exactly, its source/public identity is consistent with the calendar item, its state is `flow_a_complete`, its final source location is `processed`, and its lifecycle is complete.
3. Reconcile the calendar item to `status=completed` only after all checks pass.

The connector MUST NOT use `source_relative_path` as the normal reconciliation identity.

Reconciliation MUST set `calendar_update_status=reconciled`.

Reconciliation MUST populate canonical completion fields and `flow_a_completion` summary evidence from campaign metadata and persisted step results.

Reconciliation MUST NOT mutate `notes`.

#### Scenario: Reconciliation by exact campaign_id without ready source

- **WHEN** a calendar item contains `campaign_id=flow-a-2026-07-10-a-bounded-context-is-not-a-folder`, the ready source no longer exists, and that campaign is `flow_a_complete` with processed lifecycle evidence
- **THEN** the executor reconciles the calendar item to `completed` using `campaign_id` alone

#### Scenario: Already completed calendar with equivalent facts is idempotent no-op

- **WHEN** campaign is `flow_a_complete` and the calendar item is already `status=completed` with equivalent canonical completion facts
- **THEN** the executor performs no Flow A side effects, performs no calendar-file write, preserves `completed_at_utc`, leaves `notes` unchanged, and reports `calendar_update_status=skipped_already_completed`

### Requirement: Legacy source-path reconciliation fallback

When `campaign_id` is genuinely absent on a historical calendar item, the connector MAY resolve a unique `flow_a_complete` campaign by normalized original ready `source_relative_path` as a backward-compatibility fallback only. The fallback behavior MUST follow all constraints below.

The fallback MUST:

- search only completed Flow A campaigns;
- require exactly one unambiguous match;
- verify expected source/public identity consistency;
- perform no mutation when zero or multiple matches exist;
- return deterministic error `calendar_completion_campaign_unresolved`;
- never select the first match when multiple candidates exist;
- never infer completion from the presence of a processed file alone.

When zero matches exist, the connector MUST return `calendar_completion_campaign_unresolved` and perform no calendar mutation.

When multiple matches exist, the connector MUST return `calendar_completion_campaign_unresolved` and perform no calendar mutation.

#### Scenario: Unique legacy source-path fallback reconciles

- **WHEN** a historical calendar item lacks `campaign_id`, has normalized ready `source_relative_path`, and exactly one `flow_a_complete` campaign matches that source identity with valid lifecycle evidence
- **THEN** the executor reconciles the calendar item without Flow A side effects

#### Scenario: Zero fallback matches returns unresolved error

- **WHEN** a historical calendar item lacks `campaign_id` and no `flow_a_complete` campaign matches its normalized ready `source_relative_path`
- **THEN** the executor returns `calendar_completion_campaign_unresolved` and performs no calendar mutation

#### Scenario: Multiple fallback matches returns unresolved error

- **WHEN** a historical calendar item lacks `campaign_id` and more than one `flow_a_complete` campaign matches its normalized ready `source_relative_path`
- **THEN** the executor returns `calendar_completion_campaign_unresolved`, performs no calendar mutation, and does not choose the first match

#### Scenario: Notes unchanged on reconciliation

- **WHEN** reconciliation closes a stale calendar item
- **THEN** `notes` remains byte-for-byte unchanged

### Requirement: Conflicting terminal calendar completion facts

When reconciliation or completion is attempted for a calendar item already `status=completed` with terminal completion facts that conflict with the resolved campaign evidence, the connector MUST NOT silently overwrite existing facts.

The connector MUST return deterministic error `calendar_completion_facts_conflict` requiring operator review.

#### Scenario: Conflicting terminal facts return conflict error

- **WHEN** a calendar item is already `status=completed` with `campaign_id` A and reconciliation resolves campaign B, or with incompatible `processed_source_relative_path` or `flow_a_completion` summary evidence
- **THEN** the executor returns `calendar_completion_facts_conflict` and performs no calendar mutation

### Requirement: Dry-run calendar immutability

When `dry_run` is `true`, the connector MUST NOT write `calendar.json` and MUST NOT call `save_calendar_atomic`.

#### Scenario: Dry-run does not persist calendar completion

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true`
- **THEN** `calendar.json` is unchanged

### Requirement: Dry-run does not perform source lifecycle

When `dry_run` is `true`, the connector MUST NOT call `accept_flow_a_source_for_queue`, `claim_flow_a_execution`, `complete_flow_a_source_lifecycle`, or move editorial source files.

#### Scenario: Dry-run excludes queue acceptance and lifecycle

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true` for an eligible Flow A item
- **THEN** queue acceptance and lifecycle completion are not invoked, no `execution_state=processing` is written, and `read_only` is `true`
### Requirement: Dry-run queue acceptance reporting

When `dry_run` is `true` and an item would pass queue acceptance eligibility, the item result MUST report a would-accept queue decision without fabricated `queued_source_relative_path` values on disk.

#### Scenario: Dry-run reports would-accept without queue move

- **WHEN** `dry_run=true` and a due eligible Flow A item references a valid ready source
- **THEN** the item result indicates queue acceptance would occur and the source remains in `blog-posts/ready/`
### Requirement: Queue acceptance failure stops Flow A sequence

In real execution mode, when queue acceptance fails for an eligible item, the connector MUST NOT invoke publish, package, schedule, or lifecycle completion for that item.

The item MUST have `execution_status` `failed` and `failed_step` `queue_acceptance`.

#### Scenario: Queue acceptance failure prevents publish

- **WHEN** real execution runs for an eligible item and queue acceptance returns failed status
- **THEN** `publish_blog_post` is not invoked and `failed_step` is `queue_acceptance`
### Requirement: Already-queued campaign connector behavior

When `calendar.json` still references the original ready path but the campaign source has already moved to `queued`, a later connector invocation MUST:

- Resolve an existing campaign by persisted `campaign_id` before requiring the calendar source path to exist in `ready/`
- Match the calendar's original source path against `original_source_relative_path` (or first recorded `source_relative_path` when original is not yet set)
- Recognize `source_file_status.location=queued`
- Return `queue_acceptance_status=skipped_already_queued`
- Use `queued_source_relative_path` as the active path for subsequent Flow A steps
- Claim or reclaim execution according to execution state (including stale reclaim)
- Resume from the persisted Flow A pipeline `state`
- NOT move the source back to `ready/`
- NOT create a duplicate campaign
- NOT require the original ready file to exist

#### Scenario: Transient failure followed by later connector invocation

- **WHEN** queue acceptance succeeded and Flow A failed transiently with source in `blog-posts/queued/`, and a later connector invocation runs for the same calendar item still referencing the original ready path
- **THEN** `queue_acceptance_status` is `skipped_already_queued`, the ready file is not required, execution reclaims or resumes from persisted pipeline state, and the source is not moved back to `ready/`

#### Scenario: Stale claim followed by reclaim

- **WHEN** a campaign has `execution_state=stale` with source in `blog-posts/queued/` and the connector runs for the same calendar item
- **THEN** `queue_acceptance_status` is `skipped_already_queued`, execution is reclaimed, and Flow A resumes idempotently without duplicate side effects

#### Scenario: Distribution scheduled campaign requires only lifecycle completion

- **WHEN** a campaign has `state=distribution_scheduled`, `source_file_status.location=queued`, and scheduling metadata already exists
- **THEN** the connector skips queue acceptance with `skipped_already_queued`, resumes from `distribution_scheduled`, and invokes lifecycle completion when appropriate without re-running publish, package, or schedule unnecessarily

#### Scenario: Already-queued source after original due time

- **WHEN** a source was queue-accepted on its due date, the due time has passed, and the connector runs again for the same calendar item
- **THEN** `queue_acceptance_status` is `skipped_already_queued`, the source remains in `blog-posts/queued/`, and Flow A may continue without dequeuing or moving back to `ready/`
### Requirement: Failure handling stops Flow A sequence per item

In real execution mode, the connector MUST stop the Flow A sequence for an item at the first failing step:

- If `publish_blog_post` fails, the connector MUST NOT call `generate_linkedin_package` or `schedule_linkedin_distribution` for that item
- If `generate_linkedin_package` fails, the connector MUST NOT call `schedule_linkedin_distribution` for that item
- If `schedule_linkedin_distribution` fails, the item MUST be marked failed

A failed item MUST have `execution_status` `failed` and MUST include `failed_step` with exactly one of:

- `publish_blog`
- `generate_linkedin_package`
- `schedule_linkedin_distribution`

Failed item results MUST preserve downstream `errors[]` and `warnings[]` from the failing step without exposing secrets, tokens, or file body content.

#### Scenario: Publish failure stops package and schedule

- **WHEN** real execution runs for an eligible item and `publish_blog_post` returns a failed status
- **THEN** `generate_linkedin_package` and `schedule_linkedin_distribution` are not invoked for that item, the item `execution_status` is `failed`, and `failed_step` is `publish_blog`

#### Scenario: Package failure stops schedule

- **WHEN** real execution runs for an eligible item, publish succeeds, and `generate_linkedin_package` returns a failed status
- **THEN** `schedule_linkedin_distribution` is not invoked for that item, the item `execution_status` is `failed`, and `failed_step` is `generate_linkedin_package`

#### Scenario: Schedule failure marks item failed

- **WHEN** real execution runs for an eligible item, publish and package succeed, and `schedule_linkedin_distribution` returns a failed status
- **THEN** the item `execution_status` is `failed` and `failed_step` is `schedule_linkedin_distribution`
### Requirement: Calendar campaign_id guardrail and conflict handling

The connector MUST treat calendar `campaign_id` as the authoritative reconciliation identity and pre-execution guardrail for already-complete campaigns.

Pre-execution reconciliation ordering: for each due Flow A item, before missing-source rejection, when a calendar item includes `campaign_id` and campaign metadata exists with state `flow_a_complete` and valid processed lifecycle evidence, the connector MUST reconcile the calendar item or perform an idempotent no-op without invoking publish, package, schedule, lifecycle, or ComfyUI side effects.

Pre-execution: when a calendar item includes `campaign_id` and campaign metadata exists with state `distribution_scheduled` or any later lifecycle state before `flow_a_complete`, the connector MUST skip with `skipped_existing_campaign` and MUST NOT invoke publish, package, or schedule for that item unless reconciliation rules for stale `flow_a_complete` apply.

Post-step conflict: when a calendar item includes `campaign_id` and a completed publish or package step returns a resolved `campaign_id` that differs from the calendar value, the connector MUST:

- Set item `execution_status` to `failed`
- Set `failed_step` to the step that produced the conflicting identity (`publish_blog` or `generate_linkedin_package`)
- Include stable error code `calendar_campaign_id_conflict` in item `errors`
- NOT invoke subsequent steps for that item
- NOT mark the calendar item `completed`

The connector MUST NOT invent new campaign reconciliation policy (no campaign ID reassignment) beyond existing Flow A idempotency contracts in downstream services and the authoritative `campaign_id` reconciliation rules defined in this change.

#### Scenario: Calendar campaign_id pre-skip for already scheduled campaign

- **WHEN** a due item includes `campaign_id` matching campaign metadata with state `distribution_scheduled`
- **THEN** the item `execution_status` is `skipped_existing_campaign` and publish/package/schedule are not invoked for that item

#### Scenario: flow_a_complete stale calendar reconciled by campaign_id

- **WHEN** a due item includes `campaign_id` matching campaign metadata with state `flow_a_complete`, valid processed lifecycle evidence, and calendar `status` is still `scheduled`
- **THEN** the calendar item is reconciled to `completed` without publish/package/schedule/lifecycle side effects and without requiring the original ready source to exist

#### Scenario: Calendar campaign_id conflict fails item safely

- **WHEN** a due item includes calendar `campaign_id` `flow-a-2026-07-01-example`, publish succeeds with resolved `campaign_id` `flow-a-2026-07-06-different-slug`, and no skip rule applied earlier
- **THEN** the item `execution_status` is `failed`, `failed_step` is `publish_blog`, `calendar_campaign_id_conflict` is in item errors, package/schedule are not invoked, and the calendar item is not marked `completed`
### Requirement: Skip behavior for ineligible or already-processed items

The connector MUST skip execution (dry-run or real) with explicit per-item status when:

- Planner item `selection_status` is not `selected` → treat as not executable Flow A (`skipped_not_flow_a` or equivalent documented skip)
- `review_required` is `true` → `skipped_review_required`
- Item is not Flow A user-approved blog per planner policy → `skipped_not_flow_a`

Skipped items MUST NOT invoke publish, package, or schedule services.

#### Scenario: Review-required item skipped

- **WHEN** a due item has `review_required=true`
- **THEN** the item `execution_status` is `skipped_review_required` and no publish/package/schedule calls occur for that item

#### Scenario: Rejected source selection skipped

- **WHEN** planner returns an item with `selection_status=rejected`
- **THEN** that item is not executed and is reported with a skip status indicating not Flow A executable
### Requirement: Explicit calendar-item model for first connector

This capability MUST execute only items with planner-resolved `source_relative_path` from explicit calendar item configuration.

Queue-slot scheduling mode and every-X-days automatic folder source selection MUST NOT be implemented in this change.

#### Scenario: Explicit path item eligible after planner selection

- **WHEN** a calendar item specifies `source_relative_path`, the item is due, and the planner selects it
- **THEN** the connector may execute Flow A for that item subject to other eligibility rules
### Requirement: Optional execution limit

The service and HTTP endpoint MUST accept optional `limit` (positive integer). When provided, the connector MUST process at most `limit` eligible due items per invocation in planner order.

#### Scenario: Limit caps processed items

- **WHEN** three eligible due items exist and `limit=1`
- **THEN** at most one item is processed or reported as would-execute in dry-run
### Requirement: Structured execution response

Each element in `items[]` MUST include at minimum: `item_id`, `execution_status`, `source_relative_path` (when selected), `review_required`, `planned_flow_steps`, per-item `errors`, and per-item `warnings`. When `execution_status` is `failed`, the item MUST include `failed_step`.

When calendar completion or reconciliation is attempted, each item MUST include `calendar_update_status` with one of: `completed`, `reconciled`, `skipped_already_completed`, `failed`, or `not_applicable`.

When `calendar_update_status` is `failed`, the item MUST include `calendar_completion_write_failed`, `calendar_completion_concurrent_update`, `calendar_completion_campaign_unresolved`, `calendar_completion_facts_conflict`, or other stable calendar error codes in `errors`.

The response MUST distinguish, using existing structures:

- normal Flow A execution completed and calendar closed (`execution_status=executed`, `calendar_update_status=completed`)
- already-complete campaign reconciled into stale calendar (`execution_status=reconciled`, `calendar_update_status=reconciled`)
- already-completed calendar idempotent no-op (`calendar_update_status=skipped_already_completed`)
- Flow A succeeded but calendar persistence failed (top-level `status=partial`, `calendar_completion_write_failed`)
- Calendar file changed concurrently during persistence (`calendar_completion_concurrent_update`; no overwrite; calendar-only retry)
- campaign resolution ambiguous or missing (`calendar_completion_campaign_unresolved`)
- conflicting existing terminal calendar facts (`calendar_completion_facts_conflict`)

Aggregate `counts` MUST summarize item outcomes (for example counts of `executed`, `reconciled`, `skipped_existing_campaign`, `skipped_not_flow_a`, `skipped_review_required`, `failed`, and dry-run would-execute).

Top-level `status` MUST reflect overall outcome (for example `completed`, `partial`, `no_due_items`, `calendar_missing`, `calendar_invalid`). Top-level `status` MUST be `partial` when at least one item fully completed Flow A but calendar persistence failed.

#### Scenario: Response includes counts

- **WHEN** execution completes with mixed executed and reconciled items
- **THEN** the response includes `counts` reflecting each outcome category

#### Scenario: Response includes calendar update status for normal completion

- **WHEN** real execution completes lifecycle and calendar persistence succeeds
- **THEN** the item result includes `calendar_update_status=completed`

#### Scenario: Response includes calendar update status for reconciliation

- **WHEN** a stale calendar item is reconciled from an already `flow_a_complete` campaign
- **THEN** the item result includes `calendar_update_status=reconciled`
### Requirement: HTTP execution endpoint

The worker SHALL expose `POST /editorial-calendar/execute-flow-a-due` protected by API-key authentication (`Depends(require_api_key)`).

The request body MUST accept optional `now_utc`, `dry_run` (default `true`), `limit`, and `git_publication` (default `false`), and MUST use `extra="forbid"`.

Invalid `now_utc` format MUST return HTTP 422.

The response MUST serialize `EditorialCalendarFlowAExecutionResult`.

When an item's publish step returns `status: partial` because handoff succeeded but Git publication failed, the item result MUST surface publish partial evidence and stable Git error codes without treating the item as a complete publish failure before handoff.

#### Scenario: Authenticated execute endpoint succeeds

- **WHEN** a client with valid API key calls `POST /editorial-calendar/execute-flow-a-due`
- **THEN** the worker returns HTTP 200 with structured execution JSON

#### Scenario: Unauthenticated execute rejected

- **WHEN** a client calls `POST /editorial-calendar/execute-flow-a-due` without valid API key
- **THEN** the worker returns HTTP 401

#### Scenario: Invalid body rejected

- **WHEN** the request body includes unknown fields
- **THEN** the worker returns HTTP 422

#### Scenario: Default dry-run on HTTP

- **WHEN** a client calls the endpoint with an empty JSON body `{}`
- **THEN** `dry_run` is `true` and `git_publication` is `false` in the response

#### Scenario: HTTP Git opt-in on calendar execution

- **WHEN** a client calls `POST /editorial-calendar/execute-flow-a-due` with `dry_run: false`, `git_publication: true`, valid API key, and Git publication is enabled
- **THEN** eligible items invoke `publish_blog_post` with Git publication opt-in

#### Scenario: Environment enablement without request opt-in does not publish

- **WHEN** `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` and the calendar execution request omits `git_publication` or sets it false
- **THEN** publish performs handoff only and performs no `git` operations
### Requirement: Calendar connector Git publication tests

Automated tests MUST cover calendar execution with `git_publication: true` passing opt-in to `publish_blog_post`, environment-only enablement without opt-in performing no `git` operations, and item results reflecting publish `partial` status when handoff succeeds and Git push fails.

Tests MUST NOT require real network access or live GitHub credentials.

#### Scenario: Calendar opt-in passthrough test

- **WHEN** tests run real execution with `git_publication=true` and a mocked successful publish including Git publication
- **THEN** tests verify `publish_blog_post` was called with `git_publication=True`

#### Scenario: Calendar environment-only test

- **WHEN** tests run real execution with Git publication enabled in environment but `git_publication=false`
- **THEN** tests verify `publish_blog_post` was called without Git publication opt-in

#### Scenario: Calendar partial publish result test

- **WHEN** tests simulate publish returning `status: partial` after handoff success and Git failure
- **THEN** item results preserve handoff evidence and surface Git error codes
### Requirement: Operator documentation

The repository MUST document that this capability:

- Is the Flow A execution connector (staged rollout step 2)
- Does not activate n8n workflows or cron
- Persists terminal `calendar.json` updates only after successful full Flow A lifecycle completion in real execution mode, or via reconciliation of an already `flow_a_complete` campaign
- Does not publish LinkedIn content directly
- Defaults to dry-run; real execution requires explicit `dry_run: false`
- Distinguishes editorial calendar planning, Flow A execution, LinkedIn distribution scheduling, and LinkedIn real publication
- Documents `campaign_id` as authoritative reconciliation identity, legacy source-path fallback limits, reconciliation-before-missing-source ordering, `notes` immutability, and recovery when calendar persistence fails after publication completion (re-run executor for calendar-only reconciliation without republishing)

#### Scenario: Operator doc states dry-run first

- **WHEN** an operator reads the execution connector workflow documentation
- **THEN** it explicitly states dry-run is the default and real execution is opt-in

#### Scenario: Operator doc explains calendar completion boundary

- **WHEN** an operator reads the execution connector workflow documentation
- **THEN** it states calendar items become `completed` only after campaign `flow_a_complete` and source lifecycle completion, or via authoritative `campaign_id` reconciliation when the campaign is already complete
### Requirement: Staged rollout alignment

This change SHALL extend staged rollout step 2: Flow A execution connector with dry-run default and post-success calendar completion.

n8n/manual trigger wiring (step 3) and LinkedIn due-publication orchestration (step 4) MUST remain out of scope.

#### Scenario: Scope limited to execution connector

- **WHEN** this change is implemented and validated
- **THEN** no code path activates n8n, cron, or LinkedIn real publication
