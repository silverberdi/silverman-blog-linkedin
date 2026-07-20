## ADDED Requirements

### Requirement: Schedule-visibility marks queued LinkedIn items schedule-editable (US-084)

Authenticated `GET /flow-a/schedule-visibility` LinkedIn items MUST set `schedule_editable` to **true** when `publish_state` / source state is `pending` or `queued` (not Live on LinkedIn), subject to existing session-independent eligibility (not cancelled, not published, not failed, not in-flight publishing when distinguished).

LinkedIn items that are Live on LinkedIn (`published` / `linkedin_api_published`), cancelled, failed, or in-flight publishing MUST remain non-editable for schedule with a clear `schedule_edit_block_reason` (or equivalent) suitable for console plain-language mapping.

This requirement MUST NOT call LinkedIn API and MUST NOT mutate campaign metadata on the read path.

#### Scenario: Queued LinkedIn item is schedule-editable

- **WHEN** schedule-visibility returns a LinkedIn variant with `publish_state` `queued`
- **THEN** `schedule_editable` is true and the item is not labeled LinkedIn API published

#### Scenario: Published LinkedIn item is not schedule-editable

- **WHEN** schedule-visibility returns a LinkedIn variant that is Live on LinkedIn
- **THEN** `schedule_editable` is false with a block reason and postpone must not be offered as a working control

## MODIFIED Requirements

### Requirement: Defer LinkedIn variant service

The worker SHALL expose a defer service entry point (for example `defer_linkedin_variant(base_path, *, campaign_id, variant, new_scheduled_at_utc, dry_run=True, reason=None, idempotency_key=None, ...)`) that reschedules a **not-yet-live** LinkedIn variant in `publish_state` **`pending` or `queued`**.

Defer MUST update variant `scheduled_at_utc` to `new_scheduled_at_utc` (UTC ISO8601).

Defer MUST require `new_scheduled_at_utc` to be strictly after current UTC time.

Defer MUST append an entry to `operator_supervision.deferral_history` with previous and new schedule timestamps.

**Pending path:** Defer MUST NOT change `publish_state` from `pending`. Defer MUST set `operator_supervision.last_action` to `defer`, `operator_supervision.phase` to `pre_queue`, and `operator_supervision.auto_queue_eligible` to `false` (existing pending semantics).

**Queued path (US-084):** Defer MUST **keep** `publish_state` as `queued` (MUST NOT return the variant to `pending`). Defer MUST set `operator_supervision.last_action` to `defer` and append deferral history with audit fields. Defer MUST NOT imply withdrawal of send authorization (cancel remains a separate capability). Due evaluation / publish-due MUST treat the new future `scheduled_at_utc` as not due until that time. Defer MUST NOT call LinkedIn API.

Defer MUST continue to enforce US-040K local-day density and interim cadence/saturation checks against the new schedule for both pending and queued.

In-flight `publishing`, `published`, `cancelled`, and `failed` variants MUST be rejected (stable supervision error) without schedule mutation.

#### Scenario: Defer pending variant updates schedule

- **WHEN** defer runs with `dry_run` false for a `pending` variant with valid future `new_scheduled_at_utc`
- **THEN** `scheduled_at_utc` is updated, `deferral_history` records the change, `publish_state` remains `pending`, and `auto_queue_eligible` is `false`

#### Scenario: Defer queued variant updates schedule and stays queued

- **WHEN** defer runs with `dry_run` false for a `queued` variant with valid future `new_scheduled_at_utc`
- **THEN** `scheduled_at_utc` is updated, `deferral_history` records the change, `publish_state` remains `queued`, and LinkedIn API is not called

#### Scenario: Defer rejected for past timestamp

- **WHEN** defer is requested with `new_scheduled_at_utc` not in the future
- **THEN** the operation fails with `linkedin_supervision_defer_time_invalid` and schedule is unchanged

#### Scenario: Defer rejected for live or cancelled

- **WHEN** defer is requested for a `published` or `cancelled` variant
- **THEN** the operation fails with a stable supervision error and schedule is unchanged
