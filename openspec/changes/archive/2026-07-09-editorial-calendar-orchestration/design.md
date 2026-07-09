## Context

### Current state

| Component | Editorial calendar behavior today |
|-----------|--------------------------------|
| `metadata/campaigns/` | Per-campaign lifecycle after a source post is identified and validated |
| `linkedin_distribution` | Per-campaign variant `scheduled_at_utc` after package generation (slice 6) |
| `POST /publish-blog-post` | Manual/n8n-triggered blog publish for a known `source_relative_path` |
| `POST /generate-linkedin-package` | Manual/n8n-triggered derivative generation for an existing campaign |
| `POST /schedule-linkedin-distribution` | Manual/n8n-triggered staggered variant scheduling |
| `POST /publish-linkedin-due-variants` | Optional real LinkedIn publish; disabled by env on server |
| `paths.py` | Validates `blog-posts/`, `linkedin-posts/`, `metadata/`, `prompts/` — no `editorial-calendar/` |
| n8n Flow A workflow | Exported JSON exists; **inactive** by policy |

Gaps:

- No master schedule answering *which content item should start on which date*.
- No deterministic bridge from a due date → source document selection → planned Flow A vs Flow B handoff.
- No read-only planning API for operators or a future orchestrator to inspect due work safely.

### Policy references

- ADR-0001: n8n calls worker over HTTP only; worker owns filesystem access.
- ADR-0002: Blog post is canonical; LinkedIn posts are derivatives.
- `flow-a-automatic-publishing`: Flow A automatic path vs Flow B review requirement.
- `editorial-canon`: Audience, cadence, and distribution strategy (consumed by downstream slices, not parsed at runtime in this slice).
- `flow-a-lifecycle`: Campaign states — distinct from calendar item statuses.

### Editorial calendar vs campaign scheduling

```
editorial-calendar/calendar.json          metadata/campaigns/<id>.json
        │                                          │
        │  due_at_utc: when to START               │  linkedin_distribution.scheduled_at_utc:
        │  processing a content item               │  when to PUBLISH each variant
        ▼                                          ▼
   [This change: plan only]              [Existing: schedule-linkedin-distribution]
```

## Goals / Non-Goals

**Goals:**

- Define canonical artifact `{editorial_base}/editorial-calendar/calendar.json`.
- Implement read-only `plan_editorial_calendar_due(base_path, *, now_utc=None)` returning `EditorialCalendarPlanResult`.
- Add `POST /editorial-calendar/plan-due` with API-key auth; optional `GET /editorial-calendar/status` for calendar load health.
- Support deterministic source selection: explicit `source_relative_path` OR `source_selection_mode: single_markdown_in_folder` when exactly one `.md` exists.
- Reject ambiguous folder contents with stable error codes.
- Encode Flow A vs Flow B planning policy in the execution plan (`review_required`, `planned_flow_steps`).
- Add tests and operator documentation; extend `paths.py` to expect `editorial-calendar/`.

**Non-Goals:**

- Writing or mutating `calendar.json` from the worker (operators edit manually in this slice).
- Calling publish/package/schedule/publication endpoints.
- n8n activation, cron, or automatic triggers.
- Flow B generation implementation.
- Campaign metadata writes.
- Public blog repo access.

## Decisions

### 1. Calendar artifact path

**Decision:** Store the master calendar at `editorial-calendar/calendar.json` relative to `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` (default `./data/silverman-blog-linkedin`).

**Rationale:** Aligns with existing editorial folder layout under the base path; keeps calendar co-located with `blog-posts/` and `metadata/`; operator-visible on the shared mount.

**Alternatives considered:**

- Repo-only path outside editorial base — rejected; server operators edit on the mount, not in git.
- `metadata/calendar.json` — rejected; `metadata/` is for run/campaign artifacts, not editorial planning.

### 2. Calendar item statuses (distinct from campaign lifecycle)

**Decision:** Use calendar-specific statuses:

| Status | Meaning |
|--------|---------|
| `planned` | Future item; not yet actionable |
| `scheduled` | Operator-confirmed entry waiting for `due_at_utc` |
| `due` | Explicit marker (optional); planner also treats `scheduled` items with `due_at_utc <= now_utc` as due |
| `in_progress` | Reserved for a future execution slice to set when a connector starts work |
| `completed` | Terminal success (set by future execution slice or operator) |
| `skipped` | Operator intentionally bypassed |
| `failed` | Terminal failure (set by future execution slice or operator) |

Planner in this slice only **reads** status; it includes items where `status` is `scheduled` or `due` and `due_at_utc <= now_utc`. Items in `planned` with past `due_at_utc` are reported as warnings (`calendar_item_overdue_but_planned`) but not selected.

**Rationale:** Avoid overloading campaign lifecycle states (`validated`, `distribution_scheduled`, etc.) which describe a different dimension.

### 3. Source selection rules

**Decision:** Each item MUST specify `source_folder` (relative to editorial base, e.g. `blog-posts/ready`). Document resolution:

1. If `source_relative_path` is set → use that path (must exist, be a file, end with `.md`, stay under `source_folder`).
2. Else if `source_selection_mode` is `explicit_path` → require `source_relative_path` (validation error if missing).
3. Else if `source_selection_mode` is `single_markdown_in_folder` → list `*.md` files directly in `source_folder` (non-recursive); select only if count == 1.
4. Else → `calendar_invalid_source_selection`.

Ambiguous folder (0 or >1 markdown files without explicit path) → item plan status `rejected` with `calendar_ambiguous_source_selection`.

**Rationale:** Deterministic, testable, safe for unattended future execution.

### 4. Flow type and content mode

**Decision:**

| `flow_type` | `content_mode` | Planner behavior |
|-------------|----------------|------------------|
| `flow_a_ready_blog_post` | `user_provided_approved_blog` | Plan includes `planned_flow_steps`: `validate_ready`, `publish_blog`, `generate_linkedin_package`, `schedule_linkedin_distribution` as **labels only** (not executed) |
| `flow_b_source_material` | `system_generated_source_material` | Plan includes `review_required: true`, `planned_flow_steps`: `queue_for_review` only; MUST NOT include publish steps |

Unknown `flow_type` or `content_mode` → item rejected with `calendar_invalid_flow_policy`.

**Rationale:** Preserves Flow A/B policy from umbrella spec without executing downstream endpoints.

### 5. Service module + thin HTTP route

**Decision:** Implement `editorial_calendar_plan.py` with `plan_editorial_calendar_due()`; wire `POST /editorial-calendar/plan-due` in `main.py` as a thin adapter. Optional `GET /editorial-calendar/status` returns calendar presence, schema version, item counts by status — no due planning.

**Request body (`PlanEditorialCalendarDueRequest`):**

```json
{
  "now_utc": "2026-07-09T20:00:00Z"
}
```

`now_utc` optional; defaults to worker UTC now. `extra="forbid"`.

**Response shape (`EditorialCalendarPlanResult`):**

- `status`: `completed` | `no_due_items` | `calendar_missing` | `calendar_invalid` | `partial`
- `calendar_path`, `calendar_version`, `now_utc`
- `due_items[]`: per-item plan with `item_id`, `title`, `due_at_utc`, `flow_type`, `content_mode`, `source_relative_path` (resolved), `selection_status`, `review_required`, `planned_flow_steps[]`, `errors[]`, `warnings[]`
- Top-level `errors[]`, `warnings[]`
- `read_only: true` (always)

**Rationale:** Matches slices 4–7 module-first pattern; n8n-ready JSON without side effects.

### 6. Read-only / idempotent guarantees

**Decision:** The planner MUST NOT:

- Write `calendar.json`, campaign metadata, or run metadata
- Move files between `ready` / `processed` / `error`
- Call HTTP client to other worker endpoints
- Access `SILVERMAN_GITHUB_PAGES_REPO_PATH` or public blog repo
- Call LinkedIn APIs

Repeated calls with the same `now_utc` and unchanged calendar/folders MUST return identical plans.

**Rationale:** Safe for operator dry-runs and future n8n polling without accidental publication.

### 7. Path validation and folder bootstrap

**Decision:** Extend `EXPECTED_FOLDERS` in `paths.py` with `editorial-calendar`. Planner validates `source_folder` is under allowed roots (`blog-posts/ready`, `blog-posts/processed` disallowed for *new* picks — only `blog-posts/ready` and future `source-material/` paths in allowlist). Reject path traversal (`..`, absolute paths).

**Folder vs calendar file (health semantics):**

| Artifact | Path | Required for `/health` | Notes |
|----------|------|------------------------|-------|
| Editorial calendar directory | `{editorial_base}/editorial-calendar/` | **Yes** | Missing folder → `folders_ready: false`, `status: degraded` (same as other expected folders) |
| Calendar JSON file | `{editorial_base}/editorial-calendar/calendar.json` | **No** | Missing file → `/health` unchanged; `POST /editorial-calendar/plan-due` or `GET /editorial-calendar/status` return `calendar_missing` / `calendar_file_not_found` |

**Bootstrap responsibility:** The worker does not auto-create expected folders (validate-only per foundation). Implementation MUST create or document creation of `{editorial_base}/editorial-calendar/` in:

- README local dev `mkdir` sample (alongside existing editorial tree)
- Server editorial mount setup (e.g. `/home/silverman/compartido_mac/silverman-blog-linkedin/editorial-calendar/`)
- Deployment/bootstrap scripts and docs that enumerate expected folders (e.g. `README.md`, `docs/deployment/ubuntu-server-worker-deployment.md`)

Local dev sample calendar MAY ship at `data/silverman-blog-linkedin/editorial-calendar/calendar.json`; server operators add `calendar.json` manually when ready.

**Rationale:** Consistent with existing path safety and validate-only folder policy; prevents post-rollout `/health` regression on servers that already run the worker; separates filesystem readiness (folder) from editorial planning readiness (calendar file).

### 8. Authentication

**Decision:** Both endpoints use `Depends(require_api_key)` like existing worker routes.

**Rationale:** Planning reveals editorial schedule; not public.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Rollout flips `/health` to `degraded` when `editorial-calendar/` missing on server mount | Update deployment/bootstrap scripts and docs before or with worker deploy; verify `/health` includes `editorial-calendar` after folder bootstrap |
| Operators confuse calendar due dates with LinkedIn `scheduled_at_utc` | Documentation table in proposal and `docs/workflows/editorial-calendar-orchestration.md` |
| Ambiguous ready folder blocks automation | Explicit `source_relative_path` on calendar items for production items; planner reports clear error |
| Calendar file edited while planner runs | Read-once per request; no locks needed for read-only slice |
| `in_progress` / `completed` not updated automatically | Documented as manual/future-connector responsibility |
| Stale `planned` items past due | Warning in plan output; not auto-selected |

## Migration Plan

1. **Before or with worker deploy:** Create `{editorial_base}/editorial-calendar/` on the editorial mount (server: `/home/silverman/compartido_mac/silverman-blog-linkedin/editorial-calendar/`). Update bootstrap scripts/docs so existing deployments include this folder. Confirm `GET /health` reports `editorial-calendar` with `exists` and `is_directory` true.
2. Deploy worker with new endpoints (no behavior change to existing routes).
3. Optionally add `calendar.json` manually when operators are ready (`data/silverman-blog-linkedin/editorial-calendar/calendar.json` for local dev). Absent file does not affect `/health`.
4. Operators call `POST /editorial-calendar/plan-due` to verify plans before any execution slice (`calendar_missing` until file exists).
5. Rollback: stop calling new endpoints; removing `editorial-calendar/` would re-degrade `/health` — prefer leaving the empty folder in place; no data migration required.

## Open Questions

1. Should `GET /editorial-calendar/status` be included in v1 or defer to plan-due response only? **Default: include lightweight status GET.**
2. Should calendar support recurring items? **Deferred; out of scope.**
3. When execution connector lands, who updates item status to `in_progress` / `completed` — worker or n8n? **Defer to execution slice; document both options.**
