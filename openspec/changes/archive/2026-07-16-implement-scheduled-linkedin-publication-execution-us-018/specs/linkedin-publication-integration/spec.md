## ADDED Requirements

### Requirement: Auto-queue pending due variants (opt-in)

`POST /publish-linkedin-due-variants` SHALL support an optional request field `auto_queue_pending` (boolean, default `false`).

When `auto_queue_pending` is `false` or omitted, publish-due behavior MUST be unchanged from the canonical two-step contract (queue and publish-due remain separate operations).

When `auto_queue_pending` is `true`, the worker MUST, within the same request:

1. Identify eligible due `pending` variants (per the auto-queue eligibility requirement).
2. Queue each eligible variant using the existing queue publication service rules, computing `publish_after_utc` from the configured default safety delay (`SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES`); the publish-due request MUST NOT accept a `safety_delay_minutes` field (that override remains exclusive to `POST /queue-linkedin-publication`).
3. Evaluate publish-due for `queued` variants exactly as the existing publish-due service defines (including `publish_after_utc <= now_utc` unless `publish_now` is `true`).

A `pending` variant is **due for auto-queue** when its `scheduled_at_utc` is less than or equal to current worker UTC time. When request `publish_now` is `true`, the `scheduled_at_utc` due gate MAY be bypassed as an explicit operator override; supervision exclusions MUST still apply.

Variants with missing or unparsable `scheduled_at_utc` MUST be skipped with a stable reason and MUST NOT abort the operation.

The auto-queue phase MUST reuse the existing queue service validation (campaign eligibility, artifact existence and hash verification, source public URL) rather than a parallel implementation.

When `dry_run` is `true`, the combined operation MUST report planned queue and publish outcomes without mutating `publish_state`, writing metadata, or calling LinkedIn or OAuth endpoints.

#### Scenario: Default off preserves two-step contract

- **WHEN** `POST /publish-linkedin-due-variants` is called without `auto_queue_pending`
- **THEN** no `pending` variant is queued or evaluated and behavior matches the existing publish-due contract for `queued` variants only

#### Scenario: Due pending variant queued and published in one call

- **WHEN** publish-due runs with `auto_queue_pending` true, `dry_run` false, `publish_now` true, and real publish enabled for an eligible `pending` variant whose `scheduled_at_utc` is in the past
- **THEN** the variant is queued via existing queue rules and then published once, ending in `publish_state` `published`

#### Scenario: Not-yet-due pending variant skipped when respecting schedule

- **WHEN** publish-due runs with `auto_queue_pending` true and `publish_now` false for a `pending` variant whose `scheduled_at_utc` is in the future
- **THEN** the variant is not queued, remains `pending`, and the response reports it skipped as not due

#### Scenario: Safety delay still gates publish after auto-queue

- **WHEN** publish-due runs with `auto_queue_pending` true and `publish_now` false, and the queue phase sets `publish_after_utc` in the future via nonzero safety delay
- **THEN** the variant ends the call in `publish_state` `queued` with no LinkedIn API call, and the response communicates it was queued but not yet due for publish

#### Scenario: Dry-run auto-queue does not mutate state

- **WHEN** publish-due runs with `auto_queue_pending` true and `dry_run` true for an eligible due `pending` variant
- **THEN** the variant remains `pending`, no metadata is written, and no LinkedIn or OAuth call occurs

### Requirement: Auto-queue eligibility exclusions honor operator supervision

Auto-queue MUST NOT queue a variant when any of the following apply:

- `publish_state` is not `pending` (automatic re-queue from `failed` is excluded; manual re-queue via `POST /queue-linkedin-publication` remains the only `failed` path)
- `publish_state` is `cancelled`
- `operator_supervision.auto_queue_eligible` is `false`, except under the defer runtime re-evaluation rule below
- the variant is not due per `scheduled_at_utc` and `publish_now` is `false`

Absent `operator_supervision` on a `pending` variant MUST mean strategy-driven eligible (per `linkedin-variant-review-process`).

**Defer runtime re-evaluation:** US-017 defer persists `auto_queue_eligible` `false` with no persisted flip back. Auto-queue MUST evaluate deferred variants at runtime: a `pending` variant whose `operator_supervision.last_action` is `defer` MUST be treated as eligible once its deferred `scheduled_at_utc` is less than or equal to current worker UTC time, without requiring a persisted `auto_queue_eligible` flip to `true`. While the deferred `scheduled_at_utc` is in the future, the variant MUST be skipped — including when `publish_now` is `true` (`publish_now` never bypasses a deferred time).

`publish_now` MUST NOT override supervision exclusions: cancelled variants, variants with `auto_queue_eligible` `false` from cancel, and deferred variants whose new schedule is not yet due are never auto-queued regardless of `publish_now`.

Excluded variants MUST NOT change `publish_state` and MUST NOT by themselves cause the overall operation to fail.

#### Scenario: Cancelled variant never auto-queued

- **WHEN** publish-due runs with `auto_queue_pending` true and `publish_now` true for a campaign containing a `cancelled` variant
- **THEN** the cancelled variant is not queued, not published, and remains `cancelled`

#### Scenario: Deferred variant skipped while new schedule not due

- **WHEN** publish-due runs with `auto_queue_pending` true for a `pending` variant with `operator_supervision.last_action` `defer`, `auto_queue_eligible` `false`, and deferred `scheduled_at_utc` still in the future
- **THEN** the variant is skipped with a stable supervision skip reason and remains `pending`

#### Scenario: Deferred variant eligible again when new schedule due

- **WHEN** publish-due runs with `auto_queue_pending` true for a `pending` variant with `operator_supervision.last_action` `defer` and persisted `auto_queue_eligible` `false`, whose deferred `scheduled_at_utc` is now in the past
- **THEN** the variant is treated as eligible per runtime re-evaluation and may be queued without a persisted `auto_queue_eligible` flip to `true`

#### Scenario: publish_now does not bypass a deferred time

- **WHEN** publish-due runs with `auto_queue_pending` true and `publish_now` true for a deferred `pending` variant whose new `scheduled_at_utc` is still in the future
- **THEN** the variant is not queued, remains `pending`, and the response reports a supervision skip reason

#### Scenario: Failed variant not auto-requeued

- **WHEN** publish-due runs with `auto_queue_pending` true for a campaign containing a `failed` variant
- **THEN** the `failed` variant is not queued and the response communicates it is excluded from auto-queue

### Requirement: Bounded cross-campaign pending scan

When `auto_queue_pending` is `true` and `campaign_id` is omitted, the worker MUST bound the pending scan to campaign metadata documents under `metadata/campaigns/` and MUST consider only campaigns with `flow` `flow_a` and `state` `distribution_scheduled`.

Campaigns that are ineligible or unreadable MUST be skipped without failing the overall operation.

When `variant` is provided without `campaign_id`, the request MUST be rejected as invalid (HTTP 422).

When `campaign_id` is provided, the scan MUST be limited to that campaign; when `variant` is additionally provided, to that single variant.

#### Scenario: Cross-campaign scan targets only eligible Flow A campaigns

- **WHEN** publish-due runs with `auto_queue_pending` true and no `campaign_id` while the metadata folder contains a `distribution_scheduled` Flow A campaign and a campaign in another state
- **THEN** only the `distribution_scheduled` Flow A campaign's pending variants are considered for auto-queue

#### Scenario: Variant filter without campaign rejected

- **WHEN** `POST /publish-linkedin-due-variants` is called with `variant` set and no `campaign_id`
- **THEN** the API returns HTTP 422

### Requirement: Auto-queue outcome visibility

When `auto_queue_pending` is `true`, the response MUST include operator-understandable per-variant results covering both phases:

- variants queued by the auto-queue phase (with resulting `publish_state` and `publish_after_utc`)
- variants published, already published, or failed by the publish phase (existing publish-due result semantics)
- variants skipped, with stable machine-readable reasons distinguishing at minimum: not due per schedule, supervision-excluded (cancelled or `auto_queue_eligible` `false`), not in an auto-queueable `publish_state`, and campaign-level ineligibility

Stable reason/warning codes MUST include at minimum:

- `linkedin_publish_auto_queue_skipped_not_due`
- `linkedin_publish_auto_queue_skipped_supervision`
- `linkedin_publish_auto_queue_skipped_state`

Responses MUST NOT include variant body text or secret values.

#### Scenario: Skip reasons visible per variant

- **WHEN** publish-due runs with `auto_queue_pending` true over a campaign with one due eligible variant, one future-scheduled variant, and one cancelled variant
- **THEN** the response reports the first as queued (and published or queued-not-due per publish rules), the second skipped with `linkedin_publish_auto_queue_skipped_not_due`, and the third skipped with `linkedin_publish_auto_queue_skipped_supervision`

#### Scenario: No secrets or body text in combined response

- **WHEN** the combined auto-queue and publish operation completes or fails
- **THEN** the HTTP response contains no token values and no variant body text

### Requirement: Once-only publication under auto-queue

The combined operation MUST NOT create duplicate LinkedIn posts or duplicate queue metadata:

- variants already `queued` MUST NOT be re-queued (no rewrite of `publication_queued_at` or reset of `publish_after_utc` by the auto-queue phase)
- variants already `published` MUST retain the existing idempotent behavior (no LinkedIn API call; URN and `published_at` preserved)
- repeating the same combined request after a successful real run MUST NOT publish any variant a second time

Real LinkedIn API calls under `auto_queue_pending` MUST still require `dry_run` false, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`, and valid credentials via the token provider; enablement-off MUST fail closed with `linkedin_publish_not_enabled` without marking variants `failed`.

#### Scenario: Repeat combined run is idempotent

- **WHEN** a real combined run publishes a variant and the identical request is repeated
- **THEN** the second run makes no LinkedIn API call for that variant and its `linkedin_post_urn` and `published_at` are unchanged

#### Scenario: Already-queued variant not double-queued

- **WHEN** publish-due runs with `auto_queue_pending` true for a campaign containing a `queued` variant
- **THEN** the auto-queue phase does not modify that variant's queue metadata and the publish phase evaluates it under existing due rules

#### Scenario: Enablement off fails closed under auto-queue

- **WHEN** a real combined run executes with `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` not `true`
- **THEN** no LinkedIn API call occurs, the response includes `linkedin_publish_not_enabled`, and no variant transitions to `failed`

### Requirement: Publish-pending operator script

The repository MUST provide `deploy/server/run-publish-pending-linkedin-variants.sh` that:

- calls `POST /publish-linkedin-due-variants` with `auto_queue_pending: true` over HTTP with API key auth
- defaults to dry-run; real mode requires an explicit `--real` flag and preflights `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` in the server env file
- supports `--respect-schedule` (maps to `publish_now: false`) and optional `--campaign-id` / `--variant` filters (`--variant` requires `--campaign-id`)
- never prints secret values
- reports the worker response and an overall pass/fail derived from response `status`

The repository MAY provide `deploy/server/finish-pending-linkedin-publication.sh` as a Mac-side copy-and-run helper; it MUST invoke the server script over the same HTTP-only contract and MUST NOT bypass worker endpoints.

#### Scenario: Script defaults to dry-run

- **WHEN** the operator runs `run-publish-pending-linkedin-variants.sh` without flags
- **THEN** the request is sent with `dry_run: true` and no LinkedIn API call occurs

#### Scenario: Real mode preflights enablement

- **WHEN** the operator runs the script with `--real` and the server env file does not set `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`
- **THEN** the script fails with remediation guidance before sending a real request and prints no secrets

### Requirement: Manual inactive publish-pending n8n workflow

The repository MUST provide `n8n/workflows/silverman-blog-linkedin-publish-pending.json` as a manual-trigger workflow that orchestrates only worker HTTP calls (health check then `POST /publish-linkedin-due-variants` with `auto_queue_pending: true`), consistent with ADR-0001.

The repo export MUST have `"active": false`.

The repo export's default configuration MUST set `dry_run` `true`; real publication requires an explicit operator edit at execution time (worker enablement and dry-run guards still apply).

The workflow MUST NOT use n8n Execute Command nodes.

Importing this workflow MUST NOT be represented as unattended production automation; activation as a scheduled production workflow requires separate explicit approval outside this change.

#### Scenario: Repo export remains inactive

- **WHEN** the publish-pending workflow JSON is inspected in the repository
- **THEN** `active` is `false`, the default configuration sets `dry_run` `true`, and all nodes are HTTP/logic nodes with no Execute Command usage

#### Scenario: Workflow orchestrates worker HTTP only

- **WHEN** the publish-pending workflow runs manually against the worker
- **THEN** publication side effects occur only through `POST /publish-linkedin-due-variants` with the worker enforcing dry-run, enablement, and eligibility guards

## MODIFIED Requirements

### Requirement: HTTP endpoint POST /publish-linkedin-due-variants

The worker SHALL expose `POST /publish-linkedin-due-variants` with API key authentication.

Request body MUST include optional `campaign_id`, optional `variant`, optional `dry_run` (default `true`), optional `publish_now` (default `false`), and optional `auto_queue_pending` (default `false`).

When `campaign_id` and `variant` are omitted, worker MAY evaluate all eligible queued variants under base path (bounded behavior documented at apply); when `auto_queue_pending` is `true`, the bounded cross-campaign pending scan requirement applies additionally.

Response MUST include per-variant results or summary with `publish_state`, `linkedin_post_urn`, `published_at`, `errors`, `dry_run`; when `auto_queue_pending` is `true`, the response MUST additionally satisfy the auto-queue outcome visibility requirement.

#### Scenario: Publish-due endpoint defaults to dry-run

- **WHEN** request omits `dry_run`
- **THEN** worker treats request as `dry_run` true and does not call LinkedIn API

#### Scenario: Publish-due invalid body returns 422

- **WHEN** request includes unknown extra fields
- **THEN** API returns HTTP 422

#### Scenario: Auto-queue defaults off

- **WHEN** request omits `auto_queue_pending`
- **THEN** worker treats request as `auto_queue_pending` false and does not evaluate `pending` variants

### Requirement: Safety and orchestration boundaries

All LinkedIn publication endpoints MUST default to `dry_run: true`.

This capability MUST NOT activate n8n workflows, cron jobs, or automatic publication when `scheduled_at_utc` or `publish_after_utc` elapses without an explicit HTTP request.

The repository MAY contain manual, inactive n8n workflow exports for LinkedIn publication orchestration (`"active": false`, HTTP-only per ADR-0001); providing or updating such exports MUST NOT activate them, and activation as scheduled production automation requires separate explicit approval.

No LinkedIn API call MUST occur unless `dry_run` is false, publication is enabled, credentials are valid, member URN is present, and variant is eligible (due or `publish_now`).

Operator review UI is out of scope; cancel endpoint is the v1 pre-publish escape hatch.

#### Scenario: No automatic trigger on schedule

- **WHEN** this change is applied
- **THEN** no background job publishes variants when `scheduled_at_utc` or `publish_after_utc` passes without operator or future orchestration calling publish-due

#### Scenario: Inactive workflow export does not publish

- **WHEN** the publish-pending workflow export exists in the repository with `active` false
- **THEN** no publication occurs unless an operator or approved orchestration explicitly executes the workflow or calls the worker endpoint

### Requirement: Test coverage

The repository MUST include `tests/test_linkedin_publication.py` covering at minimum:

- successful queue `pending` → `queued` with `publish_after_utc`
- successful publish-due with mocked LinkedIn client → `published`
- cancel `queued` → `cancelled`
- missing token / missing member URN / not enabled — response fails, variant NOT `failed`
- OAuth token provider `action_required` — response fails, variant NOT `failed`, no LinkedIn API call
- invalid/expired token / insufficient permission on real API attempt → variant `failed`
- publish-due skips not-yet-due variant unless `publish_now`
- idempotent behavior for already `published`
- dry-run defaults and no mutation on queue/publish/cancel dry-run
- wrong campaign state, missing artifact, hash mismatch
- HTTP auth and 422 validation for all three endpoints
- `auto_queue_pending` default false leaves `pending` variants untouched
- auto-queue queues and publishes a due eligible `pending` variant once (mocked LinkedIn client)
- auto-queue skips: not due per `scheduled_at_utc`, `cancelled`, `operator_supervision.auto_queue_eligible` `false` from cancel, and `failed` variants, with stable skip reasons
- deferred variant skipped while its new `scheduled_at_utc` is in the future (persisted `auto_queue_eligible` `false` from defer)
- deferred variant eligible again at runtime once new `scheduled_at_utc` is due, without a persisted `auto_queue_eligible` flip
- `publish_now` bypasses the schedule gate for strategy-default variants but never supervision exclusions, including a deferred variant whose new schedule is not yet due
- repeat combined run does not duplicate LinkedIn posts and does not re-queue `queued` variants
- dry-run combined run performs no mutation and no LinkedIn/OAuth calls
- `variant` without `campaign_id` returns HTTP 422
- publish-pending n8n workflow export has `active` false and no Execute Command nodes

OAuth lifecycle tests belong to `linkedin-oauth-token-lifecycle` but publication integration tests MUST cover provider `action_required` behavior.

#### Scenario: Test module passes

- **WHEN** `pytest` runs after apply
- **THEN** `tests/test_linkedin_publication.py` passes
