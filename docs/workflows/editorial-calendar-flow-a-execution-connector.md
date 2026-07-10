# Editorial calendar Flow A execution connector

This workflow documents **staged rollout step 2**: the Flow A execution connector for due editorial calendar items. It chains internal worker services (publish → package → schedule) after read-only planning.

It does **not** activate n8n, cron, systemd timers, queue-slot scheduling, every-X-days source selection, or LinkedIn real publication.

## Layer distinction

| Layer | Capability | Mutates `calendar.json` | Calls LinkedIn APIs |
|-------|------------|-------------------------|---------------------|
| Planning (step 1) | `plan_editorial_calendar_due()` | No | No |
| **Execution connector (step 2)** | `execute_due_editorial_calendar_flow_a()` | **No** | **No** |
| Distribution scheduling | `schedule_linkedin_distribution()` | No (campaign metadata) | No |
| LinkedIn publication (step 4+) | `publish_linkedin_due_variants()` | No | Yes (when enabled) |

See also: [editorial-calendar-orchestration.md](./editorial-calendar-orchestration.md) (planning foundation).

## Dry-run default (safety)

- Service default: `dry_run=True`
- HTTP default: `"dry_run": true` when omitted
- Dry-run calls the planner, evaluates eligibility, returns per-item `would_execute` decisions and `planned_flow_steps`
- Dry-run performs **no** publish/package/schedule/**source lifecycle** calls and **no** metadata, run, blog repo, or calendar writes
- Dry-run does **not** fabricate downstream success fields (`campaign_id`, `source_public_url`, package IDs, schedule slots)

Run dry-run first; opt into real execution only with explicit `"dry_run": false`.

## Real execution (opt-in)

When `dry_run=false`, eligible due items run Flow A in strict order:

0. `accept_flow_a_source_for_queue` — move source from `blog-posts/ready/` to `blog-posts/queued/` (preserving filename), or resolve an already-queued campaign (`skipped_already_queued`)
1. `claim_flow_a_execution` then full editorial validation against the queued path
2. `publish_blog_post`
3. `generate_linkedin_package` (uses publish result identifiers)
4. `schedule_linkedin_distribution` (uses package result identifiers)
5. `complete_flow_a_source_lifecycle` (moves source `.md` and companion `.png` from `blog-posts/queued/` to `blog-posts/processed/` after scheduling succeeds)
6. `release_flow_a_execution` only on recoverable or failed non-terminal exits (idempotent `already_released` after terminal completion)

Dry-run reports `would_queue_accept` per item without physical moves, claims, or fabricated queue paths.

Each step uses the prior step's result object. Queue acceptance failure sets `failed_step=queue_acceptance` and stops the chain. Steps 2–4 stop on the first failure and set `failed_step` on the item. Step 5 runs only after scheduling succeeds; if source move fails, `execution_status` remains `executed` and `source_lifecycle_status` is `failed` with repair warnings (`flow_a_source_move_failed`).

### Operational folders

| Folder | Role |
|--------|------|
| `blog-posts/ready/` | Operator-approved inbox (not yet worker-accepted) |
| `blog-posts/queued/` | Worker-accepted work awaiting or undergoing Flow A execution |
| `blog-posts/processed/` | Successfully consumed sources after lifecycle completion |
| `blog-posts/error/` | Terminal deterministic failures; requeue via internal service |

`processing` is a logical `execution_state` on campaign metadata, not a physical folder.

### Recovery classifications

`source_file_status.recovery_classification` uses: `no_action`, `retryable`, `repair_required`, `requeue_required`, `manual_intervention_required`.

Stale processing is detected when `now >= last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` (default 3600, minimum 60).

### Eligibility

Real or dry-run execution applies only when the planner reports:

- `selection_status`: `selected`
- `review_required`: `false`
- `flow_type`: `flow_a_ready_blog_post`
- `content_mode`: `user_provided_approved_blog`
- Explicit `source_relative_path` resolved by the planner

### Campaign guardrails

- **Pre-skip:** calendar `campaign_id` with campaign state `flow_a_complete` → `skipped_existing_campaign`
- **Already queued:** campaigns with `source_file_status.location=queued` resume from persisted pipeline state with `queue_acceptance_status=skipped_already_queued`; the original ready file is not required
- **Post-step conflict:** calendar `campaign_id` differs from publish/package resolved `campaign_id` → `failed` with `calendar_campaign_id_conflict`; subsequent steps are not called

## HTTP endpoint

Requires API key: `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`.

### `POST /editorial-calendar/execute-flow-a-due`

**Request fields:**

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `now_utc` | string | worker UTC now | Canonical `...Z` timestamp; invalid → `422` |
| `dry_run` | boolean | `true` | Real execution requires explicit `false` |
| `limit` | integer | none | Positive cap on eligible items processed per invocation |

Extra fields are rejected (`422`).

### Dry-run example

```bash
curl -sS -X POST "http://localhost:8010/editorial-calendar/execute-flow-a-due" \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"now_utc":"2026-07-09T20:00:00Z"}' | jq .
```

### Real execution example (one item)

```bash
curl -sS -X POST "http://localhost:8010/editorial-calendar/execute-flow-a-due" \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"now_utc":"2026-07-09T20:00:00Z","dry_run":false,"limit":1}' | jq .
```

## Explicit non-activation

This capability:

- Does **not** activate n8n workflows
- Does **not** add cron or automatic triggers
- Does **not** modify `editorial-calendar/calendar.json`
- Does **not** call `publish_linkedin_due_variants` or enable `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
- Does **not** implement queue-slot or cadence-based source selection

## Staged rollout alignment

1. Planning foundation — read-only planner ([orchestration doc](./editorial-calendar-orchestration.md))
2. **This change** — Flow A execution connector with dry-run default
3. Later — n8n/manual trigger wiring (workflows remain inactive until a separate change)
4. Later — LinkedIn due-publication orchestration when explicitly enabled

## Recovery after partial failure

If publish succeeds but package or schedule fails, campaign metadata reflects partial progress via existing services. Operators recover using the standalone endpoints (`/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`) documented in their respective workflow guides.

If scheduling succeeds but source lifecycle move fails (`flow_a_source_move_failed` or `flow_a_source_move_partial`), distribution scheduling metadata is preserved. Repair source files under `blog-posts/processed/` (or restore the ready copy if needed) and retry lifecycle completion by `campaign_id` via a future operator hook or by re-running the Flow A connector when the campaign is not yet skipped as `distribution_scheduled`.

### Folder semantics after successful Flow A

| Folder | Meaning |
|--------|---------|
| `blog-posts/ready/` | Pending operator-approved input not yet consumed by successful Flow A completion |
| `blog-posts/processed/` | Source editorial files successfully consumed through scheduling and source lifecycle |
| `blog-posts/error/` | Failed input (validation/lifecycle policy) |

Campaign metadata (`metadata/campaigns/<campaign-id>.json`) is the traceability authority: `original_source_relative_path`, `processed_source_relative_path`, and optional image path fields record where files lived before and after the move. **Do not manually move processed files after successful Flow A**; use campaign metadata for audit and re-run by `campaign_id`.
