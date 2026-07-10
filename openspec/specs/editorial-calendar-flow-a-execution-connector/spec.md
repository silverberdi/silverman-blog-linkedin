# editorial-calendar-flow-a-execution-connector

## Purpose

Flow A execution connector for the `silverman-blog-linkedin` HTTP worker: consumes read-only planner output from `editorial-calendar-orchestration` and simulates or executes publish → generate LinkedIn package → schedule LinkedIn distribution for eligible Flow A items. Dry-run default; `calendar.json` remains immutable; no n8n activation, cron, or LinkedIn real publication. Staged rollout step 2 only.

## Requirements

### Requirement: Flow A execution connector distinct from planning and LinkedIn publication

The worker SHALL provide a Flow A execution connector that consumes output from `plan_editorial_calendar_due()` and either simulates or executes the publish → generate LinkedIn package → schedule LinkedIn distribution sequence.

Editorial calendar planning (`editorial-calendar-orchestration`) MUST remain read-only and MUST NOT be modified by this capability.

LinkedIn real publication (`publish_linkedin_due_variants`, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`) MUST NOT be invoked by this capability.

Campaign LinkedIn distribution scheduling (`schedule_linkedin_distribution`, `linkedin_distribution.scheduled_at_utc`) remains the authority for per-variant publish timing within a campaign; this connector invokes scheduling as part of Flow A execution only.

#### Scenario: Connector does not call LinkedIn publication

- **WHEN** `execute_due_editorial_calendar_flow_a` runs in real execution mode
- **THEN** no code path calls `publish_linkedin_due_variants` or LinkedIn publication APIs

#### Scenario: Connector does not modify calendar.json

- **WHEN** `execute_due_editorial_calendar_flow_a` completes in real execution mode
- **THEN** `editorial-calendar/calendar.json` content is unchanged from before the invocation

### Requirement: Execution service entry point

The worker SHALL expose `execute_due_editorial_calendar_flow_a(base_path, *, now_utc=None, dry_run=True, limit=None)` returning a structured `EditorialCalendarFlowAExecutionResult` serializable to JSON.

The entry point MUST call `plan_editorial_calendar_due(base_path, now_utc=now_utc)` as its first step.

When planner returns `calendar_missing`, `calendar_invalid`, or `no_due_items`, the execution result MUST reflect that planner status without invoking publish, package, or schedule services.

The result MUST include: `status`, `dry_run`, `now_utc`, `calendar_path`, `items`, `counts`, `errors`, `warnings`, and `read_only`.

When `dry_run` is `true`, `read_only` MUST be `true`.

#### Scenario: Missing calendar produces no execution

- **WHEN** `execute_due_editorial_calendar_flow_a` is called and the planner returns `calendar_missing`
- **THEN** the execution result reflects `calendar_missing`, `items` is empty, and no downstream services are called

#### Scenario: No due items produces no execution

- **WHEN** the planner returns `no_due_items`
- **THEN** the execution result reflects `no_due_items`, `items` is empty, and no downstream services are called

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

### Requirement: Real execution Flow A sequence with result chaining

When `dry_run` is `false`, the connector MUST execute Flow A only for items where:

- Planner `selection_status` is `selected`
- `review_required` is `false`
- `flow_type` is `flow_a_ready_blog_post` and `content_mode` is `user_provided_approved_blog`
- Item is not skipped per existing-campaign or other skip rules

For each eligible item, the connector MUST invoke existing internal services in strict order:

1. `publish_blog_post`
2. `generate_linkedin_package`
3. `schedule_linkedin_distribution`
4. `complete_flow_a_source_lifecycle` (canonical spec `flow-a-source-lifecycle-completion`)

Each subsequent step MUST use the actual result object from the immediately prior step as its primary input source:

- After publish: `generate_linkedin_package` MUST prefer `campaign_id` from the publish result; when absent, MUST use `source_relative_path` from the publish result. Calendar `site_url` and other supported calendar fields MAY be passed when present.
- After package: `schedule_linkedin_distribution` MUST prefer `campaign_id` from the package result; when absent, MUST use `source_relative_path` from the package result. Calendar `strategy` MAY be passed when present and supported.
- After schedule: `complete_flow_a_source_lifecycle` MUST prefer `campaign_id` from the schedule result; when absent, MUST use `source_relative_path` from the schedule result.

The publish step result (`BlogPublishResult`) is the source of truth for resolved `campaign_id`, `source_public_url`, published blog path (`source_relative_path`), and blog publish status. Calendar hints MUST NOT override resolved publish/package outputs for subsequent steps.

The connector MUST preserve existing idempotency behavior of downstream services.

Lifecycle completion MUST NOT run when `schedule_linkedin_distribution` fails.

When scheduling succeeds but lifecycle completion fails, item `execution_status` MUST remain `executed` (scheduling succeeded) and item results MUST include `source_lifecycle_status` `failed` with lifecycle `errors[]` and `warnings[]` merged without exposing secrets.

When lifecycle completion succeeds or skips as already processed, item results MUST include `source_lifecycle_status` `completed` or `skipped`.

#### Scenario: Real mode executes Flow A sequence with chained inputs

- **WHEN** `dry_run=false`, one eligible due Flow A item exists, and no skip rule applies
- **THEN** `publish_blog_post`, `generate_linkedin_package`, `schedule_linkedin_distribution`, and `complete_flow_a_source_lifecycle` are invoked in order for that item, package receives publish result identifiers, schedule receives package result identifiers, lifecycle receives schedule result identifiers, and the item `execution_status` is `executed` when scheduling succeeds

#### Scenario: Real mode uses internal services not HTTP self-calls

- **WHEN** real execution runs for an eligible item
- **THEN** the connector invokes Python service functions directly rather than HTTP loopback to worker endpoints

#### Scenario: Schedule failure skips lifecycle completion

- **WHEN** `schedule_linkedin_distribution` fails for an item in real execution mode
- **THEN** `complete_flow_a_source_lifecycle` is not invoked and source files remain in `blog-posts/ready/`

### Requirement: Dry-run does not perform source lifecycle

When `dry_run` is `true`, the connector MUST NOT call `complete_flow_a_source_lifecycle` and MUST NOT move editorial source files.

#### Scenario: Dry-run excludes lifecycle completion

- **WHEN** `execute_due_editorial_calendar_flow_a` runs with `dry_run=true` for an eligible Flow A item
- **THEN** `complete_flow_a_source_lifecycle` is not invoked and `read_only` is `true`

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

The connector MUST treat calendar `campaign_id` in `calendar.json` as a guardrail and reconciliation hint — not authoritative over downstream publish or package outputs.

Pre-execution: when a calendar item includes `campaign_id` and campaign metadata exists with state `distribution_scheduled` or any later lifecycle state, the connector MUST skip with `skipped_existing_campaign` and MUST NOT invoke publish, package, or schedule for that item.

Post-step conflict: when a calendar item includes `campaign_id` and a completed publish or package step returns a resolved `campaign_id` that differs from the calendar value, the connector MUST:

- Set item `execution_status` to `failed`
- Set `failed_step` to the step that produced the conflicting identity (`publish_blog` or `generate_linkedin_package`)
- Include stable error code `calendar_campaign_id_conflict` in item `errors`
- NOT invoke subsequent steps for that item

The connector MUST NOT invent new campaign reconciliation policy (no calendar writes, no campaign ID reassignment) beyond existing Flow A idempotency contracts in downstream services.

#### Scenario: Calendar campaign_id pre-skip for already scheduled campaign

- **WHEN** a due item includes `campaign_id` matching campaign metadata with state `distribution_scheduled`
- **THEN** the item `execution_status` is `skipped_existing_campaign` and publish/package/schedule are not invoked for that item

#### Scenario: Calendar campaign_id conflict fails item safely

- **WHEN** a due item includes calendar `campaign_id` `flow-a-2026-07-01-example`, publish succeeds with resolved `campaign_id` `flow-a-2026-07-06-different-slug`, and no skip rule applied earlier
- **THEN** the item `execution_status` is `failed`, `failed_step` is `publish_blog`, `calendar_campaign_id_conflict` is in item errors, and package/schedule are not invoked for that item

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

Aggregate `counts` MUST summarize item outcomes (for example counts of `executed`, `skipped_existing_campaign`, `skipped_not_flow_a`, `skipped_review_required`, `failed`, and dry-run would-execute).

Top-level `status` MUST reflect overall outcome (for example `completed`, `partial`, `no_due_items`, `calendar_missing`, `calendar_invalid`).

#### Scenario: Response includes counts

- **WHEN** execution completes with mixed executed and skipped items
- **THEN** the response includes `counts` reflecting each outcome category

### Requirement: HTTP execution endpoint

The worker SHALL expose `POST /editorial-calendar/execute-flow-a-due` protected by API-key authentication (`Depends(require_api_key)`).

The request body MUST accept optional `now_utc`, `dry_run` (default `true`), and `limit`, and MUST use `extra="forbid"`.

Invalid `now_utc` format MUST return HTTP 422.

The response MUST serialize `EditorialCalendarFlowAExecutionResult`.

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
- **THEN** `dry_run` is `true` in the response

### Requirement: Operator documentation

The repository MUST document that this capability:

- Is the Flow A execution connector (staged rollout step 2)
- Does not activate n8n workflows or cron
- Does not modify `calendar.json`
- Does not publish LinkedIn content directly
- Defaults to dry-run; real execution requires explicit `dry_run: false`
- Distinguishes editorial calendar planning, Flow A execution, LinkedIn distribution scheduling, and LinkedIn real publication

#### Scenario: Operator doc states dry-run first

- **WHEN** an operator reads the execution connector workflow documentation
- **THEN** it explicitly states dry-run is the default and real execution is opt-in

### Requirement: Staged rollout alignment

This change SHALL implement staged rollout step 2 only: Flow A execution connector with dry-run default.

n8n/manual trigger wiring (step 3) and LinkedIn due-publication orchestration (step 4) MUST remain out of scope.

#### Scenario: Scope limited to execution connector

- **WHEN** this change is implemented and validated
- **THEN** no code path activates n8n, cron, calendar writes, or LinkedIn real publication
