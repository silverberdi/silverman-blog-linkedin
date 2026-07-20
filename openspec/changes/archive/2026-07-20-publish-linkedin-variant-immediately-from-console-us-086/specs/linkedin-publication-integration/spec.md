## ADDED Requirements

### Requirement: Console control-center publish now uses existing publish-due endpoint (US-086)

The Silverman Authority Manager / LinkedIn console MUST call the existing authenticated worker endpoint `POST /publish-linkedin-due-variants` as the **sole** LinkedIn API publish persistence path for operator **publish now** of eligible not-yet-live LinkedIn variants, including at least:

- `publish_state` `queued` (Waiting to send) with `publish_now: true` and `auto_queue_pending: false`
- `publish_state` `pending` (Scheduled) with `publish_now: true` and `auto_queue_pending: true` when the variant is not excluded by supervision rules that `publish_now` must not bypass

Requests MUST be **targeted** with `campaign_id` and `variant`. Dry-run MUST default to `true`. Real publish (`dry_run` false) MUST require the console’s explicit confirmation path and MUST fail closed when `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is off.

Publish-due MUST continue to enforce existing safeguards: duplicate-publication / once-only protection with URN evidence preservation; publish-time sequence and cadence guards (`publish_now` bypasses only ordinary timing gates, never sequence/cadence/evidence fail-closed/supervision exclusions/deferred time); no LinkedIn API call on dry-run.

On successful real publish of the targeted variant, the response MUST include traceable publication identity (`linkedin_post_urn` on the variant result) suitable for operator verification.

This capability MUST NOT introduce a second LinkedIn publish HTTP route, MUST NOT treat browser filesystem or raw mounts as publish SoT, MUST NOT bypass ADR-0001, and MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` for real publish.

#### Scenario: Console publish now for queued uses publish-linkedin-due-variants

- **WHEN** the console submits a real publish now for a `queued` variant
- **THEN** the worker handles `POST /publish-linkedin-due-variants` with `campaign_id`, `variant`, `publish_now` true, and `dry_run` false under existing queued publish semantics

#### Scenario: Console publish now for pending uses auto_queue_pending plus publish_now

- **WHEN** the console submits a real publish now for an eligible `pending` variant
- **THEN** the worker handles `POST /publish-linkedin-due-variants` with `auto_queue_pending` true and `publish_now` true under existing auto-queue then publish semantics

#### Scenario: Real publish now fails closed when not enabled

- **WHEN** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is false and publish-due is requested with `dry_run` false and `publish_now` true for an eligible variant
- **THEN** the operation fails closed with a stable not-enabled error, `publish_state` is not advanced to published as a successful send, and no LinkedIn API call occurs

#### Scenario: Cadence and sequence still block under publish_now

- **WHEN** publish-due runs with `publish_now` true for a variant that is sequence-blocked or cadence-blocked
- **THEN** the variant is reported blocked with the existing stable codes, `publish_state` is unchanged, and no LinkedIn API call occurs for that variant

#### Scenario: Successful real publish returns URN evidence

- **WHEN** real publish now succeeds for a targeted variant with LinkedIn publication enabled
- **THEN** the variant result includes `linkedin_post_urn` (and published evidence) suitable for operator verification and once-only preservation

#### Scenario: No second publish route for US-086

- **WHEN** US-086 console publish now is implemented
- **THEN** LinkedIn API publish persistence uses only existing `POST /publish-linkedin-due-variants` and does not add a parallel publish endpoint

## MODIFIED Requirements

### Requirement: Safety and orchestration boundaries

All LinkedIn publication endpoints MUST default to `dry_run: true`.

This capability MUST NOT activate n8n workflows, cron jobs, or automatic publication when `scheduled_at_utc` or `publish_after_utc` elapses without an explicit HTTP request.

The repository MAY contain manual, inactive n8n workflow exports for LinkedIn publication orchestration (`"active": false`, HTTP-only per ADR-0001); providing or updating such exports MUST NOT activate them, and activation as scheduled production automation requires separate explicit approval.

No LinkedIn API call MUST occur unless `dry_run` is false, publication is enabled, credentials are valid, member URN is present, and variant is eligible (due or `publish_now`).

The authenticated cancel endpoint remains the pre-publish / not-yet-live withdrawal path. The Silverman Authority Manager / LinkedIn console MAY invoke `POST /cancel-linkedin-publication` for operator control-center cancel of eligible `pending` and `queued` variants (US-085). Cancel MUST NOT call the LinkedIn API and MUST NOT be treated as LinkedIn unpublish of a Live post.

The Silverman Authority Manager / LinkedIn console MAY invoke `POST /publish-linkedin-due-variants` for operator control-center **publish now** of eligible not-yet-live variants (US-086), with targeted `campaign_id` + `variant`, `publish_now: true`, and `auto_queue_pending` when publishing from `pending`. Real console publish now MUST fail closed when publication enablement is off and MUST NOT bypass duplicate-publication, sequence, or cadence safeguards.

#### Scenario: No automatic trigger on schedule

- **WHEN** this change is applied
- **THEN** no background job publishes variants when `scheduled_at_utc` or `publish_after_utc` passes without operator or future orchestration calling publish-due

#### Scenario: Inactive workflow export does not publish

- **WHEN** an inactive LinkedIn publication workflow export exists in the repository
- **THEN** it does not publish by itself and remains inactive until separately approved activation

#### Scenario: Console cancel is an allowed operator path

- **WHEN** an authenticated console operator cancels an eligible not-yet-live variant via `POST /cancel-linkedin-publication`
- **THEN** the request is a valid worker HTTP cancel (not n8n Execute Command) and does not call the LinkedIn API

#### Scenario: Console publish now is an allowed operator path

- **WHEN** an authenticated console operator runs publish now for an eligible not-yet-live variant via `POST /publish-linkedin-due-variants` with `publish_now` true
- **THEN** the request is a valid worker HTTP publish-due (not n8n Execute Command) and LinkedIn API calls occur only when dry-run is false, publication is enabled, and existing eligibility/safeguards allow
