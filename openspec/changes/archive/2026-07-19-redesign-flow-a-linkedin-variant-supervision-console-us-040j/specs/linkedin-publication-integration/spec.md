## ADDED Requirements

### Requirement: Reopen cancelled LinkedIn variant service

The worker SHALL expose a reopen/reschedule-from-cancelled service entry point (HTTP surface: authenticated `POST /reopen-linkedin-variant` or an equivalent kebab-case path fixed at apply) that transitions an eligible `cancelled` Flow A LinkedIn variant to editable `pending` with a new future schedule in one atomic mutation.

Request body MUST include `campaign_id`, `variant`, and `new_scheduled_at_utc` (strictly after now in absolute worker UTC time). Optional fields MUST include `dry_run` (default `true`), `reason`, `idempotency_key`, and MAY include `actor` / `source` for audit attribution (console SHOULD supply a stable console source).

On successful real reopen (`dry_run` false), the worker MUST:

- set variant `publish_state` to `pending` (MUST NOT set `queued` and MUST NOT call the LinkedIn publication API)
- set `scheduled_at_utc` to the validated `new_scheduled_at_utc`
- set `operator_supervision.auto_queue_eligible` to `true` (strategy-driven eligibility restored; BL-007 still applies due-time, sequence, cadence, and enablement at queue/publish time)
- set `operator_supervision.last_action` to `reopen` (or equivalent stable reopen action name), `phase` to `pre_queue`, and `last_action_at_utc`
- archive any prior `operator_supervision.cancellation` into an append-only history list and record a `reopen_history` (or equivalent) entry with previous and new schedule timestamps
- preserve draft content hashes and MUST NOT invent LinkedIn API published evidence

Dry-run MUST validate eligibility and schedule rules without mutating campaign metadata.

Reopen MUST require campaign metadata at `metadata/campaigns/<campaign-id>.json`, `flow` `flow_a`, and campaign `state` `distribution_scheduled` (same eligibility family as cancel/defer unless a stable existing code already covers the failure).

#### Scenario: Real reopen restores pending with new schedule

- **WHEN** reopen runs with `dry_run` false for an eligible `cancelled` variant and a future `new_scheduled_at_utc`
- **THEN** `publish_state` becomes `pending`, `scheduled_at_utc` equals the new time, `auto_queue_eligible` is `true`, and no LinkedIn API call occurs

#### Scenario: Dry-run reopen does not mutate

- **WHEN** reopen runs with `dry_run` true (or omitted) for an eligible cancelled variant
- **THEN** the worker validates without changing `publish_state`, `scheduled_at_utc`, or supervision history writes

#### Scenario: Reopen does not auto-queue

- **WHEN** a real reopen succeeds
- **THEN** the variant remains `pending` (not `queued`) and is not published to LinkedIn as part of reopen

### Requirement: Reopen eligibility and fail-closed refusals

Reopen MUST accept only variants whose `publish_state` is `cancelled` and whose cancellation provenance is reopen-eligible:

- `operator_supervision.cancellation.phase` `pre_queue` — eligible
- `operator_supervision.cancellation.phase` `post_queue` (queued then cancelled before LinkedIn API publish) — eligible; result state MUST still be `pending`, not `queued`
- cancellation originating from the failed-state recovery cancel path (`failed` → `cancelled` / recovery cancellation evidence) — **not** eligible

Reopen MUST refuse `published`, `pending`, `queued`, and `failed` variants, and MUST refuse ineligible cancelled variants, with a stable machine-readable code such as `linkedin_reopen_not_allowed` (exact code fixed at apply and mapped in console errors).

Reopen MUST reject `new_scheduled_at_utc` that is not strictly after now with a stable time-invalid code (reuse or mirror defer’s time-invalid family).

Interim duplicate-slot / same-campaign saturation checks already applied to defer MAY also apply to reopen’s new schedule with stable codes; US-040K max-2-per-local-day product enforcement MUST NOT be introduced by this requirement.

#### Scenario: Pre-queue cancelled variant can be reopened

- **WHEN** reopen is requested for a `cancelled` variant with cancellation phase `pre_queue` and a future schedule
- **THEN** the operation is allowed (subject to dry-run/auth/idempotency) and can restore `pending`

#### Scenario: Post-queue cancelled variant reopens to pending not queued

- **WHEN** a real reopen succeeds for a `cancelled` variant with cancellation phase `post_queue`
- **THEN** `publish_state` becomes `pending` and is not `queued`

#### Scenario: Failed-cancellation reopen is refused

- **WHEN** reopen is requested for a variant cancelled from `failed` via the recovery cancellation path
- **THEN** the operation fails with a stable reopen-not-allowed code and metadata is unchanged

#### Scenario: Past schedule on reopen is refused

- **WHEN** reopen supplies `new_scheduled_at_utc` that is not strictly after now
- **THEN** the operation fails with a stable time-invalid code and metadata is unchanged

### Requirement: HTTP endpoint POST /reopen-linkedin-variant

The worker SHALL expose authenticated `POST /reopen-linkedin-variant` (or the equivalent path chosen at apply) with API key authentication.

Request body MUST include `campaign_id`, `variant`, `new_scheduled_at_utc`, optional `dry_run` (default `true`), optional `reason`, optional `idempotency_key`, and MAY include optional `actor` and `source`.

Responses MUST be structured JSON, MUST NOT include secrets or raw LinkedIn API bodies, and MUST expose enough fields for the console to toast success/failure (`status`, `dry_run`, `campaign_id`, `variant`, `publish_state`, `scheduled_at_utc` on success; stable error code on failure).

Idempotent replay with the same key and equivalent payload MUST NOT double-append reopen history.

#### Scenario: Reopen endpoint defaults to dry-run

- **WHEN** a reopen request omits `dry_run`
- **THEN** the worker validates without mutating campaign metadata

#### Scenario: Unauthorized reopen is rejected

- **WHEN** reopen is attempted without a valid API key
- **THEN** the worker returns unauthorized and does not mutate campaign metadata

#### Scenario: Idempotent reopen replay does not double-write

- **WHEN** a successful real reopen is repeated with the same idempotency key and equivalent payload
- **THEN** the worker returns a successful replay outcome without appending a second reopen history entry

### Requirement: Cancel remains irreversible except via reopen

Cancel via `POST /cancel-linkedin-publication` MUST remain a destructive operator action that moves eligible variants to `cancelled` and excludes them from strategy-driven auto-queue.

After US-040J, cancel MUST be irreversible **except** through the approved reopen/reschedule-from-cancelled path defined in this change. No other existing endpoint (`defer`, `correct`, queue, publish-due) MUST silently restore `cancelled` → `pending`.

Documentation and operator-facing copy that previously stated cancel is irreversible through existing endpoints MUST be treated as superseded for reopen-eligible cancellations only.

#### Scenario: Defer does not reopen cancelled

- **WHEN** `POST /defer-linkedin-variant` is requested for a `cancelled` variant
- **THEN** the operation fails under existing pending-only defer rules and does not restore `pending`

#### Scenario: Only reopen restores cancelled to pending

- **WHEN** an eligible cancelled variant is restored to `pending` with a new schedule
- **THEN** persistence uses the reopen endpoint/service and not cancel, defer, or correct

## MODIFIED Requirements

### Requirement: Cancel publication service

The worker SHALL expose a cancel service entry point that transitions `queued -> cancelled`, `pending -> cancelled`, or `failed -> cancelled`.

Cancel from `pending` MUST record `operator_supervision` cancellation audit with `phase` `pre_queue`.

Cancel from `queued` MUST record `operator_supervision` cancellation audit with `phase` `post_queue` (or preserve existing `linkedin_publication.cancelled_at` alongside `operator_supervision`).

Cancel from `failed` MUST preserve latest publication evidence and all attempt/recovery history, append a `recovery_cancelled` event tied to the latest attempt, and report attempt/retry counters.

Cancel MUST set `operator_supervision.auto_queue_eligible` to `false` when persisting cancellation.

Cancel MUST NOT affect `published` variants and MUST NOT call LinkedIn API.

Cancel MUST remain irreversible except through the approved US-040J reopen/reschedule-from-cancelled path for reopen-eligible cancellations. Cancel MUST NOT itself restore `pending`.

#### Scenario: Cancel queued variant

- **WHEN** cancel runs with `dry_run` false for a `queued` variant
- **THEN** variant `publish_state` becomes `cancelled` under existing post-queue behavior

#### Scenario: Cancel pending variant during supervision

- **WHEN** cancel runs with `dry_run` false for a `pending` variant
- **THEN** variant `publish_state` becomes `cancelled` and `operator_supervision.cancellation.phase` is `pre_queue`

#### Scenario: Cancel failed variant preserves recovery evidence

- **WHEN** cancel runs with `dry_run` false for a failed or retry-exhausted variant
- **THEN** variant becomes `cancelled`, its publication attempts remain unchanged, one recovery cancellation event is appended, and no LinkedIn API call occurs

#### Scenario: Cancel rejected for published

- **WHEN** cancel is requested for a `published` variant
- **THEN** operation fails with `linkedin_publish_cancel_not_allowed` and variant remains `published`

#### Scenario: Cancel does not reopen

- **WHEN** cancel completes successfully
- **THEN** the variant remains `cancelled` until an approved reopen succeeds
