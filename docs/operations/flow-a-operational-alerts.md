# Flow A Operational Alerts (US-028 / US-029)

Operator contract for BL-011 alert evaluation and optional fail-closed webhook
emission. Candidates are derived from the same confined evidence used by
read-only [`GET /flow-a/operational-status`](flow-a-operational-status.md).

- **US-028:** `item_moved_to_error`, `image_generation_failure`,
  `blog_publication_failure`
- **US-029:** `partial_calendar_execution`,
  `linkedin_token_or_publication_failure`, `stale_campaign`

This capability does **not** replace the observation endpoint, does not
implement US-030 alert types, does not add BL-015 UI, and does not by itself
accept US-028/US-029 or close BL-011.

## Relationship to operational status

| Surface | Role |
|---------|------|
| `GET /flow-a/operational-status` | Read-only observation (US-026 / US-027). Never notifies, never writes alert ledgers. |
| `POST /flow-a/operational-alerts/evaluate` | US-028 + US-029 alert typing, safe payloads, optional webhook emission + emission ledger. |

Evaluation reuses operational-status classifications and dependency buckets. It
does not ad-hoc rescan raw editorial folders as a parallel source of truth and
does not call ComfyUI, DeepSeek, LinkedIn, Git, or live-site APIs.

## Request

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

## Response

- `status`: mirrored from underlying operational-status evidence (`ok` / `partial`)
- `observed_at_utc`: one request-level observation instant
- `alerts`: deterministic list ordered by `alert_type` then `fingerprint`
- `summary.counts`: integers for all six alert types plus `summary.total`
- `data_issues`: safe issues from the status aggregation when evidence is partial
- `emission`: whether emit was requested and what happened

Each alert includes `alert_type`, `severity` (`error` or `warning`),
`fingerprint`, `observed_at_utc`, short `summary`, and safe identifiers
(`campaign_id` and/or `run_id`; `calendar_item_id` for partial-calendar alerts).
Dependency-derived alerts also include `dependency` and sorted validated
`error_codes`.

Payloads never include Markdown/draft bodies, API keys, tokens, webhook URLs,
authorization values, raw provider bodies, the absolute editorial base path, or
calendar free-text titles.

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
`linkedin_token_or_publication_failure`. US-030 types (`unhealthy_worker`,
`failed_n8n_workflow`) are not produced.

Fingerprint form:
`{alert_type}:{campaign_id|run_id|calendar_item_id}:{primary_error_code|none}`.

## Emission (optional, fail-closed)

| Env | Role | Default |
|-----|------|---------|
| `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` | Master switch | off / false |
| `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_WEBHOOK_URL` | Generic HTTPS webhook target | unset |

When `emit=false` (default): `emission.status=not_requested`; no webhook; no
ledger I/O.

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

## Emission ledger

Path (under the editorial base): `metadata/operational-alerts/emissions.json`

Written only on successful emit. Schema: `version` + `entries` map fingerprint →
`{alert_type, first_emitted_at_utc, last_emitted_at_utc, campaign_id?, run_id?, calendar_item_id?}`.

Already-emitted fingerprints are not re-posted. Evaluate-only never writes this
file. Emit never mutates `metadata/campaigns/`, `metadata/runs/`, editorial
lifecycle folders, calendar, or LinkedIn artifacts.

## Controlled fixture demonstration

Local verification exercised authenticated evaluate responses for:

- error-folder campaigns → `item_moved_to_error`
- ComfyUI / blog image-generation codes → `image_generation_failure`
- blog publish / git publication codes → `blog_publication_failure`
- delayed calendar items → `partial_calendar_execution` (warning; no title)
- LinkedIn dependency / progress failure codes → `linkedin_token_or_publication_failure`
- stale campaigns → `stale_campaign` (warning)
- exclusion of preview-only checkout codes from blog and LinkedIn alert types
- six-type `summary.counts`; US-028 + US-029 coexistence
- auth 401, invalid `now_utc` 422, deterministic ordering, secret-safe output
- evaluate-only zero lifecycle mutation
- fail-closed emit when disabled/misconfigured
- successful emit + ledger write and no re-emit for existing fingerprints (including US-029)

This demonstrates US-028 and US-029 at controlled-fixture and automated-test
scope only. Business acceptance, deployment, live webhook enablement, and
BL-011 closure remain pending. US-030 and BL-015 remain out of scope.
