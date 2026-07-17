# Flow A Operational Alerts (US-028 / US-029 / US-030)

Operator contract for BL-011 alert evaluation, optional fail-closed webhook
emission, and authenticated orchestration-failure report ingest.

- **US-028:** `item_moved_to_error`, `image_generation_failure`,
  `blog_publication_failure`
- **US-029:** `partial_calendar_execution`,
  `linkedin_token_or_publication_failure`, `stale_campaign`
- **US-030:** `unhealthy_worker`, `failed_n8n_workflow`

This capability does **not** replace the observation endpoint, does not add
BL-015 UI, and does not embed Slack/email SDKs. US-028, US-029, and US-030 were
operator-accepted and **BL-011 closed 2026-07-17** after deploy + controlled live
smoke on `BUILD_REVISION=b67c538`. **Production webhook + n8n Error Trigger
wiring enabled 2026-07-17** (see Emission and n8n wiring below).

## Relationship to operational status and health

| Surface | Role |
|---------|------|
| `GET /flow-a/operational-status` | Read-only observation (US-026 / US-027). Never notifies, never writes alert ledgers or orchestration-failure evidence. |
| `GET /health` | Process-reachable editorial-folder readiness (`folders_ready`). Unauthenticated. |
| `POST /flow-a/operational-alerts/evaluate` | US-028 + US-029 + US-030 alert typing, safe payloads, optional webhook emission + emission ledger. |
| `POST /flow-a/operational-alerts/report-orchestration-failure` | Authenticated ingest of secret-safe n8n failure evidence (US-030 only). |

US-028/US-029 evaluation reuses operational-status classifications and dependency
buckets. It does not ad-hoc rescan raw editorial folders as a parallel source of
truth for those types and does not call ComfyUI, DeepSeek, LinkedIn, Git, or
live-site APIs.

US-030 `unhealthy_worker` uses the **same in-process** `validate_folders` path as
`GET /health` (no HTTP loopback to `/health`). Process-down / unreachable worker
is outside this contract (n8n health-check failure). Deploy-revision /
`BUILD_REVISION` mismatch alerts are not produced.

US-030 `failed_n8n_workflow` is derived **only** from the
orchestration-failures store populated by the report endpoint — not from failed
`metadata/runs/*` alone.

## Evaluate request

`POST /flow-a/operational-alerts/evaluate` requires the worker Bearer API key.
JSON body (`extra` forbidden):

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `now_utc` | no | current UTC | Canonical `YYYY-MM-DDTHH:MM:SSZ`; invalid → HTTP 422 |
| `emit` | no | `false` | When false, evaluate only — no webhook, no ledger write |

Example (evaluate only):

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${SILVERMAN_BLOG_LINKEDIN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"now_utc":"2026-07-17T12:00:00Z","emit":false}' \
  "http://localhost:8010/flow-a/operational-alerts/evaluate"
```

Missing API key → HTTP 401 (no evaluation side effects).

## Evaluate response

- `status`: mirrored from underlying operational-status evidence (`ok` / `partial`)
- `observed_at_utc`: one request-level observation instant
- `alerts`: deterministic list ordered by `alert_type` then `fingerprint`
- `summary.counts`: integers for all **eight** alert types plus `summary.total`
- `data_issues`: safe issues from the status aggregation when evidence is partial
- `emission`: whether emit was requested and what happened

Each alert includes `alert_type`, `severity` (`error` or `warning`),
`fingerprint`, `observed_at_utc`, short `summary`, and safe identifiers
(`campaign_id` and/or `run_id`; `calendar_item_id` for partial-calendar alerts;
`workflow_id` and optional `execution_id` for failed-n8n alerts).
Dependency-derived alerts also include `dependency` and sorted validated
`error_codes`.

Payloads never include Markdown/draft bodies, API keys, tokens, webhook URLs,
authorization values, raw provider/n8n bodies, the absolute editorial base path,
or calendar free-text titles.

## Report orchestration failure (US-030)

`POST /flow-a/operational-alerts/report-orchestration-failure` requires the
worker Bearer API key. JSON body (`extra` forbidden):

| Field | Required | Notes |
|-------|----------|-------|
| `workflow_id` | yes | Non-empty safe opaque token |
| `reason_code` | yes | Allowlisted: `n8n_workflow_failed`, `n8n_http_node_failed`, `n8n_error_trigger` |
| `observed_at_utc` | no | Canonical UTC; default request-time UTC |
| `execution_id` | no | Safe opaque token when present |
| `node_name` | no | Short safe label when present |
| `campaign_id` / `run_id` | no | Only when already known and valid-shaped |

Example:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${SILVERMAN_BLOG_LINKEDIN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"workflow_id":"silvermanFlowAPublish01","reason_code":"n8n_workflow_failed","execution_id":"exec-123","observed_at_utc":"2026-07-17T12:00:00Z"}' \
  "http://localhost:8010/flow-a/operational-alerts/report-orchestration-failure"
```

On success: HTTP 200 with `fingerprint`, identifiers, and `created` (`true` on
first write; `false` when the identical fingerprint already exists). Writes only
`metadata/operational-alerts/orchestration-failures.json`. Does **not** write the
emissions ledger, call webhooks, or mutate campaign/run/calendar/editorial
lifecycle. Missing API key → HTTP 401. Unknown `reason_code` / invalid UTC →
HTTP 422.

n8n Error Trigger / catch wiring to this endpoint is an optional later ops step —
not required for implementation completeness (tests use controlled fixtures /
direct report calls).

## US-028 alert types

| `alert_type` | Severity | Evidence rule |
|--------------|----------|---------------|
| `item_moved_to_error` | `error` | Failed Flow A campaign with `source_file_status.location=error` (or equivalent `source_location_error` health reason) |
| `image_generation_failure` | `error` | Dependency bucket `comfyui` (`comfyui_*` / `blog_image_generation_*`) on a campaign or failed run |
| `blog_publication_failure` | `error` | `github_pages_checkout` attributions whose codes match `blog_publish_*` or `blog_git_publication_*` only |

LinkedIn-preview checkout codes (`linkedin_preview_validation_checkout_*`,
`linkedin_article_preview_public_repo_not_configured`) do **not** produce
`blog_publication_failure`.

## US-029 alert types

| `alert_type` | Severity | Evidence rule |
|--------------|----------|---------------|
| `partial_calendar_execution` | `warning` | Each operational-status `delayed_calendar_items` entry (past-due non-terminal; reason `calendar_item_past_due`); one alert per `item_id`; includes `calendar_item_id`; omits calendar title |
| `linkedin_token_or_publication_failure` | `error` | Union of `linkedin` dependency-bucket attributions and campaign LinkedIn progress `failure_codes` (merged, sorted, unique) on a campaign or failed run; `dependency=linkedin` |
| `stale_campaign` | `warning` | Flow A campaign with `stale=true`; one alert per `campaign_id`; stale-related `health_reasons` as `error_codes` when present |

LinkedIn-preview checkout codes under `github_pages_checkout` do **not** produce
`linkedin_token_or_publication_failure`.

US-028/US-029 fingerprint form:
`{alert_type}:{campaign_id|run_id|calendar_item_id}:{primary_error_code|none}`.

## US-030 alert types

| `alert_type` | Severity | Evidence rule |
|--------------|----------|---------------|
| `unhealthy_worker` | `error` | In-process `validate_folders` reports `folders_ready=false`; one alert for the current not-ready folder set; `error_codes` like `editorial_folder_not_ready:<folder>` (sorted) |
| `failed_n8n_workflow` | `error` | One alert per open orchestration-failure fingerprint; includes `workflow_id`, reported `reason_code`, optional `execution_id` |

Fingerprints:

- `unhealthy_worker:folders_not_ready:{comma-sorted-not-ready-folder-names}`
- `failed_n8n_workflow:{workflow_id}:{reason_code}:{execution_id|none}`

## Emission (optional, fail-closed)

| Env | Role | Default |
|-----|------|---------|
| `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` | Master switch | off / false |
| `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_WEBHOOK_URL` | Generic http(s) webhook target | unset |

When `emit=false` (default): `emission.status=not_requested`; no webhook; no
ledger I/O; no orchestration-failure write.

When `emit=true`:

- disabled → `emission.status=disabled` (HTTP 200; alerts still returned)
- enabled but webhook unset/invalid → `emission.status=misconfigured`
- enabled and configured → POST secret-safe `{observed_at_utc, alert}` JSON to
  the webhook for fingerprints not already recorded; ledger updated only after
  HTTP 2xx

MVP channel is a **generic HTTP webhook**. The worker does not embed Slack,
email, or UI SDKs. n8n (or another operator client) may map evaluate JSON or
webhook payloads to any downstream channel outside this contract. Webhook
consumers must accept both `error` and `warning` severities.

### Live enablement on `192.168.0.194` (2026-07-17)

| Item | Value |
|------|-------|
| Enabled | `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED=true` |
| Webhook URL | `http://n8n:5678/webhook/silverman-flow-a-operational-alerts` |
| Why internal DNS | Public gateway `192.168.0.194:5678/webhook/*` requires `X-Avatares-Api-Key`; worker emit client has no custom headers |
| Compose | Worker joins external network `local-ai-stack_backend` |
| Receiver workflow | `silvermanFlowAAlertsWebhook01` (path `silverman-flow-a-operational-alerts`) |
| Error report workflow | `silvermanFlowAErrorReport01` — Flow A `settings.errorWorkflow` |
| Evaluate/emit schedule | `silvermanFlowAAlertsEvaluate01` — cron `30 9 * * *` UTC + Manual |
| Enable script | `deploy/server/enable-flow-a-operational-alerts-n8n.sh` |

Controlled enablement smoke: internal webhook probe HTTP 200; evaluate
`emit=true` → `emission.status=emitted` for live US-028 fingerprints; report
ingest with `n8n_error_trigger` accepted then smoke entry removed.

## Persistence under `metadata/operational-alerts/`

| File | Written by | Purpose |
|------|------------|---------|
| `emissions.json` | evaluate with `emit=true` after HTTP 2xx only | Once-per-fingerprint emit dedupe |
| `orchestration-failures.json` | report endpoint only | Open n8n failure evidence for `failed_n8n_workflow` |

Evaluate-only never writes either file. Emit never writes orchestration-failures.
Report never writes the emissions ledger. Neither path mutates
`metadata/campaigns/`, `metadata/runs/`, editorial lifecycle folders, calendar,
or LinkedIn artifacts.

## Controlled fixture demonstration

Local verification exercised authenticated evaluate/report responses for:

- error-folder campaigns → `item_moved_to_error`
- ComfyUI / blog image-generation codes → `image_generation_failure`
- blog publish / git publication codes → `blog_publication_failure`
- delayed calendar items → `partial_calendar_execution` (warning; no title)
- LinkedIn dependency / progress failure codes → `linkedin_token_or_publication_failure`
- stale campaigns → `stale_campaign` (warning)
- degraded folder readiness → `unhealthy_worker`; healthy layout → none
- report ingest → `failed_n8n_workflow`; failed runs alone → no n8n alert
- exclusion of preview-only checkout codes from blog and LinkedIn alert types
- eight-type `summary.counts`; US-028 + US-029 + US-030 coexistence
- report auth 401, invalid `reason_code` / `observed_at_utc` 422, idempotent duplicate report
- evaluate auth 401, invalid `now_utc` 422, deterministic ordering, secret-safe output
- evaluate-only zero lifecycle mutation
- fail-closed emit when disabled/misconfigured
- successful emit + ledger write and no re-emit for existing fingerprints (including US-030)

This demonstrates US-028, US-029, and US-030 at controlled-fixture,
automated-test, and controlled live-smoke scope on `192.168.0.194`
(`BUILD_REVISION=b67c538`). **Operator-accepted 2026-07-17; BL-011 closed.**
Production webhook + n8n Error Trigger wiring were enabled as the documented
follow-up on 2026-07-17 (see Emission / Live enablement above).
