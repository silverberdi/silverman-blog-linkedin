# Editorial calendar orchestration (planning foundation)

This workflow documents **staged rollout step 1 only**: the read-only editorial calendar planner. It does **not** activate n8n, cron, systemd timers, or automatic publish/package/schedule/LinkedIn publication.

## Calendar vs campaign scheduling

| Dimension | Editorial calendar (this slice) | Campaign LinkedIn distribution (existing) |
|-----------|--------------------------------|-------------------------------------------|
| Artifact | `editorial-calendar/calendar.json` | `metadata/campaigns/<id>.json` → `linkedin_distribution` |
| Question | When should editorial **processing start** for a content item? | When should each LinkedIn **variant publish** within a campaign? |
| Timestamp field | `due_at_utc` on calendar items | `scheduled_at_utc` per variant after package generation |
| This slice | Read-only plan only | Unchanged |

## Folder bootstrap vs `calendar.json`

| Artifact | Path | Required for `/health` |
|----------|------|------------------------|
| Editorial calendar directory | `{editorial_base}/editorial-calendar/` | **Yes** — missing folder degrades health like other expected folders |
| Calendar JSON file | `{editorial_base}/editorial-calendar/calendar.json` | **No** — absence does not affect `/health` |

Versioned example: `docs/examples/editorial-calendar/calendar.example.json`

Copy to runtime path when ready (optional for `/health`):

```bash
cp docs/examples/editorial-calendar/calendar.example.json \
   data/silverman-blog-linkedin/editorial-calendar/calendar.json
```

Runtime path remains `{editorial_base}/editorial-calendar/calendar.json`.

Server mount folder (create before worker rollout):

```bash
mkdir -p /home/silverman/compartido_mac/silverman-blog-linkedin/editorial-calendar
```

Container path: `/data/silverman-blog-linkedin/editorial-calendar/`

Until `calendar.json` exists, planning endpoints return `status: calendar_missing` with error code `calendar_file_not_found`.

## Flow A vs Flow B planning policy

The planner returns **labels only** — no downstream HTTP calls.

| `flow_type` | `content_mode` | `review_required` | `planned_flow_steps` |
|-------------|----------------|-------------------|----------------------|
| `flow_a_ready_blog_post` | `user_provided_approved_blog` | `false` | `validate_ready`, `publish_blog`, `generate_linkedin_package`, `schedule_linkedin_distribution` |
| `flow_b_source_material` (or any) | `system_generated_source_material` | `true` | `queue_for_review` only |

System-generated content plans MUST NOT include publish, package, or distribution step labels.

## HTTP endpoints

Both require API key: `Authorization: Bearer <SILVERMAN_BLOG_LINKEDIN_API_KEY>`.

### `POST /editorial-calendar/plan-due`

Find due items (`status` `scheduled` or `due` with `due_at_utc <= now_utc`), resolve source documents, and return an execution plan.

**Request:**

```json
{
  "now_utc": "2026-07-09T20:00:00Z"
}
```

`now_utc` is optional (defaults to worker UTC now). Extra fields are rejected (`422`).

**Example response (one due Flow A item):**

```json
{
  "status": "completed",
  "calendar_path": "/data/silverman-blog-linkedin/editorial-calendar/calendar.json",
  "calendar_version": "1",
  "now_utc": "2026-07-09T20:00:00Z",
  "due_items": [
    {
      "item_id": "sample-scheduled-flow-a",
      "title": "Why I did not start with the database",
      "due_at_utc": "2026-07-01T14:00:00Z",
      "flow_type": "flow_a_ready_blog_post",
      "content_mode": "user_provided_approved_blog",
      "source_relative_path": "blog-posts/ready/01-why-i-did-not-start-with-the-database.md",
      "selection_status": "selected",
      "review_required": false,
      "planned_flow_steps": [
        "validate_ready",
        "publish_blog",
        "generate_linkedin_package",
        "schedule_linkedin_distribution"
      ],
      "errors": [],
      "warnings": []
    }
  ],
  "errors": [],
  "warnings": [],
  "read_only": true
}
```

**Other top-level `status` values:** `no_due_items`, `calendar_missing`, `calendar_invalid`, `partial`.

### `GET /editorial-calendar/status`

Calendar presence and item counts by status — no due-item planning.

**Example (calendar present):**

```json
{
  "status": "ok",
  "calendar_path": "/data/silverman-blog-linkedin/editorial-calendar/calendar.json",
  "calendar_present": true,
  "schema_version": "1",
  "item_counts_by_status": {
    "planned": 1,
    "scheduled": 1,
    "due": 0,
    "in_progress": 0,
    "completed": 0,
    "skipped": 0,
    "failed": 0
  },
  "errors": [],
  "read_only": true
}
```

## Explicit non-activation

This capability:

- Does **not** activate n8n workflows (exports remain inactive)
- Does **not** add cron or automatic production triggers
- Does **not** call `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, or `/publish-linkedin-due-variants`
- Does **not** enable LinkedIn real publication
- Does **not** modify the public blog repository or campaign metadata

## Staged rollout

1. Planning foundation — read-only planner (this document)
2. **Flow A execution connector** — [editorial-calendar-flow-a-execution-connector.md](./editorial-calendar-flow-a-execution-connector.md) (dry-run default; publish → package → schedule)
3. **Later** — n8n/manual trigger wiring (workflows still inactive until a separate change)
4. **Later** — LinkedIn due-publication orchestration when explicitly enabled

## Operator dry-run

```bash
curl -sS -X POST "http://localhost:8010/editorial-calendar/plan-due" \
  -H "Authorization: Bearer $SILVERMAN_BLOG_LINKEDIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"now_utc":"2026-07-09T20:00:00Z"}' | jq .
```

Verify `/health` reports `editorial-calendar` with `exists` and `is_directory` true after folder bootstrap, even when `calendar.json` is absent.

## Completed item exclusion

Items with `status=completed` are excluded from due planning **before** source existence validation. They are not selected, do not invoke `resolve_source_document`, and do not produce `calendar_source_not_found`.

Terminal `status=completed` is written by the Flow A execution connector after campaign `flow_a_complete` and processed source lifecycle, or via authoritative `campaign_id` reconciliation when the campaign is already complete. The planner remains read-only.
