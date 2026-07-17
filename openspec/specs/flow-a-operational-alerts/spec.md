# flow-a-operational-alerts

## Purpose

BL-011 / US-028 + US-029 + US-030 Flow A operational-alert evaluation, optional
fail-closed emission, and authenticated orchestration-failure report ingest:
authenticated `POST /flow-a/operational-alerts/evaluate` derives secret-safe
alert candidates (US-028/US-029 from operational-status evidence; US-030 from
health-equivalent folder readiness and persisted orchestration-failure reports),
with optional generic webhook delivery and a minimal idempotent emission ledger.
Does not add BL-015 UI or Slack/email SDKs, and does not by itself accept
US-028/US-029/US-030 or close BL-011.

## Requirements

### Requirement: Authenticated operational-alerts evaluate endpoint

The worker SHALL expose `POST /flow-a/operational-alerts/evaluate` protected by API-key authentication through `Depends(require_api_key)`.

The endpoint MUST accept a JSON body with:

- optional `now_utc` in canonical UTC `YYYY-MM-DDTHH:MM:SSZ` form (invalid values MUST return HTTP 422);
- optional `emit` boolean defaulting to `false`.

When `now_utc` is omitted, the worker MUST capture current UTC once and use that instant for every derived alert in the response.

The response MUST include `status`, `observed_at_utc`, `alerts`, `summary`, `data_issues`, and `emission`. The endpoint MUST NOT accept filesystem paths from the client.

#### Scenario: Authenticated operator evaluates alerts
- **WHEN** a client with a valid API key calls `POST /flow-a/operational-alerts/evaluate` with `emit` omitted or `false`
- **THEN** the worker returns HTTP 200 with structured US-028, US-029, and US-030 alert candidates and does not call a webhook

#### Scenario: Endpoint requires API-key authentication
- **WHEN** a client calls `POST /flow-a/operational-alerts/evaluate` without a valid API key
- **THEN** the worker returns HTTP 401 and does not read alert ledgers, call webhooks, or mutate operational artifacts

#### Scenario: Invalid observation time is rejected
- **WHEN** `now_utc` is present but not canonical UTC `YYYY-MM-DDTHH:MM:SSZ`
- **THEN** the worker returns HTTP 422 and performs no evaluation side effects

### Requirement: Authenticated orchestration-failure report endpoint

The worker SHALL expose `POST /flow-a/operational-alerts/report-orchestration-failure` protected by API-key authentication through `Depends(require_api_key)`.

The endpoint MUST accept a JSON body with:

- required `workflow_id` (non-empty safe opaque token; invalid → HTTP 422);
- required `reason_code` from an allowlisted set of machine-readable codes (unknown values → HTTP 422);
- optional `observed_at_utc` in canonical UTC `YYYY-MM-DDTHH:MM:SSZ` form (invalid → HTTP 422; when omitted, use request-time UTC);
- optional `execution_id` (safe opaque token when present);
- optional `node_name` (short safe label when present);
- optional `campaign_id` and/or `run_id` when already known and valid-shaped.

The endpoint MUST reject request bodies that include Markdown/content bodies, authorization values, webhook URLs, absolute editorial base paths, raw provider/HTTP bodies, stack traces, or arbitrary environment dumps.

On success the worker MUST persist a secret-safe orchestration-failure record under `metadata/operational-alerts/` (orchestration-failures store) and return HTTP 200 with a structured acknowledgment including the report fingerprint / identifiers. Identical fingerprints MUST be idempotent (no duplicate open entries).

The endpoint MUST NOT write the emissions ledger, MUST NOT call webhooks, and MUST NOT mutate campaign, run, calendar, editorial lifecycle, LinkedIn, or public-blog artifacts.

#### Scenario: Authenticated n8n client reports a workflow failure
- **WHEN** a client with a valid API key posts a valid orchestration-failure body for workflow `silvermanFlowAPublish01` with allowlisted `reason_code`
- **THEN** the worker returns HTTP 200, persists the record under `metadata/operational-alerts/`, and does not mutate campaign/run/editorial lifecycle artifacts

#### Scenario: Report endpoint requires API-key authentication
- **WHEN** a client calls `POST /flow-a/operational-alerts/report-orchestration-failure` without a valid API key
- **THEN** the worker returns HTTP 401 and does not write orchestration-failure evidence or lifecycle artifacts

#### Scenario: Invalid reason_code is rejected
- **WHEN** `reason_code` is not in the allowlist
- **THEN** the worker returns HTTP 422 and performs no persistence

#### Scenario: Identical report fingerprint is idempotent
- **WHEN** the same valid fingerprint is reported twice
- **THEN** the second call returns HTTP 200 without creating a duplicate open entry

### Requirement: Derive US-028 alerts from operational-status evidence

Alert evaluation SHALL derive US-028 candidates from the same confined operational-status evidence and classifications used by `GET /flow-a/operational-status` (runs, campaigns, delayed calendar items, dependency-failure buckets, LinkedIn progress). It MUST NOT perform an ad-hoc independent scan of raw editorial folders or calendar files as a parallel source of truth for those US-028 types, and MUST NOT call ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site endpoints.

US-028 alert types MUST continue to be produced exactly when:

- `item_moved_to_error` when a Flow A campaign is classified failed with `source_file_status.location=error` (or the equivalent operational-status error-location health reason);
- `image_generation_failure` when dependency-failure attribution exists in bucket `comfyui` for a campaign or run;
- `blog_publication_failure` when dependency-failure attribution exists in bucket `github_pages_checkout` for validated codes matching `blog_publish_*` or `blog_git_publication_*`.

`blog_publication_failure` MUST NOT be raised solely for LinkedIn-preview checkout codes (`linkedin_preview_validation_checkout_*` or exactly `linkedin_article_preview_public_repo_not_configured`).

US-029 alert types are specified separately in this capability and MUST also be derived from the same operational-status evidence. US-030 alert types are specified separately and MUST be derived from health-equivalent folder readiness and persisted orchestration-failure evidence as defined in this capability.

#### Scenario: Error-folder campaign produces item_moved_to_error
- **WHEN** operational evidence includes a Flow A campaign with `source_file_status.location=error`
- **THEN** evaluation returns one `item_moved_to_error` alert for that `campaign_id`

#### Scenario: ComfyUI dependency failure produces image_generation_failure
- **WHEN** operational dependency aggregation attributes validated code `blog_image_generation_comfyui_failed` to bucket `comfyui` for a campaign or run
- **THEN** evaluation returns one `image_generation_failure` alert referencing that artifact and code

#### Scenario: Blog publish failure produces blog_publication_failure
- **WHEN** operational dependency aggregation attributes validated code `blog_git_publication_push_failed` to bucket `github_pages_checkout`
- **THEN** evaluation returns one `blog_publication_failure` alert for that artifact and code

#### Scenario: Preview-only checkout codes are excluded from blog_publication_failure
- **WHEN** the only `github_pages_checkout` attribution is `linkedin_article_preview_public_repo_not_configured`
- **THEN** evaluation does not emit `blog_publication_failure` for that code

#### Scenario: Evaluation performs no external integration calls
- **WHEN** alerts are evaluated
- **THEN** no ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site client or command is invoked

### Requirement: Derive US-029 alerts from operational-status evidence

In addition to US-028 types, alert evaluation SHALL produce exactly these US-029 alert types from the same operational-status evidence:

- `partial_calendar_execution` when operational-status includes a delayed calendar item (past-due non-terminal item with reason `calendar_item_past_due`); one alert per `item_id`;
- `linkedin_token_or_publication_failure` when dependency-failure attribution exists in bucket `linkedin` for a campaign or failed run, or when a campaign’s LinkedIn progress exposes one or more validated `failure_codes`; one alert per campaign or run with sorted unique codes merged;
- `stale_campaign` when a Flow A campaign is classified `stale=true`; one alert per `campaign_id`.

`partial_calendar_execution` severity MUST be `warning`. `stale_campaign` severity MUST be `warning`. `linkedin_token_or_publication_failure` severity MUST be `error`.

`linkedin_token_or_publication_failure` MUST set `dependency=linkedin`. It MUST NOT be raised solely for LinkedIn-preview checkout codes that belong to `github_pages_checkout`.

Evaluation MUST still reuse operational-status aggregation and MUST NOT invent a parallel scanner.

#### Scenario: Delayed calendar item produces partial_calendar_execution
- **WHEN** operational evidence includes a delayed calendar item with reason `calendar_item_past_due`
- **THEN** evaluation returns one `partial_calendar_execution` alert for that `calendar_item_id` with severity `warning`

#### Scenario: LinkedIn dependency failure produces linkedin_token_or_publication_failure
- **WHEN** operational dependency aggregation attributes validated code `linkedin_publish_api_error` or `linkedin_oauth_refresh_failed` to bucket `linkedin` for a campaign or run
- **THEN** evaluation returns one `linkedin_token_or_publication_failure` alert referencing that artifact, `dependency=linkedin`, and the validated code(s)

#### Scenario: LinkedIn progress failure codes produce linkedin_token_or_publication_failure
- **WHEN** a campaign’s LinkedIn progress summary includes validated `failure_codes` such as `linkedin_publish_token_invalid`
- **THEN** evaluation returns one `linkedin_token_or_publication_failure` alert for that `campaign_id` including those codes

#### Scenario: Stale campaign produces stale_campaign
- **WHEN** operational evidence classifies a Flow A campaign with `stale=true`
- **THEN** evaluation returns one `stale_campaign` alert for that `campaign_id` with severity `warning`

#### Scenario: LinkedIn preview checkout codes do not produce linkedin_token_or_publication_failure
- **WHEN** the only relevant attribution is a LinkedIn-preview checkout code under `github_pages_checkout`
- **THEN** evaluation does not produce `linkedin_token_or_publication_failure` for that code

#### Scenario: US-028 and US-029 candidates coexist without lifecycle mutation
- **WHEN** evidence includes an error-folder campaign and a delayed calendar item in the same evaluate-only request
- **THEN** both corresponding alert types are returned and campaign/run/editorial lifecycle bytes remain unchanged

### Requirement: Derive US-030 alerts from health and orchestration-failure evidence

In addition to US-028 and US-029 types, alert evaluation SHALL produce exactly these US-030 alert types:

- `unhealthy_worker` when in-process editorial-folder validation equivalent to `GET /health` reports `folders_ready=false` (degraded readiness); one alert for the current not-ready folder set;
- `failed_n8n_workflow` when the operational-alerts orchestration-failures store contains an open report; one alert per distinct report fingerprint.

`unhealthy_worker` severity MUST be `error`. `failed_n8n_workflow` severity MUST be `error`.

Evaluation MUST obtain unhealthy-worker evidence via the shared folder-validation path used by `GET /health` (in-process). It MUST NOT HTTP-loopback to `/health`, MUST NOT call ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site endpoints, MUST NOT scrape n8n APIs, and MUST NOT treat failed `metadata/runs/*` records alone as `failed_n8n_workflow`.

`unhealthy_worker` MUST include sorted validated reason codes for not-ready folders. `failed_n8n_workflow` MUST include `workflow_id` and the reported `reason_code` (and optional `execution_id` when present).

US-028 and US-029 alert types MUST continue to be produced from operational-status evidence unchanged by these rules.

#### Scenario: Degraded folder readiness produces unhealthy_worker
- **WHEN** editorial folder validation reports `folders_ready=false` during evaluate
- **THEN** evaluation returns one `unhealthy_worker` alert with severity `error` and sorted not-ready folder reason codes

#### Scenario: Healthy folder readiness produces no unhealthy_worker
- **WHEN** editorial folder validation reports `folders_ready=true` during evaluate
- **THEN** evaluation does not produce `unhealthy_worker`

#### Scenario: Persisted orchestration failure produces failed_n8n_workflow
- **WHEN** the orchestration-failures store contains an open report for workflow `silvermanFlowAPublish01` with allowlisted reason code `n8n_workflow_failed`
- **THEN** evaluation returns one `failed_n8n_workflow` alert referencing that workflow and reason code

#### Scenario: Failed runs alone do not produce failed_n8n_workflow
- **WHEN** operational-status includes a failed run but the orchestration-failures store is empty
- **THEN** evaluation does not produce `failed_n8n_workflow` solely from that run

#### Scenario: US-030 evaluation performs no external integration or n8n API calls
- **WHEN** alerts are evaluated
- **THEN** no ComfyUI, DeepSeek, LinkedIn, OAuth, Git, live-site, or n8n Admin/API client is invoked

### Requirement: Safe understandable alert payloads

Each alert object MUST include `alert_type`, `severity`, `fingerprint`, `observed_at_utc`, a short `summary`, and safe identifiers (`campaign_id` and/or `run_id` when known; `calendar_item_id` when the alert is `partial_calendar_execution`; `workflow_id` and optional `execution_id` when the alert is `failed_n8n_workflow`). When derived from dependency evidence, it MUST include `dependency` and sorted validated `error_codes`.

Alert payloads MUST NOT include Markdown or draft bodies, API keys, tokens, client secrets, authorization headers, raw external API bodies, arbitrary environment values, webhook URLs, the absolute editorial base path, or calendar free-text titles.

`summary.counts` MUST include integer counts for `item_moved_to_error`, `image_generation_failure`, `blog_publication_failure`, `partial_calendar_execution`, `linkedin_token_or_publication_failure`, `stale_campaign`, `unhealthy_worker`, and `failed_n8n_workflow`.

`alerts` MUST be ordered deterministically by `alert_type` ascending, then `fingerprint` ascending. Repeated evaluation with the same `now_utc` and unchanged evidence MUST return identical candidate sets and ordering.

#### Scenario: Alert payload is understandable without raw files
- **WHEN** an `image_generation_failure` alert is returned
- **THEN** it includes `alert_type`, safe artifact id, validated error code(s), `dependency=comfyui`, and a short summary an operator can understand without opening raw JSON bodies

#### Scenario: Secrets and content bodies are excluded from alerts
- **WHEN** source documents contain tokens, secret-shaped fields, or content bodies
- **THEN** none of those values appear in the evaluate response or webhook payload

#### Scenario: Deterministic alert ordering
- **WHEN** two authenticated evaluate requests use the same `now_utc` against unchanged evidence
- **THEN** both responses contain identical `alerts` ordering and fingerprints

#### Scenario: Partial-calendar alert identifies the calendar item safely
- **WHEN** a `partial_calendar_execution` alert is returned
- **THEN** it includes `calendar_item_id`, reason code `calendar_item_past_due`, and does not include the calendar item title

#### Scenario: Failed n8n alert identifies the workflow safely
- **WHEN** a `failed_n8n_workflow` alert is returned
- **THEN** it includes `workflow_id`, the reported reason code, and does not include raw n8n error payloads

### Requirement: Fail-closed optional webhook emission

When `emit` is `false` or omitted, the worker MUST NOT call any webhook and MUST NOT write the operational-alerts emission ledger.

When `emit` is `true`, emission SHALL be fail-closed:

- If `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` is not enabled, or the webhook URL is unset/invalid, the worker MUST NOT call a webhook and MUST NOT write the ledger; the response MUST set `emission` to an explicit disabled or misconfigured status while still returning evaluated `alerts`.
- If enabled and configured, the worker MAY POST only secret-safe alert payloads for fingerprints not already recorded as successfully emitted.

Successful webhook acceptance (HTTP 2xx) is required before recording a fingerprint as emitted. Failed webhook delivery MUST leave the fingerprint unemitted.

The MVP channel is a generic HTTP webhook. The worker MUST NOT require Slack, email, or UI integrations for US-028, US-029, or US-030.

#### Scenario: Evaluate-only performs no emission
- **WHEN** `emit` is false or omitted
- **THEN** no webhook is called and the emission ledger is not written

#### Scenario: Emit while disabled is fail-closed
- **WHEN** `emit` is true and operational alerts are disabled or the webhook URL is unset
- **THEN** evaluated alerts are still returned, `emission` reports disabled or misconfigured, and no webhook call or ledger write occurs

#### Scenario: Enabled emit delivers new fingerprints only
- **WHEN** `emit` is true, alerts are enabled and configured, and a candidate fingerprint is not yet recorded
- **THEN** the worker POSTs a safe payload to the configured webhook and records the fingerprint only after HTTP 2xx

#### Scenario: Already-emitted fingerprint is not re-sent
- **WHEN** `emit` is true and the fingerprint already exists in the emission ledger from a prior successful delivery
- **THEN** the worker does not call the webhook again for that fingerprint and reports it as already emitted

### Requirement: Emission ledger isolation and lifecycle non-mutation

Persisted “already alerted” state, when used, MUST live only under `metadata/operational-alerts/` beneath the configured editorial base (ledger file `emissions.json`).

Persisted orchestration-failure evidence MUST also live only under `metadata/operational-alerts/` (orchestration-failures store) and MUST be written only by the authenticated report endpoint.

Evaluate-only requests MUST NOT mutate campaign, run, calendar, editorial lifecycle, LinkedIn, or public-blog artifacts, MUST NOT write the emissions ledger, and MUST NOT write the orchestration-failures store.

Emit requests MUST NOT mutate those lifecycle artifacts either; the only permitted write is the operational-alerts emission ledger under the rules above.

Report requests MUST NOT mutate lifecycle artifacts; the only permitted write is the orchestration-failures store under the rules above.

Reads for evaluation evidence MUST remain confined to the approved operational-status sources, in-process health-equivalent folder validation, the orchestration-failures store, and, when emit requires dedupe, the operational-alerts emissions ledger path.

#### Scenario: Evaluate-only leaves lifecycle bytes unchanged
- **WHEN** an authenticated evaluate-only request runs over valid and invalid evidence
- **THEN** file inventory and bytes under runs, campaigns, calendar, editorial lifecycle folders, and LinkedIn artifact folders are unchanged, and no operational-alerts emissions ledger write occurs

#### Scenario: Emit writes only the alerts ledger
- **WHEN** an enabled emit succeeds for a new fingerprint
- **THEN** the only new or modified persistence under the editorial base for that request is under `metadata/operational-alerts/`, and campaign/run/editorial lifecycle files remain unchanged

#### Scenario: Report writes only orchestration-failure evidence
- **WHEN** an authenticated report succeeds for a new fingerprint
- **THEN** the only new or modified persistence under the editorial base for that request is under `metadata/operational-alerts/`, and campaign/run/editorial lifecycle files remain unchanged

### Requirement: US-028 scope and verification

Implementation SHALL continue to satisfy BL-011 / US-028 alert criteria for items moved to error, image-generation failure, and blog publication failure through the evaluate/emit contract defined in this capability.

Focused behavioral tests MUST continue to cover each US-028 alert type, exclusion of preview-only checkout codes from `blog_publication_failure`, auth failures, invalid `now_utc`, deterministic ordering, safe output, fail-closed emission, idempotent ledger behavior, evaluate-only zero lifecycle mutation, and no external integration calls during evaluation.

US-029 and US-030 alert types are specified separately and MUST NOT regress US-028 behaviors. This capability MUST NOT add BL-015 UI behavior, MUST NOT deploy or mutate live systems as part of the change, and MUST NOT require a production n8n workflow activation to complete implementation.

`docs/CURRENT-STATE.md` and product progress MUST be updated only to the level actually implemented and demonstrated. Proposal or code completion alone MUST NOT mark US-028 accepted, MUST NOT mark US-029 accepted, MUST NOT mark US-030 accepted, and MUST NOT close BL-011.

#### Scenario: US-028 focused suite passes
- **WHEN** the change is verified
- **THEN** focused operational-alerts tests for the three US-028 types, fail-closed emission, and lifecycle non-mutation pass

#### Scenario: US-028 behaviors remain intact alongside US-030
- **WHEN** the US-030 capability extension is implemented
- **THEN** US-028 alert types continue to be produced from operational-status evidence and no supervision UI is added

### Requirement: US-029 scope and verification

Implementation SHALL satisfy BL-011 / US-029 alert criteria for partial calendar execution, LinkedIn token or publication failure, and stale campaigns through the existing evaluate/emit contract.

Focused behavioral tests MUST cover each US-029 alert type, coexistence with US-028 types, exclusion of preview-only checkout codes from the LinkedIn alert type, summary counts for prior and US-029 types, fail-closed emission for new fingerprints, evaluate-only zero lifecycle mutation, and no external integration calls during evaluation.

This capability MUST NOT add BL-015 UI behavior, MUST NOT deploy or mutate live systems as part of the change, MUST NOT require production n8n workflow activation, and MUST NOT mark US-028 or US-029 accepted or close BL-011 from proposal or code alone. US-030 types are specified separately and MUST NOT regress US-029 behaviors.

`docs/CURRENT-STATE.md` and product progress MUST be updated only to the level actually implemented and demonstrated.

#### Scenario: US-029 focused suite passes
- **WHEN** the change is verified
- **THEN** focused operational-alerts tests for the three US-029 types, coexistence with US-028, fail-closed emission, and lifecycle non-mutation pass

#### Scenario: US-029 behaviors remain intact alongside US-030
- **WHEN** the US-030 capability extension is implemented
- **THEN** US-029 alert types continue to be produced and no supervision UI is added

### Requirement: US-030 scope and verification

Implementation SHALL satisfy BL-011 / US-030 alert criteria for unhealthy worker and failed n8n workflow attention through the evaluate/emit contract plus the authenticated orchestration-failure report contract defined in this capability.

Focused behavioral tests MUST cover each US-030 alert type, coexistence with US-028 and US-029 types, summary counts for all eight alert types, report auth/validation/idempotency, fail-closed emission for new fingerprints, evaluate-only zero lifecycle mutation, report isolation to `metadata/operational-alerts/`, and no external integration or n8n API calls during evaluation.

This capability MUST NOT add BL-015 UI behavior, MUST NOT deploy or mutate live systems as part of the change, MUST NOT require production n8n workflow activation or Error Trigger wiring to complete implementation, and MUST NOT mark US-028, US-029, or US-030 accepted or close BL-011 from proposal or code alone.

`docs/CURRENT-STATE.md`, `docs/operations/flow-a-operational-alerts.md`, and product progress MUST be updated only to the level actually implemented and demonstrated.

#### Scenario: US-030 focused suite passes
- **WHEN** the change is verified
- **THEN** focused operational-alerts tests for both US-030 types, eight-type summary counts, report ingest, fail-closed emission, and lifecycle non-mutation pass

#### Scenario: Out-of-scope behavior remains absent
- **WHEN** the US-030 capability extension is implemented
- **THEN** no supervision UI is added, US-028 and US-029 alert behaviors remain intact, and BL-011 is not closed from code alone
