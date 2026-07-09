## 1. Planning artifacts

- [x] 1.1 Review and approve `proposal.md` — planning vs execution vs distribution vs LinkedIn publication, dry-run default, calendar immutability, explicit calendar-item model
- [x] 1.2 Review and approve `design.md` — planner-first orchestration, internal service calls, skip rules, campaign threshold, HTTP contract
- [x] 1.3 Review and approve `specs/editorial-calendar-flow-a-execution-connector/spec.md` — testable requirements and execution status vocabulary
- [x] 1.4 Run `openspec validate editorial-calendar-flow-a-execution-connector --strict` and fix any issues

## 2. Execution module

> **Implementation note (apply):** Before coding, inspect `editorial_calendar_plan.py`, `blog_publish_flow.publish_blog_post`, `linkedin_package_flow.generate_linkedin_package`, `linkedin_distribution_schedule.schedule_linkedin_distribution`, `campaign_lifecycle.py` (state constants and campaign load helpers), and `main.py` auth/request patterns. Use actual signatures; do not invent APIs. Do NOT import `linkedin_publication_flow`.

- [x] 2.1 Create `src/silverman_blog_linkedin/editorial_calendar_flow_a_execute.py` with dataclasses: `EditorialCalendarFlowAItemResult`, `EditorialCalendarFlowAExecutionResult`, execution status constants (`executed`, `skipped_existing_campaign`, `skipped_not_flow_a`, `skipped_review_required`, `failed`, dry-run `would_execute`), and `failed_step` constants (`publish_blog`, `generate_linkedin_package`, `schedule_linkedin_distribution`)
- [x] 2.2 Implement campaign skip helper: load campaign by calendar `campaign_id`; if state is `distribution_scheduled` or later, return skip decision (`skipped_existing_campaign`)
- [x] 2.3 Implement calendar `campaign_id` conflict check: after publish or package step, if calendar item had `campaign_id` and resolved step `campaign_id` differs, fail item with `calendar_campaign_id_conflict` and appropriate `failed_step`; do not call subsequent steps
- [x] 2.4 Implement eligibility evaluator per planner item (selection status, review_required, Flow A policy)
- [x] 2.5 Implement `execute_due_editorial_calendar_flow_a(base_path, *, now_utc=None, dry_run=True, limit=None)` — call `plan_editorial_calendar_due()` first; short-circuit on planner terminal statuses
- [x] 2.6 Dry-run path: build per-item decisions and aggregate `counts`; set `read_only: true`; include `planned_flow_steps` only — no downstream calls, writes, or simulated downstream success fields
- [x] 2.7 Real execution path — step 1: invoke `publish_blog_post` with resolved `source_relative_path` and calendar fields when supported; on failure set `failed` / `failed_step: publish_blog` and skip package/schedule for that item
- [x] 2.8 Real execution path — step 2: invoke `generate_linkedin_package` using publish result `campaign_id` (prefer) and `source_relative_path` (fallback); on failure set `failed` / `failed_step: generate_linkedin_package` and skip schedule for that item
- [x] 2.9 Real execution path — step 3: invoke `schedule_linkedin_distribution` using package result `campaign_id` (prefer) and `source_relative_path` (fallback); on failure set `failed` / `failed_step: schedule_linkedin_distribution`
- [x] 2.10 On full sequence success set `execution_status` `executed`; preserve downstream errors/warnings in item result without secrets or file body content
- [x] 2.11 Apply optional `limit` to eligible items in planner order
- [x] 2.12 Confirm no writes to `editorial-calendar/calendar.json`; confirm no import/call to `linkedin_publication_flow` or `publish_linkedin_due_variants`

## 3. HTTP endpoint

- [x] 3.1 Add `ExecuteEditorialCalendarFlowADueRequest` Pydantic model (`now_utc` optional, `dry_run: bool = True`, `limit` optional; `extra="forbid"`)
- [x] 3.2 Add `POST /editorial-calendar/execute-flow-a-due` in `main.py` with `Depends(require_api_key)`
- [x] 3.3 Wire route to `execute_due_editorial_calendar_flow_a()` using `load_settings().base_path`
- [x] 3.4 Serialize `EditorialCalendarFlowAExecutionResult` to JSON; response MUST NOT include secrets or file body content
- [x] 3.5 Log structured summary (status, dry_run, item counts) at info level

## 4. Tests

- [x] 4.1 Add `tests/test_editorial_calendar_flow_a_execute.py` with temp editorial base fixtures (reuse patterns from `test_editorial_calendar_plan.py`)
- [x] 4.2 Test dry-run does not call publish/package/schedule (mock/spy) and does not write metadata or calendar
- [x] 4.3 Test missing calendar → planner status propagated, no execution
- [x] 4.4 Test no due items → no execution
- [x] 4.5 Test due Flow A item dry-run → would-execute decision, `read_only: true`
- [x] 4.6 Test real execution invokes publish → package → schedule in order with mocked/stubbed services; assert package receives publish `campaign_id`/`source_relative_path` and schedule receives package `campaign_id`
- [x] 4.7 Test publish failure stops package and schedule for that item; item has `failed` and `failed_step: publish_blog`
- [x] 4.8 Test package failure stops schedule for that item; item has `failed` and `failed_step: generate_linkedin_package`
- [x] 4.9 Test schedule failure marks item failed with `failed_step: schedule_linkedin_distribution`
- [x] 4.10 Test calendar `campaign_id` conflict after publish or package (mocked) → `failed` with `calendar_campaign_id_conflict`; subsequent steps not called
- [x] 4.11 Test existing campaign at `distribution_scheduled` → `skipped_existing_campaign`
- [x] 4.12 Test `review_required: true` item → `skipped_review_required`
- [x] 4.13 Test rejected source selection → skip, no downstream calls
- [x] 4.14 Test dry-run does not include simulated downstream success fields (`campaign_id`, `source_public_url`, etc.)
- [x] 4.15 Test HTTP: auth required (401), invalid body 422, invalid `now_utc` 422, default dry-run on empty body
- [x] 4.16 Test no LinkedIn publication import/call in real execution path
- [x] 4.17 Test `calendar.json` unchanged after real execution (hash or content compare)
- [x] 4.18 Test optional `limit` caps processed items
- [x] 4.19 Run full test suite (`pytest`) and confirm existing tests still pass

## 5. Documentation

- [x] 5.1 Add `docs/workflows/editorial-calendar-flow-a-execution-connector.md` explaining: execution connector role, dry-run default, real execution opt-in, calendar immutability, no n8n/cron, no LinkedIn real publication, distinction from planning and distribution scheduling
- [x] 5.2 Document example `POST /editorial-calendar/execute-flow-a-due` dry-run and real execution curl commands
- [x] 5.3 Update staged rollout reference in `docs/workflows/editorial-calendar-orchestration.md` to point to step 2 execution connector doc (minimal cross-link only)

## 6. Verification

- [x] 6.1 Confirm no n8n workflow JSON changed; workflows remain inactive
- [x] 6.2 Confirm no cron/systemd timer added
- [x] 6.3 Confirm no calendar.json writes in any code path
- [x] 6.4 Confirm no LinkedIn publication calls
- [x] 6.5 Run `openspec validate editorial-calendar-flow-a-execution-connector --strict`
- [x] 6.6 Run `openspec validate --all --strict`
