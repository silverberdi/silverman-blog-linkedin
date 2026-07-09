## Context

### Current state

| Component | Behavior today |
|-----------|----------------|
| `editorial-calendar/calendar.json` | Canonical editorial intent; deployed on server |
| `plan_editorial_calendar_due()` | Read-only due-item planner; returns Flow A step labels |
| `POST /editorial-calendar/plan-due` | API-key-protected planning endpoint; smoke-tested on server |
| `publish_blog_post()` | Internal service + `POST /publish-blog-post` |
| `generate_linkedin_package()` | Internal service + `POST /generate-linkedin-package` |
| `schedule_linkedin_distribution()` | Internal service + `POST /schedule-linkedin-distribution` |
| `publish_linkedin_due_variants()` | Internal service + HTTP endpoint; disabled on server |
| `metadata/campaigns/` | Campaign lifecycle evidence; states include `distribution_scheduled` and later |
| n8n Flow A workflow | Exported JSON exists; **inactive** by policy |

Gap: operators must manually chain publish → package → schedule for each due calendar item. The planner answers *what is due* but does not execute Flow A.

### Policy references

- ADR-0001: n8n calls worker over HTTP only; worker owns filesystem access and orchestration.
- ADR-0002: Blog post is canonical; LinkedIn posts are derivatives.
- `editorial-calendar-orchestration` (archived): Read-only planning; calendar.json is editorial intent.
- `flow-a-automatic-publishing`: Flow A sequence and idempotency contracts.
- `flow-a-lifecycle`: Campaign states — distinct from calendar item statuses.

### Layer distinction

```
calendar.json (editorial intent, read-only)
        │
        ▼
plan_editorial_calendar_due()          ← planning (archived)
        │
        ▼
execute_due_editorial_calendar_flow_a() ← execution connector (this change)
        │
        ├── publish_blog_post()
        ├── generate_linkedin_package()
        └── schedule_linkedin_distribution()
        │
        ▼
metadata/campaigns/ + metadata/runs/   ← runtime evidence
        │
        ▼
publish_linkedin_due_variants()        ← LinkedIn real publication (out of scope)
```

## Goals / Non-Goals

**Goals:**

- Implement `execute_due_editorial_calendar_flow_a(base_path, *, now_utc=None, dry_run=True, limit=None)` returning structured per-item execution results.
- Add `POST /editorial-calendar/execute-flow-a-due` with API-key auth; **`dry_run` defaults to `true`**.
- Reuse `plan_editorial_calendar_due()` — no duplicated planning logic.
- In real mode, call existing internal services in strict order: publish → package → schedule, chaining each step from the prior step's result object.
- Skip ineligible items with explicit reasons; never modify `calendar.json`.
- First connector uses explicit `source_relative_path` calendar items only (planner already resolves path).
- Preserve idempotency from downstream services; skip when campaign already `distribution_scheduled` or later.

**Non-Goals:**

- Writing or mutating `calendar.json`.
- n8n activation, cron, or automatic triggers.
- Queue-slot mode or every-X-days folder cadence source selection.
- Calling `publish_linkedin_due_variants()` or enabling LinkedIn publication env flag.
- Reprocess mode for already-scheduled campaigns.
- Flow B execution.

## Decisions

### 1. Planner-first orchestration

**Decision:** The execution connector MUST call `plan_editorial_calendar_due()` as its first step and operate only on returned `due_items`.

**Rationale:** Single source of truth for due discovery, source resolution, and Flow A/B policy; avoids drift between plan and execute.

**Alternatives considered:**

- Inline duplicate due-item logic — rejected; violates DRY and risks policy divergence.
- HTTP self-call to `/editorial-calendar/plan-due` — rejected; unnecessary overhead; direct function call matches existing worker patterns.

### 2. Internal service calls vs HTTP self-calls

**Decision:** In real execution mode, invoke `publish_blog_post`, `generate_linkedin_package`, and `schedule_linkedin_distribution` as Python functions with the same parameters the HTTP endpoints would pass.

**Rationale:** Matches how other orchestration modules compose; avoids localhost HTTP, auth duplication, and serialization overhead.

**Alternatives considered:**

- HTTP loopback to worker endpoints — rejected for complexity and test brittleness.

### 3. Dry-run default and safety contract

**Decision:** `dry_run=True` by default at service and HTTP layers. Dry-run MUST: call planner, evaluate eligibility, build per-item decisions (including planned step chain labels), return `read_only: true`, and perform zero downstream service calls and zero filesystem writes (campaigns, runs, blog repo, file moves). Dry-run MUST NOT simulate successful downstream outputs — no fabricated `campaign_id`, `source_public_url`, package IDs, or schedule slots.

**Rationale:** Operators can inspect execution intent safely before opting into real execution with `dry_run: false`.

### 4. Per-item execution status vocabulary

**Decision:** Each item in `items[]` carries `execution_status` from:

| Status | Meaning |
|--------|---------|
| `executed` | Real mode; publish → package → schedule completed (or idempotent success from downstream) |
| `skipped_existing_campaign` | `campaign_id` present; campaign state is `distribution_scheduled` or later |
| `skipped_not_flow_a` | Not Flow A eligible (wrong flow/content mode, selection rejected, etc.) |
| `skipped_review_required` | `review_required: true` from planner |
| `failed` | Real mode; a downstream step failed; `failed_step` identifies which step |

Dry-run eligible items use `execution_status` `would_execute` (or equivalent documented label) without calling services. Dry-run item results MAY include `planned_flow_steps` but MUST NOT include simulated downstream success fields (`campaign_id`, `source_public_url`, etc.) from publish/package/schedule.

**Rationale:** Stable n8n branching and operator visibility; aligns with user-requested status vocabulary.

### 5. Calendar `campaign_id` as guardrail / reconciliation hint

**Decision:** Calendar `campaign_id` is an editorial guardrail and reconciliation hint — not authoritative over downstream publish/package outputs.

- **Pre-execution skip:** When a calendar item includes `campaign_id`, load `metadata/campaigns/<campaign_id>.json` if present. If campaign `state` is in `{distribution_scheduled, distribution_complete, flow_a_complete}` (or any state at or after `distribution_scheduled` in lifecycle ordering), skip with `skipped_existing_campaign`. Do not re-run publish/package/schedule.
- **Post-step conflict:** After `publish_blog_post` or `generate_linkedin_package` returns, if the calendar item included `campaign_id` and the resolved `campaign_id` from the step result differs, fail the item with `execution_status` `failed`, `failed_step` set to the step that produced the conflict, and stable error code `calendar_campaign_id_conflict`. Do not call subsequent steps for that item.
- **No new reconciliation policy:** The connector MUST NOT invent campaign ID reassignment, calendar updates, or merge logic beyond existing Flow A idempotency contracts in downstream services.

**Rationale:** Calendar intent can drift from runtime metadata; guardrails prevent duplicate work while conflicts surface operator-visible failures instead of silent divergence.

**Alternatives considered:**

- Always re-run and rely on downstream idempotency only — rejected; wastes work and obscures operator intent.
- Update calendar item status on execution — rejected; calendar.json is editorial intent only in this change.
- Silently prefer calendar `campaign_id` over publish output — rejected; publish result is source of truth for resolved identity.

### 6. Flow A step result chaining

**Decision:** In real execution mode, invoke services in strict sequence and pass prior step outputs as inputs to the next step:

```
publish_blog_post(source_relative_path, site_url?, public_slug_override?)
        │
        ▼ BlogPublishResult (source of truth)
        │   campaign_id, source_relative_path, source_public_url, state, blog_publish
        ▼
generate_linkedin_package(campaign_id=<publish.campaign_id>,
                          source_relative_path=<publish.source_relative_path fallback>,
                          site_url?, variants?, topic_theme?)
        │
        ▼ LinkedInPackageResult
        │   campaign_id, source_relative_path, package_id, variants
        ▼
schedule_linkedin_distribution(campaign_id=<package.campaign_id>,
                               source_relative_path=<package.source_relative_path fallback>,
                               strategy?, start_at_utc?)
```

Rules:

- Prefer `campaign_id` from the immediate prior step result; fall back to `source_relative_path` from that result when `campaign_id` is absent (matches n8n Flow A orchestration spec).
- Calendar fields (`campaign_id`, `public_slug`, `site_url`, `strategy`) MAY seed initial publish/schedule inputs when present and supported by service signatures, but resolved publish/package outputs override calendar hints for subsequent steps.
- Treat step `status` of `completed` (including idempotent `already_published`-style success encoded in result) as success; any other terminal failure status stops the chain for that item.

**Rationale:** Matches deployed n8n Flow A chaining (`n8n-flow-a-blog-publish-orchestration`); prevents package/schedule from targeting stale or calendar-only identities.

### 7. Failure handling and sequence stop

**Decision:** Real execution MUST stop the Flow A sequence for an item at the first failing step:

| Failing step | Subsequent steps | Item outcome |
|--------------|-------------------|--------------|
| `publish_blog_post` | Do NOT call package or schedule | `failed`, `failed_step`: `publish_blog` |
| `generate_linkedin_package` | Do NOT call schedule | `failed`, `failed_step`: `generate_linkedin_package` |
| `schedule_linkedin_distribution` | — | `failed`, `failed_step`: `schedule_linkedin_distribution` |

Each failed item result MUST:

- Set `execution_status` to `failed`
- Include `failed_step` with one of: `publish_blog`, `generate_linkedin_package`, `schedule_linkedin_distribution`
- Copy downstream `errors[]` and `warnings[]` from the failing step result (stable codes/messages only)
- Omit secrets, tokens, and file body content from item or aggregate responses

Partial success state from an earlier step (e.g., blog published before package failure) remains in `metadata/campaigns` via existing services; the connector documents recovery via existing standalone endpoints.

**Rationale:** Prevents orphaned schedule calls against unpublished or unpackaged campaigns; gives operators actionable per-item failure attribution.

### 8. Explicit calendar-item model only

**Decision:** Execute only items where planner `selection_status` is `selected` with resolved `source_relative_path`. Do not add queue-slot or cadence-based source selection in this connector.

**Rationale:** User decision for first connector; planner already supports explicit path; queue/cadence deferred to future change.

### 9. Optional `limit` parameter

**Decision:** Accept optional `limit` (positive integer) to process at most N eligible due items per invocation, in planner order.

**Rationale:** Safe incremental rollout on server; operator can execute one item at a time.

### 10. Calendar immutability

**Decision:** The connector MUST NOT read-write `calendar.json`. No calendar item status updates from execution.

**Rationale:** Editorial calendar remains human-edited intent; runtime evidence lives in `metadata/runs` and `metadata/campaigns`.

### 11. HTTP endpoint contract

**Decision:** Add `ExecuteEditorialCalendarFlowADueRequest` Pydantic model:

- `now_utc: str | None = None`
- `dry_run: bool = True`
- `limit: int | None = None`
- `extra="forbid"`

Route: `POST /editorial-calendar/execute-flow-a-due` with `Depends(require_api_key)`.

Response: `EditorialCalendarFlowAExecutionResult.to_dict()` with aggregate `status`, `counts` object, and `items[]`.

**Rationale:** Consistent with existing editorial calendar endpoints and auth pattern.

### 12. Module placement

**Decision:** New module `editorial_calendar_flow_a_execute.py` colocated with `editorial_calendar_plan.py`.

**Rationale:** Clear separation: plan vs execute; easy testing and imports.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Partial failure mid-sequence (publish ok, package fails) | Stop chain at failing step; return `failed` with `failed_step`; preserve downstream errors/warnings; operator recovery via existing endpoints |
| Calendar `campaign_id` mismatch vs publish/package output | Fail item with `calendar_campaign_id_conflict`; do not call subsequent steps |
| Calendar `campaign_id` present but campaign already scheduled | Pre-execution skip with `skipped_existing_campaign` |
| Operator runs real execution without dry-run first | Default `dry_run=true`; document dry-run-first in operator doc |
| Accidental LinkedIn publication | Connector MUST NOT import or call `linkedin_publication_flow`; tests assert no publication call |

## Migration Plan

1. Implement module and endpoint behind existing API key auth.
2. Deploy worker image to Ubuntu server (same Docker pattern as editorial-calendar-orchestration).
3. Operator dry-run: `POST /editorial-calendar/execute-flow-a-due` with default body or explicit `"dry_run": true`.
4. Operator real execution: explicit `"dry_run": false` (and optional `limit`) when satisfied with dry-run output.
5. Rollback: revert worker image; no calendar or campaign schema migration required.

## Open Questions

- None blocking implementation. Queue-slot and cadence modes explicitly deferred.
