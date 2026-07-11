## MODIFIED Requirements

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

## ADDED Requirements

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
