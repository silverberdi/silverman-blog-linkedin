# linkedin-publication-integration

## Purpose

Flow A deferred LinkedIn API publication for the `silverman-blog-linkedin` HTTP worker: queue-and-safety-delay model with separate queue, publish-due, and cancel actions; worker-side scheduling only (no LinkedIn native scheduling); personal-profile text posts; per-variant state model; dry-run defaults; smoke tooling; and operator documentation. Implements umbrella slice 8 as a follow-up to Flow A Core.

## ADDED Requirements

### Requirement: Umbrella and dependency references

This child change SHALL implement Flow A LinkedIn API publication under umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap` (child slice 8), as a **follow-up** to Flow A Core completion at `distribution_scheduled`.

Publication behavior MUST align with Flow A policy in canonical spec `editorial-canon`.

Campaign metadata and variant IDs MUST use canonical spec `flow-a-lifecycle` and worker module `campaign_lifecycle.py`.

Publication MUST consume scheduling metadata from canonical spec `linkedin-distribution-scheduling-model` and artifacts from `linkedin-derivative-package-generation`.

Existing `scheduled_at_utc` MUST remain the internal distribution schedule. LinkedIn MUST receive posts only when the worker calls the LinkedIn API. This change MUST NOT assume LinkedIn native personal-profile scheduled posting.

Flow B campaigns MUST NOT enter this publication path.

This capability is **separate from Flow A Core** — Flow A Core success does not require LinkedIn API publication.

#### Scenario: Child change cites umbrella and completed siblings

- **WHEN** this capability is documented or implemented
- **THEN** it references umbrella `flow-a-automatic-blog-linkedin-publishing-roadmap`, lifecycle, package generation, and distribution scheduling child changes

#### Scenario: Worker-side scheduling only

- **WHEN** a variant is queued or published
- **THEN** timing is controlled by worker metadata (`scheduled_at_utc`, `publish_after_utc`) and worker endpoint invocation, not LinkedIn-side scheduling

### Requirement: Per-variant publish states

LinkedIn publication MUST use these per-variant `publish_state` values:

- `pending` — scheduled by Flow A Core; not authorized for LinkedIn API publication
- `queued` — authorized; waiting for `publish_after_utc` before eligible for real publish
- `published` — successfully sent to LinkedIn
- `failed` — real LinkedIn API attempt failed or content/platform rejection for that variant
- `cancelled` — operator cancelled before real publish

#### Scenario: Initial state after Flow A Core

- **WHEN** distribution scheduling completes
- **THEN** each variant has `publish_state` `pending`

#### Scenario: Queue transitions pending to queued

- **WHEN** real queue succeeds for a `pending` variant
- **THEN** variant `publish_state` becomes `queued`

#### Scenario: Cancel transitions queued to cancelled

- **WHEN** real cancel succeeds for a `queued` variant
- **THEN** variant `publish_state` becomes `cancelled` and published variants are unchanged

### Requirement: LinkedIn publication configuration

The worker SHALL support these environment variables:

- `SILVERMAN_LINKEDIN_ACCESS_TOKEN` — OAuth 2.0 access token supplied externally
- `SILVERMAN_LINKEDIN_MEMBER_URN` — **required in v1**; member author URN (for example `urn:li:person:{id}`)
- `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` — must be `true` for real LinkedIn API calls
- `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` — default safety delay; default value `120` for this phase
- `SILVERMAN_LINKEDIN_API_VERSION` — optional LinkedIn API version header override

The worker MUST NOT auto-resolve member URN via `/v2/userinfo` in this slice.

The worker MUST NOT print, log, or return access tokens in HTTP responses, smoke scripts, or error messages.

Missing token, missing member URN, or publication not enabled MUST fail the HTTP response with stable error codes but MUST NOT set variant `publish_state` to `failed`.

#### Scenario: Missing member URN on real publish

- **WHEN** a real publish-due request runs with `dry_run` false and `SILVERMAN_LINKEDIN_MEMBER_URN` is unset
- **THEN** the operation fails with `linkedin_publish_member_urn_missing`, no LinkedIn API call occurs, and variant `publish_state` is unchanged

#### Scenario: Config error does not mark failed

- **WHEN** a real publish-due request fails because `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not `true`
- **THEN** response includes `linkedin_publish_not_enabled` and variant `publish_state` remains `queued` (not `failed`)

#### Scenario: Token never in response

- **WHEN** any LinkedIn publication operation completes or fails
- **THEN** HTTP response and campaign metadata do not contain token values

### Requirement: Safety delay and publish_after_utc

Real queue operations MUST set `publish_after_utc` on the variant using:

- request `publish_after_utc` when provided (UTC ISO8601), or
- `now_utc + safety_delay_minutes`, where `safety_delay_minutes` comes from request override or `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES` (default `120`)

Real publish-due MUST publish a `queued` variant only when `publish_after_utc <= now_utc`, unless request `publish_now` is `true`.

Immediate publication MUST require either `SILVERMAN_LINKEDIN_DEFAULT_SAFETY_DELAY_MINUTES=0` at queue time or explicit `publish_now: true` on publish-due.

Future immediate mode MUST be achievable by configuration or request flag without redesigning the queue/publish flow.

#### Scenario: Default safety delay applied on queue

- **WHEN** real queue runs without `publish_after_utc` or `safety_delay_minutes` and default delay is `120`
- **THEN** variant `publish_after_utc` is approximately `now + 120 minutes` and `publication_safety_delay_minutes` is `120`

#### Scenario: Publish-due skips not-yet-due variant

- **WHEN** publish-due runs in real mode for a `queued` variant whose `publish_after_utc` is in the future and `publish_now` is false
- **THEN** no LinkedIn API call occurs and response indicates variant not yet due

#### Scenario: Publish_now bypasses delay

- **WHEN** publish-due runs with `publish_now` true for a `queued` variant and real publish is enabled
- **THEN** LinkedIn API may be called regardless of `publish_after_utc`

### Requirement: Per-variant publication metadata fields

For queued variants, campaign metadata MUST record at minimum:

- `publish_after_utc`
- `publication_queued_at`
- `publication_mode` (for example `safety_delay`)
- `publication_safety_delay_minutes`

For published variants, metadata MUST record at minimum:

- `linkedin_post_urn` or `linkedin_post_id`
- `published_at`
- `linkedin_publication` (safe provider subset; no tokens)

For failed variants after real API attempt, metadata MUST record failure context in `linkedin_publication`.

Campaign metadata and HTTP responses MUST NOT include variant body text.

#### Scenario: Queue writes publication metadata

- **WHEN** real queue succeeds
- **THEN** variant records `publication_queued_at`, `publish_after_utc`, `publication_mode`, and `publication_safety_delay_minutes`

#### Scenario: Publish writes URN without body text

- **WHEN** real publish succeeds
- **THEN** variant records `linkedin_post_urn`, `published_at`, and `linkedin_publication` without artifact body text in metadata or HTTP response

### Requirement: Queue publication service

The worker SHALL expose a queue service entry point (for example `queue_linkedin_publication(base_path, *, campaign_id, variant, dry_run=True, safety_delay_minutes=None, publish_after_utc=None, ...)`) that validates eligibility and moves eligible variants from `pending` to `queued` without calling LinkedIn API.

The queue entry point MUST NOT call LinkedIn API.

The queue entry point MUST NOT move editorial source files or run git operations.

When `dry_run` is true, the entry point MUST validate and return planned queue outcome without mutating `publish_state`.

When `dry_run` is false, the entry point MUST transition `pending` → `queued` and write queue metadata.

#### Scenario: Real queue from pending

- **WHEN** queue is called with `dry_run` false for a `pending` variant on a `distribution_scheduled` Flow A campaign with valid artifact
- **THEN** variant becomes `queued`, `publish_after_utc` is set, and no LinkedIn API call occurs

#### Scenario: Dry-run queue does not mutate state

- **WHEN** queue is called with `dry_run` true for an eligible `pending` variant
- **THEN** response `status` is `completed`, `dry_run` is true, and variant remains `pending`

### Requirement: Publish due variants service

The worker SHALL expose a publish-due service entry point (for example `publish_linkedin_due_variants(base_path, *, campaign_id=None, variant=None, dry_run=True, publish_now=False, ...)`) that publishes eligible `queued` variants to LinkedIn when due.

Real LinkedIn API calls MUST require `dry_run` false, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`, valid token, and required member URN.

The service MUST read variant text from `artifact_relative_path` and include `source_public_url` in commentary (text post format).

The service MUST NOT upload images or publish to company pages.

On real API success, variant MUST become `published`. On real API failure or content rejection, variant MUST become `failed`.

Configuration errors MUST NOT mark variant `failed`.

Apply phase MUST verify exact current LinkedIn Posts API payload and required headers against official documentation.

#### Scenario: Successful text post publish

- **WHEN** publish-due runs in real mode for a due `queued` variant with valid credentials
- **THEN** LinkedIn receives a personal-profile text post whose commentary includes variant text and blog URL, and variant becomes `published`

#### Scenario: API failure marks failed

- **WHEN** publish-due runs in real mode, LinkedIn API is called, and API returns a publish failure
- **THEN** variant `publish_state` becomes `failed` with stable error code in `linkedin_publication`

#### Scenario: Dry-run publish-due does not call API

- **WHEN** publish-due runs with `dry_run` true for a due `queued` variant
- **THEN** no LinkedIn API call occurs and variant remains `queued`

### Requirement: Cancel publication service

The worker SHALL expose a cancel service entry point (for example `cancel_linkedin_publication(base_path, *, campaign_id, variant, dry_run=True, ...)`) that transitions `queued` → `cancelled`.

Cancel MUST NOT affect `published` variants.

Cancel MUST NOT call LinkedIn API.

#### Scenario: Cancel queued variant

- **WHEN** cancel runs with `dry_run` false for a `queued` variant
- **THEN** variant `publish_state` becomes `cancelled`

#### Scenario: Cancel rejected for published

- **WHEN** cancel is requested for a `published` variant
- **THEN** the operation fails with `linkedin_publish_cancel_not_allowed` and variant remains `published`

### Requirement: Campaign eligibility

Queue, publish-due, and cancel MUST require campaign metadata at `metadata/campaigns/<campaign-id>.json`, `flow` `flow_a`, and campaign `state` `distribution_scheduled`.

Queue MUST require variant `publish_state` `pending` (or `failed` when re-queue retry is supported).

Publish-due MUST require variant `publish_state` `queued` for real publish attempts.

Cancel MUST require variant `publish_state` `queued`.

Artifact existence and hash verification MUST match distribution scheduling rules before queue or publish.

This change MUST NOT transition campaign state to `distribution_complete` or beyond in v1.

#### Scenario: Campaign state unchanged after publish

- **WHEN** a variant is successfully published
- **THEN** campaign `state` remains `distribution_scheduled`

#### Scenario: Queue rejected before distribution_scheduled

- **WHEN** queue is requested for a campaign in state `derivatives_generated`
- **THEN** the operation fails with `linkedin_publish_invalid_campaign_state`

### Requirement: HTTP endpoint POST /queue-linkedin-publication

The worker SHALL expose `POST /queue-linkedin-publication` with API key authentication.

Request body MUST include `campaign_id`, `variant`, and optional `dry_run` (default `true`), `safety_delay_minutes`, `publish_after_utc`.

Request model MUST use `extra="forbid"`.

Response MUST include at minimum: `status`, `campaign_id`, `variant`, `state`, `publish_state`, `dry_run`, `publish_after_utc`, `errors`, `warnings`, `metadata_written`.

#### Scenario: Queue endpoint defaults to dry-run

- **WHEN** request omits `dry_run`
- **THEN** worker treats request as `dry_run` true

#### Scenario: Queue endpoint requires auth

- **WHEN** called without valid API key
- **THEN** request is rejected unauthorized

### Requirement: HTTP endpoint POST /publish-linkedin-due-variants

The worker SHALL expose `POST /publish-linkedin-due-variants` with API key authentication.

Request body MUST include optional `campaign_id`, optional `variant`, optional `dry_run` (default `true`), optional `publish_now` (default `false`).

When `campaign_id` and `variant` are omitted, worker MAY evaluate all eligible queued variants under base path (bounded behavior documented at apply).

Response MUST include per-variant results or summary with `publish_state`, `linkedin_post_urn`, `published_at`, `errors`, `dry_run`.

#### Scenario: Publish-due endpoint defaults to dry-run

- **WHEN** request omits `dry_run`
- **THEN** worker treats request as `dry_run` true and does not call LinkedIn API

#### Scenario: Publish-due invalid body returns 422

- **WHEN** request includes unknown extra fields
- **THEN** API returns HTTP 422

### Requirement: HTTP endpoint POST /cancel-linkedin-publication

The worker SHALL expose `POST /cancel-linkedin-publication` with API key authentication.

Request body MUST include `campaign_id`, `variant`, optional `dry_run` (default `true`).

#### Scenario: Cancel endpoint defaults to dry-run

- **WHEN** cancel request omits `dry_run`
- **THEN** worker validates without mutating `publish_state`

### Requirement: Stable error codes

LinkedIn publication MUST use stable error codes including at minimum:

- `linkedin_publish_campaign_not_found`
- `linkedin_publish_flow_not_allowed`
- `linkedin_publish_invalid_campaign_state`
- `linkedin_publish_variant_not_found`
- `linkedin_publish_variant_not_pending`
- `linkedin_publish_variant_not_queued`
- `linkedin_publish_variant_not_due`
- `linkedin_publish_artifact_missing`
- `linkedin_publish_artifact_hash_changed`
- `linkedin_publish_missing_source_public_url`
- `linkedin_publish_token_missing`
- `linkedin_publish_member_urn_missing`
- `linkedin_publish_token_invalid`
- `linkedin_publish_token_expired`
- `linkedin_publish_insufficient_permission`
- `linkedin_publish_not_enabled`
- `linkedin_publish_api_error`
- `linkedin_publish_content_invalid`
- `linkedin_publish_metadata_write_failed`
- `linkedin_publish_cancel_not_allowed`

#### Scenario: Stable error codes in response

- **WHEN** a known eligibility or configuration failure occurs
- **THEN** `errors[]` contains the documented stable code string

### Requirement: Safety and orchestration boundaries

All LinkedIn publication endpoints MUST default to `dry_run: true`.

This change MUST NOT activate n8n workflows, cron jobs, or automatic publication when `scheduled_at_utc` or `publish_after_utc` elapses without an explicit HTTP request.

This change MUST NOT modify n8n workflow JSON.

No LinkedIn API call MUST occur unless `dry_run` is false, publication is enabled, credentials are valid, member URN is present, and variant is eligible (due or `publish_now`).

Operator review UI is out of scope; cancel endpoint is the v1 pre-publish escape hatch.

#### Scenario: No automatic trigger on schedule

- **WHEN** this change is applied
- **THEN** no background job publishes variants when `scheduled_at_utc` or `publish_after_utc` passes without operator or future orchestration calling publish-due

### Requirement: Test coverage

The repository MUST include `tests/test_linkedin_publication.py` covering at minimum:

- successful queue `pending` → `queued` with `publish_after_utc`
- successful publish-due with mocked LinkedIn client → `published`
- cancel `queued` → `cancelled`
- missing token / missing member URN / not enabled — response fails, variant NOT `failed`
- invalid/expired token / insufficient permission on real API attempt → variant `failed`
- publish-due skips not-yet-due variant unless `publish_now`
- idempotent behavior for already `published`
- dry-run defaults and no mutation on queue/publish/cancel dry-run
- wrong campaign state, missing artifact, hash mismatch
- HTTP auth and 422 validation for all three endpoints
- no n8n workflow JSON changed

#### Scenario: Test module passes

- **WHEN** `pytest` runs after apply
- **THEN** `tests/test_linkedin_publication.py` passes

### Requirement: LinkedIn publication smoke script

The repository MUST provide `deploy/server/run-linkedin-publication-smoke.sh` that:

- defaults to dry-run for all steps
- exercises queue and publish-due dry-run paths (and optionally cancel dry-run)
- supports explicit real mode flags requiring `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true`
- never prints secrets
- reports variant `publish_state` before and after each step

This smoke capability belongs to `linkedin-publication-integration`, not Flow A Core smoke.

#### Scenario: Smoke dry-run queue and publish-due

- **WHEN** smoke script runs without real flags
- **THEN** it calls queue and publish-due with `dry_run: true` without requiring LinkedIn credentials

#### Scenario: Smoke real mode gated

- **WHEN** smoke runs real publish without publication enabled
- **THEN** script reports failure with remediation and does not print tokens

### Requirement: Evidence collector LinkedIn state display

The repository MUST extend `deploy/server/collect-flow-a-smoke-evidence.sh` to optionally report per-variant LinkedIn publication state counts when campaign metadata includes `variants[]` with `publish_state`.

When reported, the summary MUST include counts for `pending`, `queued`, `published`, `failed`, and `cancelled` where present.

This informational display MUST NOT change Flow A Core PASS semantics (`distribution_scheduled` with `linkedin_distribution`).

#### Scenario: Evidence shows queued variants

- **WHEN** evidence collection runs for a campaign with one `queued` and three `pending` variants
- **THEN** script reports queued count 1 and pending count 3 without variant body text

#### Scenario: Flow A Core PASS unchanged

- **WHEN** evidence collection passes worker, public blog, and n8n checks with `distribution_scheduled`
- **THEN** `OVERALL: PASS` is reported even when all variants remain `pending` or `queued`

### Requirement: Operator documentation

Documentation MUST describe:

- LinkedIn Developer App and manual OAuth 2.0 access token
- Required scope `w_member_social` and required `SILVERMAN_LINKEDIN_MEMBER_URN`
- Queue → safety delay → publish-due two-step workflow; cancel before publish
- Default safety delay 120 minutes; future immediate mode via config `0` or `publish_now`
- Personal-profile text post only (commentary with variant text + URL); no image or company page
- Separation from Flow A Core; worker-side scheduling only
- Future operator UI need (out of scope v1)

#### Scenario: Two-step workflow documented

- **WHEN** operator reads LinkedIn publication docs
- **THEN** they find queue and publish-due as separate steps with safety delay and cancel guidance
