## ADDED Requirements

### Requirement: Console control-center cancel uses existing cancel endpoint (US-085)

The Silverman Authority Manager / LinkedIn console MUST call the existing authenticated worker endpoint `POST /cancel-linkedin-publication` as the **sole** persistence path for operator cancel of not-yet-live LinkedIn variants, including at least:

- `publish_state` `pending` (pre-queue / Scheduled)
- `publish_state` `queued` (post-queue / Waiting to send)

Cancel MUST continue to follow the Cancel publication service contract: dry-run default `true`; real cancel transitions eligible variants to `cancelled` with the appropriate supervision cancellation phase (`pre_queue` for pending, `post_queue` for queued); sets `operator_supervision.auto_queue_eligible` to `false` when persisting; does not call the LinkedIn API; rejects `published` with `linkedin_publish_cancel_not_allowed`; remains irreversible except through the approved US-040J reopen path for reopen-eligible cancellations.

This capability MUST NOT introduce a second cancel HTTP route, MUST NOT treat browser filesystem or raw mounts as cancel SoT, MUST NOT require LinkedIn publication enablement for cancel to succeed (cancel is withdrawal, not publish), and MUST NOT bypass ADR-0001.

#### Scenario: Console cancel pending uses cancel-linkedin-publication

- **WHEN** the console submits a real cancel for a `pending` variant
- **THEN** the worker handles `POST /cancel-linkedin-publication` under existing pending → cancelled semantics and no LinkedIn API call occurs

#### Scenario: Console cancel queued uses cancel-linkedin-publication

- **WHEN** the console submits a real cancel for a `queued` variant
- **THEN** the worker handles `POST /cancel-linkedin-publication` under existing queued → cancelled semantics and no LinkedIn API call occurs

#### Scenario: No second cancel route for US-085

- **WHEN** US-085 console cancel is implemented
- **THEN** persistence uses only existing `POST /cancel-linkedin-publication` and does not add a parallel cancel endpoint

#### Scenario: Cancel does not require publication enablement

- **WHEN** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is false and cancel is requested for an eligible `pending` or `queued` variant with `dry_run` false
- **THEN** cancel may still succeed under existing cancel rules (withdrawal without LinkedIn API) and MUST NOT be blocked solely because publication enablement is off

## MODIFIED Requirements

### Requirement: Safety and orchestration boundaries

All LinkedIn publication endpoints MUST default to `dry_run: true`.

This capability MUST NOT activate n8n workflows, cron jobs, or automatic publication when `scheduled_at_utc` or `publish_after_utc` elapses without an explicit HTTP request.

The repository MAY contain manual, inactive n8n workflow exports for LinkedIn publication orchestration (`"active": false`, HTTP-only per ADR-0001); providing or updating such exports MUST NOT activate them, and activation as scheduled production automation requires separate explicit approval.

No LinkedIn API call MUST occur unless `dry_run` is false, publication is enabled, credentials are valid, member URN is present, and variant is eligible (due or `publish_now`).

The authenticated cancel endpoint remains the pre-publish / not-yet-live withdrawal path. The Silverman Authority Manager / LinkedIn console MAY invoke `POST /cancel-linkedin-publication` for operator control-center cancel of eligible `pending` and `queued` variants (US-085). Cancel MUST NOT call the LinkedIn API and MUST NOT be treated as LinkedIn unpublish of a Live post.

#### Scenario: No automatic trigger on schedule

- **WHEN** this change is applied
- **THEN** no background job publishes variants when `scheduled_at_utc` or `publish_after_utc` passes without operator or future orchestration calling publish-due

#### Scenario: Inactive workflow export does not publish

- **WHEN** an inactive LinkedIn publication workflow export exists in the repository
- **THEN** it does not publish by itself and remains inactive until separately approved activation

#### Scenario: Console cancel is an allowed operator path

- **WHEN** an authenticated console operator cancels an eligible not-yet-live variant via `POST /cancel-linkedin-publication`
- **THEN** the request is a valid worker HTTP cancel (not n8n Execute Command) and does not call the LinkedIn API
