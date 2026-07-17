## ADDED Requirements

### Requirement: Authenticated operational-alerts evaluate endpoint

The worker SHALL expose `POST /flow-a/operational-alerts/evaluate` protected by API-key authentication through `Depends(require_api_key)`.

The endpoint MUST accept a JSON body with:

- optional `now_utc` in canonical UTC `YYYY-MM-DDTHH:MM:SSZ` form (invalid values MUST return HTTP 422);
- optional `emit` boolean defaulting to `false`.

When `now_utc` is omitted, the worker MUST capture current UTC once and use that instant for every derived alert in the response.

The response MUST include `status`, `observed_at_utc`, `alerts`, `summary`, `data_issues`, and `emission`. The endpoint MUST NOT accept filesystem paths from the client.

#### Scenario: Authenticated operator evaluates alerts
- **WHEN** a client with a valid API key calls `POST /flow-a/operational-alerts/evaluate` with `emit` omitted or `false`
- **THEN** the worker returns HTTP 200 with structured US-028 alert candidates and does not call a webhook

#### Scenario: Endpoint requires API-key authentication
- **WHEN** a client calls `POST /flow-a/operational-alerts/evaluate` without a valid API key
- **THEN** the worker returns HTTP 401 and does not read alert ledgers, call webhooks, or mutate operational artifacts

#### Scenario: Invalid observation time is rejected
- **WHEN** `now_utc` is present but not canonical UTC `YYYY-MM-DDTHH:MM:SSZ`
- **THEN** the worker returns HTTP 422 and performs no evaluation side effects

### Requirement: Derive US-028 alerts from operational-status evidence

Alert evaluation SHALL derive candidates from the same confined operational-status evidence and classifications used by `GET /flow-a/operational-status` (runs, campaigns, dependency-failure buckets). It MUST NOT perform an ad-hoc independent scan of raw editorial folders as a parallel source of truth, and MUST NOT call ComfyUI, DeepSeek, LinkedIn, OAuth, Git, or live-site endpoints.

US-028 alert types MUST be exactly:

- `item_moved_to_error` when a Flow A campaign is classified failed with `source_file_status.location=error` (or the equivalent operational-status error-location health reason);
- `image_generation_failure` when dependency-failure attribution exists in bucket `comfyui` for a campaign or run;
- `blog_publication_failure` when dependency-failure attribution exists in bucket `github_pages_checkout` for validated codes matching `blog_publish_*` or `blog_git_publication_*`.

`blog_publication_failure` MUST NOT be raised solely for LinkedIn-preview checkout codes (`linkedin_preview_validation_checkout_*` or exactly `linkedin_article_preview_public_repo_not_configured`).

US-029 and US-030 alert types MUST NOT be produced by this capability.

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

### Requirement: Safe understandable alert payloads

Each alert object MUST include `alert_type`, `severity`, `fingerprint`, `observed_at_utc`, a short `summary`, and safe identifiers (`campaign_id` and/or `run_id` when known). When derived from dependency evidence, it MUST include `dependency` and sorted validated `error_codes`.

Alert payloads MUST NOT include Markdown or draft bodies, API keys, tokens, client secrets, authorization headers, raw external API bodies, arbitrary environment values, webhook URLs, or the absolute editorial base path.

`summary.counts` MUST include integer counts for `item_moved_to_error`, `image_generation_failure`, and `blog_publication_failure`.

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

### Requirement: Fail-closed optional webhook emission

When `emit` is `false` or omitted, the worker MUST NOT call any webhook and MUST NOT write the operational-alerts emission ledger.

When `emit` is `true`, emission SHALL be fail-closed:

- If `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` is not enabled, or the webhook URL is unset/invalid, the worker MUST NOT call a webhook and MUST NOT write the ledger; the response MUST set `emission` to an explicit disabled or misconfigured status while still returning evaluated `alerts`.
- If enabled and configured, the worker MAY POST only secret-safe alert payloads for fingerprints not already recorded as successfully emitted.

Successful webhook acceptance (HTTP 2xx) is required before recording a fingerprint as emitted. Failed webhook delivery MUST leave the fingerprint unemitted.

The MVP channel is a generic HTTP webhook. The worker MUST NOT require Slack, email, or UI integrations for US-028.

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

Evaluate-only requests MUST NOT mutate campaign, run, calendar, editorial lifecycle, LinkedIn, or public-blog artifacts.

Emit requests MUST NOT mutate those lifecycle artifacts either; the only permitted write is the operational-alerts emission ledger under the rules above.

Reads for evaluation evidence MUST remain confined to the same approved operational-status sources plus, when emit requires dedupe, the operational-alerts ledger path.

#### Scenario: Evaluate-only leaves lifecycle bytes unchanged
- **WHEN** an authenticated evaluate-only request runs over valid and invalid evidence
- **THEN** file inventory and bytes under runs, campaigns, calendar, editorial lifecycle folders, and LinkedIn artifact folders are unchanged, and no operational-alerts ledger write occurs

#### Scenario: Emit writes only the alerts ledger
- **WHEN** an enabled emit succeeds for a new fingerprint
- **THEN** the only new or modified persistence under the editorial base for that request is under `metadata/operational-alerts/`, and campaign/run/editorial lifecycle files remain unchanged

### Requirement: US-028 scope and verification

Implementation SHALL satisfy BL-011 / US-028 alert criteria for items moved to error, image-generation failure, and blog publication failure through the evaluate/emit contract defined in this capability.

Focused behavioral tests MUST cover each US-028 alert type, exclusion of preview-only checkout codes from `blog_publication_failure`, auth failures, invalid `now_utc`, deterministic ordering, safe output, fail-closed emission, idempotent ledger behavior, evaluate-only zero lifecycle mutation, and no external integration calls during evaluation.

This capability MUST NOT implement US-029 or US-030 alert types, MUST NOT add BL-015 UI behavior, MUST NOT deploy or mutate live systems as part of the change, and MUST NOT require a production n8n workflow activation to complete implementation.

`docs/CURRENT-STATE.md` and product progress MUST be updated only to the level actually implemented and demonstrated. Proposal or code completion alone MUST NOT mark US-028 accepted or BL-011 closed.

#### Scenario: US-028 focused suite passes
- **WHEN** the change is verified
- **THEN** focused operational-alerts tests for the three US-028 types, fail-closed emission, and lifecycle non-mutation pass

#### Scenario: Out-of-scope alert types remain absent
- **WHEN** the US-028 capability is implemented
- **THEN** no partial-calendar, LinkedIn-token, stale-campaign, unhealthy-worker, or failed-n8n-workflow alert types are produced, and no supervision UI is added
