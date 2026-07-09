## Why

Flow A already supports blog publication, derivative package generation, per-campaign LinkedIn distribution scheduling, and optional real LinkedIn publication—but all of these are triggered ad hoc per campaign. Campaign-level scheduling metadata (`metadata/campaigns/`, `linkedin_distribution.scheduled_at_utc`) answers *when to publish each LinkedIn variant within a single campaign*, not *when the editorial pipeline should start for the next piece of content*. Without a master editorial calendar, there is no deterministic, operator-visible plan for which source document to process on which date, which flow applies (user-approved ready blog vs system-generated source material), or how due items should be handed off to downstream endpoints. This change introduces the first read-only editorial calendar planning layer so a future execution slice can safely connect due Flow A items to publish/package/schedule without activating n8n, cron, or automatic publication.

## Goals

- Define a canonical editorial calendar artifact at `{editorial_base}/editorial-calendar/calendar.json`.
- Model calendar items with required fields (`item_id`, `title`, `status`, `due_at_utc`, `source_folder`, selection mode, `flow_type`, `content_mode`, `target_audience`, `topic_theme`) and optional fields (`public_slug`, `site_url`, `campaign_id`, `strategy`, `notes`).
- Provide a read-only planning service that loads and validates the calendar, finds due items for a supplied `now_utc`, inspects source folders, selects a document only when deterministic and safe, and returns an execution plan without side effects.
- Expose an API-key-protected HTTP endpoint (for example `POST /editorial-calendar/plan-due`) returning structured JSON suitable for n8n branching in a later slice.
- Preserve Flow A vs Flow B policy: `user_provided_approved_blog` may be planned for automatic Flow A execution later; `system_generated_source_material` MUST be planned for review, not direct publish.
- Add comprehensive tests and operator documentation stating this slice does not activate automation.

## Non-Goals

- Activating n8n workflows or importing workflow JSON as active.
- Adding cron, systemd timers, or any automatic production trigger.
- Calling `/publish-blog-post`, `/generate-linkedin-package`, `/schedule-linkedin-distribution`, or `/publish-linkedin-due-variants`.
- Enabling LinkedIn real publication (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` remains off).
- Implementing LinkedIn article preview image support.
- Modifying the public blog repository or publishing real content.
- Implementing Flow B generation/review workflows.
- Changing archived OpenSpec changes.
- Committing or pushing repository changes as part of this proposal.

## What Changes

- Add OpenSpec change `editorial-calendar-orchestration` introducing the first master editorial calendar capability.
- Define `editorial-calendar/calendar.json` schema, allowed item statuses, and source-selection rules under the editorial base path (`SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, default `./data/silverman-blog-linkedin`).
- Add worker module `editorial_calendar_plan.py` (or equivalent) implementing read-only calendar load, validation, due-item discovery, folder inspection, deterministic document selection, and execution-plan assembly.
- Add API-key-protected `POST /editorial-calendar/plan-due` (optional read-only `GET /editorial-calendar/status` if useful for health/diagnostics) in `main.py`.
- Extend `paths.py` expected folders to include `editorial-calendar/` (read-only for planning; no writes in this slice).
- Ensure deployment and bootstrap paths create `{editorial_base}/editorial-calendar/` before rollout so existing server deployments remain healthy after the change (folder required for `/health`; `calendar.json` optional for `/health`).
- Add `tests/test_editorial_calendar_plan.py` covering empty/missing calendar, invalid shape, no due items, one due Flow A item, future items excluded, ambiguous selection rejected, generated-content review requirement, and idempotent read-only behavior.
- Add operator documentation (`docs/workflows/editorial-calendar-orchestration.md` or equivalent) explaining calendar vs campaign scheduling, staged rollout, and explicit non-activation of automation.

No n8n exports, cron, downstream endpoint calls, public blog writes, or LinkedIn API calls are included.

## Editorial calendar vs LinkedIn distribution scheduling

| Dimension | Editorial calendar (this change) | Campaign LinkedIn distribution scheduling (existing) |
|-----------|----------------------------------|-----------------------------------------------------|
| Scope | Master plan across content items | Per-campaign variant publish slots |
| Artifact | `editorial-calendar/calendar.json` | `metadata/campaigns/<id>.json` → `linkedin_distribution` |
| Question answered | *What content should start processing and when?* | *When should each LinkedIn variant go live?* |
| Trigger input | `due_at_utc` on calendar items | `scheduled_at_utc` per variant after package generation |
| This slice | Read-only plan only | Unchanged |

## Flow A vs Flow B policy (preserved)

- **`flow_type: flow_a_ready_blog_post`** with **`content_mode: user_provided_approved_blog`**: eligible for a future automatic execution connector (publish → package → schedule). This slice only plans the handoff; it does not execute.
- **`content_mode: system_generated_source_material`** (Flow B path): plan MUST mark the item as requiring human review/approval before any publish endpoint may be called. Planner returns `review_required: true` and MUST NOT emit a direct-publish execution step.

## Staged rollout (safe plan)

1. **This change** — calendar artifact + validation + read-only due-item planner/endpoint.
2. **Later execution connector** — connect due Flow A items to `/publish-blog-post` → image → `/generate-linkedin-package` → `/schedule-linkedin-distribution` with idempotency and campaign linkage.
3. **Later n8n/manual trigger** — operator or n8n calls planner then execution connector; workflows remain inactive until explicitly activated in a separate change.
4. **Later LinkedIn due-publication orchestration** — connect scheduled variants to `/publish-linkedin-due-variants` only when publication is explicitly enabled.

## Capabilities

### New Capabilities

- `editorial-calendar-orchestration`: Canonical editorial calendar artifact, item schema and statuses, read-only due-item planning service, deterministic source-folder selection rules, Flow A vs Flow B planning policy, API-key-protected planning endpoint(s), stable error codes, structured execution-plan response, tests, and operator documentation. No side effects on blog repo, campaign metadata, or LinkedIn.

### Modified Capabilities

<!-- No existing main spec requirements change. Calendar planning is a new upstream layer; campaign lifecycle, distribution scheduling, and publication specs are consumed by reference only. -->

## Impact

- **Editorial base path**: New folder `editorial-calendar/` under `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` (`{editorial_base}/editorial-calendar/`). The folder MUST exist for `/health` folder readiness; `calendar.json` inside it MAY be absent without affecting `/health`. Local dev sample may live at `data/silverman-blog-linkedin/editorial-calendar/calendar.json`.
- **Deployment / bootstrap**: README local `mkdir` guidance, server editorial mount setup, and any deployment scripts that create expected folders MUST include `editorial-calendar/` so rollouts do not flip `/health` to `degraded` on existing servers. Operators add `calendar.json` manually when ready; until then, `POST /editorial-calendar/plan-due` or `GET /editorial-calendar/status` report `calendar_missing`.
- **Worker API**: New authenticated planning endpoint(s); no changes to existing publish/package/schedule/publication contracts.
- **Campaign metadata**: Read-only inspection only when `campaign_id` is present on a calendar item; no writes.
- **n8n**: No workflow changes; exports remain inactive.
- **Operations**: Operators gain a visible master schedule and a dry-run planning API; no cron or automatic triggers.
- **Future slices**: Execution connector, n8n orchestration, and LinkedIn due-publication depend on this planning contract.
- **HTTP worker rationale**: Planning logic runs in the worker (not n8n Execute Command) for controlled filesystem access, path validation, and structured JSON responses per ADR-0001.
