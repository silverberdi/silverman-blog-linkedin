## ADDED Requirements

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

## MODIFIED Requirements

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

### Requirement: Execution service entry point

The worker SHALL expose `execute_due_editorial_calendar_flow_a(base_path, *, now_utc=None, dry_run=True, limit=None)` returning a structured `EditorialCalendarFlowAExecutionResult` serializable to JSON.

The entry point MUST call `plan_editorial_calendar_due(base_path, now_utc=now_utc)` as its first step.

When planner returns `calendar_missing`, `calendar_invalid`, or `no_due_items`, the execution result MUST reflect that planner status without invoking publish, package, or schedule services.

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
