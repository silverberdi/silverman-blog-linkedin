## Why

The archived `editorial-calendar-orchestration` capability (deployed and smoke-tested) provides a read-only planner that discovers due calendar items and returns Flow A step labels—but operators and a future orchestrator still must manually invoke `/publish-blog-post`, `/generate-linkedin-package`, and `/schedule-linkedin-distribution` for each due item. Without a safe execution connector, the editorial calendar remains intent-only and cannot drive the existing Flow A sequence in a controlled, idempotent way. This change introduces staged rollout step 2: a dry-run-first execution connector that consumes planner output and runs publish → package → schedule for eligible Flow A items while preserving `calendar.json` as editorial intent only and leaving n8n, cron, and LinkedIn real publication inactive.

## Goals

- Add `execute_due_editorial_calendar_flow_a(base_path, *, now_utc=None, dry_run=True, limit=None)` that calls the existing read-only planner, evaluates per-item execution eligibility, and either simulates or executes the Flow A sequence.
- Add API-key-protected `POST /editorial-calendar/execute-flow-a-due` with **`dry_run` defaulting to `true`**.
- In dry-run mode: plan due items, compute execution decisions, return structured JSON—no publish/package/schedule calls, no metadata writes, no public blog writes. Dry-run MAY report the planned step chain per item but MUST NOT simulate successful downstream outputs (no fabricated `campaign_id`, URLs, or schedule slots).
- In real execution mode: for eligible Flow A items with `review_required: false`, call existing internal services in strict sequence — `publish_blog_post` → `generate_linkedin_package` → `schedule_linkedin_distribution` — passing each step the resolved outputs from the previous step (not calendar-only hints alone). The publish result is the source of truth for resolved `campaign_id`, `source_public_url`, published blog path, and blog publish status; package generation consumes publish outputs when applicable; distribution scheduling consumes package outputs when applicable. Preserve downstream idempotency; never call LinkedIn real publication or `/publish-linkedin-due-variants`.
- For the first connector, use **explicit calendar-item model only**: each item resolves via `source_relative_path`; do not implement queue-slot mode or every-X-days folder cadence selection.
- Skip safely when calendar missing, no due items, source selection rejected, `review_required: true`, or existing campaign already at `distribution_scheduled` or later (when calendar `campaign_id` is present and matches metadata).
- Treat calendar `campaign_id` as a guardrail / reconciliation hint only — not authoritative over downstream publish/package outputs. If calendar `campaign_id` is present but publish or package returns a conflicting resolved campaign identity, fail that item safely with a stable error code (`calendar_campaign_id_conflict`) rather than continuing silently. Do not invent new campaign reconciliation policy beyond existing Flow A idempotency contracts.
- On real execution failure, stop the Flow A sequence for that item at the failing step: publish failure skips package and schedule; package failure skips schedule; schedule failure marks the item failed. Item results include `failed_step` when applicable (`publish_blog`, `generate_linkedin_package`, or `schedule_linkedin_distribution`) and preserve downstream errors/warnings without exposing secrets or file body content.
- Return combined operational status per item: `executed`, `skipped_existing_campaign`, `skipped_not_flow_a`, `skipped_review_required`, `failed`.
- **Do not modify `calendar.json`**; runtime evidence remains in `metadata/runs` and `metadata/campaigns`.
- Add comprehensive tests and operator documentation distinguishing planning, execution connector, distribution scheduling, and LinkedIn real publication.

## Non-Goals

- Activating n8n workflows or importing workflow JSON as active.
- Adding cron, systemd timers, or any automatic production trigger.
- Implementing queue-slot scheduling or every-X-days automatic source selection from folders.
- Modifying `calendar.json` (read-only for execution connector).
- Calling `/publish-linkedin-due-variants` or enabling `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Implementing `linkedin-article-preview-image-support`.
- Adding UI/dashboard.
- Adding reprocess mode unless required by existing idempotency contracts.
- Modifying archived OpenSpec changes.

## What Changes

- Add OpenSpec change `editorial-calendar-flow-a-execution-connector` introducing the Flow A execution connector (staged rollout step 2).
- Add worker module `editorial_calendar_flow_a_execute.py` (or equivalent) implementing `execute_due_editorial_calendar_flow_a()` with dry-run and real execution paths.
- Reuse `plan_editorial_calendar_due()` for due-item discovery; do not duplicate planning logic.
- For real execution, invoke existing internal functions from `blog_publish_flow`, `linkedin_package_flow`, and `linkedin_distribution_schedule` rather than HTTP self-calls when consistent with the codebase. Chain step inputs from prior step results per n8n Flow A orchestration conventions (publish `campaign_id`/`source_relative_path`/`source_public_url` → package; package `campaign_id` → schedule).
- Add API-key-protected `POST /editorial-calendar/execute-flow-a-due` accepting optional `now_utc`, `dry_run` (default `true`), and `limit`; reject unknown body fields with `422`.
- Implement campaign existence check: when a calendar item includes `campaign_id` and campaign metadata shows state `distribution_scheduled` or later, skip with `skipped_existing_campaign`.
- Return structured `EditorialCalendarFlowAExecutionResult` with `status`, `dry_run`, `now_utc`, `calendar_path`, `items[]`, `counts`, `errors[]`, `warnings[]`, and `read_only` (true in dry-run).
- Add `tests/test_editorial_calendar_flow_a_execute.py` covering dry-run safety, skip paths, real execution with mocked services, auth, validation, no LinkedIn publication, unchanged `calendar.json` after real execution, failure cascade (publish failure stops package/schedule; package failure stops schedule; schedule failure marks item failed), and calendar `campaign_id` conflict handling when feasible with mocked services.
- Add operator documentation (`docs/workflows/editorial-calendar-flow-a-execution-connector.md` or extend existing workflow doc) explaining dry-run-first operation, non-activation of n8n/cron, calendar immutability, and distinction from LinkedIn real publication.

No n8n activation, cron, calendar writes, LinkedIn API publication, or queue/cadence source selection are included.

## Editorial calendar planning vs Flow A execution vs distribution scheduling vs LinkedIn publication

| Layer | Capability | Artifact / endpoint | This change |
|-------|------------|---------------------|-------------|
| **Planning** | Editorial calendar orchestration (archived, deployed) | `calendar.json`; `POST /editorial-calendar/plan-due` | Consumed read-only; not modified |
| **Execution connector** | Flow A due-item execution (this change) | `POST /editorial-calendar/execute-flow-a-due` | **New** — publish → package → schedule for eligible due items |
| **Distribution scheduling** | Per-campaign variant slots (existing) | `metadata/campaigns/` → `linkedin_distribution.scheduled_at_utc`; `POST /schedule-linkedin-distribution` | Invoked internally by connector; unchanged contract |
| **LinkedIn real publication** | Optional API publish (existing, disabled) | `POST /publish-linkedin-due-variants`; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | **Not called**; remains disabled |

## Staged rollout (safe plan)

1. **Archived** — calendar artifact + read-only planner (`editorial-calendar-orchestration`).
2. **This change** — Flow A execution connector with dry-run default; explicit real execution only.
3. **Later** — n8n/manual trigger wiring calling planner then execution connector; workflows remain inactive until a separate change.
4. **Later** — LinkedIn due-publication orchestration when publication is explicitly enabled.

## Capabilities

### New Capabilities

- `editorial-calendar-flow-a-execution-connector`: Dry-run-first Flow A execution service and HTTP endpoint that consumes due editorial calendar planner output, evaluates eligibility (Flow A, review policy, existing campaign state), executes publish → generate LinkedIn package → schedule LinkedIn distribution via existing internal services when `dry_run=false`, returns structured per-item operational status and aggregate counts, preserves calendar.json immutability, and includes tests and operator documentation. No n8n, cron, calendar writes, or LinkedIn real publication.

### Modified Capabilities

<!-- No existing main spec requirements change. The execution connector consumes editorial-calendar-orchestration planning output and existing Flow A publish/package/schedule services by reference; their contracts are unchanged. -->

## Impact

- **Editorial base path**: Read-only access to `editorial-calendar/calendar.json`; **no writes** to calendar file or folder beyond existing bootstrap.
- **Worker API**: New authenticated endpoint `POST /editorial-calendar/execute-flow-a-due`; existing planning, publish, package, schedule, and publication endpoints unchanged.
- **Campaign metadata**: Written only by existing publish/package/schedule services during real execution; connector adds read-only campaign state inspection for skip logic.
- **Run metadata**: Written only during real execution via existing services.
- **Public blog repo**: Written only during real execution via existing `publish_blog_post` when not dry-run.
- **n8n**: No workflow changes; exports remain inactive.
- **Operations**: Operators can dry-run due Flow A execution safely, then opt in to real execution with `dry_run: false`; calendar remains editorial intent; evidence in `metadata/runs` and `metadata/campaigns`.
- **HTTP worker rationale**: Execution orchestration runs in the worker (not n8n Execute Command) for controlled filesystem access, path validation, idempotent service reuse, and structured JSON responses per ADR-0001.
