## 1. Planning artifacts

- [x] 1.1 Review and approve `proposal.md` — calendar vs campaign scheduling, Flow A/B policy, staged rollout, goals and non-goals
- [x] 1.2 Review and approve `design.md` — calendar path, statuses, source selection, read-only planner, HTTP contract
- [x] 1.3 Review and approve `specs/editorial-calendar-orchestration/spec.md` — testable requirements and error codes
- [x] 1.4 Run `openspec validate editorial-calendar-orchestration --strict` and fix any issues

## 2. Editorial calendar plan module

> **Implementation note (apply):** Before coding, inspect `paths.py`, `campaign_lifecycle.py` (Flow A/B constants only — no writes), `main.py` auth pattern, and existing dataclass/result patterns in `linkedin_distribution_schedule.py`. Use actual signatures; do not invent APIs.

- [x] 2.1 Create `src/silverman_blog_linkedin/editorial_calendar_plan.py` with `EditorialCalendarPlanResult` dataclass and stable error code constants (`calendar_file_not_found`, `calendar_schema_invalid`, `calendar_ambiguous_source_selection`, `calendar_invalid_flow_policy`, `calendar_item_overdue_but_planned`, etc.)
- [x] 2.2 Define calendar constants: allowed statuses, `flow_type` / `content_mode` pairs, `source_selection_mode` values, `CALENDAR_RELATIVE_PATH = "editorial-calendar/calendar.json"`
- [x] 2.3 Implement `load_calendar(base_path)` with JSON parse and schema validation (required top-level fields, per-item required fields, unique `item_id`)
- [x] 2.4 Implement `find_due_items(calendar, now_utc)` selecting `scheduled`/`due` items with `due_at_utc <= now_utc`; emit warnings for overdue `planned` items
- [x] 2.5 Implement path safety helpers: reject traversal, validate `source_folder` allowlist (`blog-posts/ready` minimum), verify `.md` extension
- [x] 2.6 Implement `resolve_source_document(base_path, item)` — explicit path and `single_markdown_in_folder` modes; ambiguous → `calendar_ambiguous_source_selection`
- [x] 2.7 Implement `build_item_plan(item, resolved_source)` — `review_required`, `planned_flow_steps` labels per Flow A/B policy; no execution
- [x] 2.8 Implement `plan_editorial_calendar_due(base_path, *, now_utc=None)` orchestrating load → due discovery → source resolution → plan assembly; set `read_only: true` always
- [x] 2.9 Confirm no imports or calls to `blog_publish_flow`, `linkedin_package_flow`, `linkedin_distribution_schedule`, `linkedin_publication_flow`, or git/public-blog modules
- [x] 2.10 Confirm no filesystem writes (calendar, campaigns, runs, file moves)

## 3. Paths, folder bootstrap, and sample artifact

- [x] 3.1 Add `editorial-calendar` to `EXPECTED_FOLDERS` in `paths.py`
- [x] 3.2 Ensure `{editorial_base}/editorial-calendar/` is created or documented for local dev and server mounts (folder required for `/health`; `calendar.json` optional for `/health`)
- [x] 3.3 Add sample `data/silverman-blog-linkedin/editorial-calendar/calendar.json` for local dev (one future `planned` item, one `scheduled` Flow A example with explicit `source_relative_path`)
- [x] 3.4 Update `README.md` folder layout section and local dev `mkdir` sample to include `editorial-calendar/` (minimal pointer only)

## 3b. Deployment and bootstrap scripts

> **Operational note:** Adding `editorial-calendar` to `EXPECTED_FOLDERS` makes the folder part of `/health` readiness. Existing server deployments MUST have `{editorial_base}/editorial-calendar/` before or when the new worker image rolls out, or `/health` will report `degraded`.

- [x] 3b.1 Update deployment/bootstrap paths that enumerate or create expected editorial folders to include `editorial-calendar/` (e.g. `README.md` `mkdir` command, `docs/deployment/ubuntu-server-worker-deployment.md` troubleshooting/layout references)
- [x] 3b.2 Document server mount path for the folder: `/home/silverman/compartido_mac/silverman-blog-linkedin/editorial-calendar/` (container: `/data/silverman-blog-linkedin/editorial-calendar/`)
- [x] 3b.3 Verify post-bootstrap `GET /health` includes `editorial-calendar` with `exists` and `is_directory` true on a layout that omits `calendar.json`

## 4. HTTP endpoints

- [x] 4.1 Add `PlanEditorialCalendarDueRequest` Pydantic model (`now_utc` optional; `extra="forbid"`)
- [x] 4.2 Add `POST /editorial-calendar/plan-due` in `main.py` with `Depends(require_api_key)`
- [x] 4.3 Add optional `GET /editorial-calendar/status` with `Depends(require_api_key)` returning calendar presence, `schema_version`, item counts by status
- [x] 4.4 Wire routes to `plan_editorial_calendar_due()` and calendar load helpers using `load_settings()`
- [x] 4.5 Serialize `EditorialCalendarPlanResult` to JSON; response MUST NOT include secrets or file body content

## 5. Tests

- [x] 5.1 Add `tests/test_editorial_calendar_plan.py` with temp editorial base fixtures (`editorial-calendar/`, `blog-posts/ready/`)
- [x] 5.2 Test missing calendar → `calendar_missing` / `calendar_file_not_found`
- [x] 5.3 Test invalid calendar shape → `calendar_invalid` / `calendar_schema_invalid`
- [x] 5.4 Test no due items for supplied `now_utc`
- [x] 5.5 Test one due Flow A `user_provided_approved_blog` item with explicit path → selected plan with Flow A step labels, `review_required` false
- [x] 5.6 Test future item (`due_at_utc > now_utc`) not in `due_items`
- [x] 5.7 Test ambiguous folder (`single_markdown_in_folder` with 0 or 2+ files) → `calendar_ambiguous_source_selection`
- [x] 5.8 Test `system_generated_source_material` → `review_required` true, no publish steps
- [x] 5.9 Test idempotent read-only: double call identical; assert no metadata/calendar/file changes
- [x] 5.10 Add HTTP endpoint tests: auth required, 401 without key, 200 shape, invalid body 422
- [x] 5.11 Update `tests/test_paths.py` and `tests/test_health.py`: `editorial-calendar` in `EXPECTED_FOLDERS`; health reports folder after full layout bootstrap
- [x] 5.12 Test `/health` remains `healthy` when `editorial-calendar/` exists but `calendar.json` is absent (folder present, file optional for health)
- [x] 5.13 Test missing `editorial-calendar/` folder degrades health (`folders_ready: false`) consistent with existing folder validation
- [x] 5.14 Test `POST /editorial-calendar/plan-due` and/or `GET /editorial-calendar/status` return `calendar_missing` when folder exists but `calendar.json` is absent
- [x] 5.15 Run full test suite (`pytest`) and confirm existing tests still pass

## 6. Documentation

- [x] 6.1 Add `docs/workflows/editorial-calendar-orchestration.md` explaining calendar vs campaign scheduling, Flow A/B planning policy, folder bootstrap vs `calendar.json` health semantics, staged rollout steps 1–4, and explicit non-activation of n8n/cron/auto-publish
- [x] 6.2 Document example `POST /editorial-calendar/plan-due` request/response for operators

## 7. Verification

- [x] 7.1 Confirm no n8n workflow JSON changed; workflows remain inactive
- [x] 7.2 Confirm no cron/systemd timer added
- [x] 7.3 Confirm no automatic calls to publish/package/schedule/LinkedIn publication endpoints
- [x] 7.4 Run `openspec validate editorial-calendar-orchestration --strict`
- [x] 7.5 Run `openspec validate --all --strict`
