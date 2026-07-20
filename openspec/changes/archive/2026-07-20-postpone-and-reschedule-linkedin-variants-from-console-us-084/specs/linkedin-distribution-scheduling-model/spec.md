## MODIFIED Requirements

### Requirement: Supervised reschedule validation

Defer MUST reject `new_scheduled_at_utc` that is not strictly in the future relative to worker UTC now.

Defer MUST accept variants in `publish_state` **`pending` or `queued`** (US-084 not-yet-live postpone). Defer MUST reject variants that are Live on LinkedIn (`published`), `cancelled`, `failed`, or in-flight `publishing` (when distinguished), with a stable supervision error and no schedule mutation.

Defer MUST store all schedule timestamps in UTC ISO8601.

Defer MUST NOT call LinkedIn API as part of supervised reschedule.

#### Scenario: Future-only defer times

- **WHEN** defer is requested with `new_scheduled_at_utc` equal to or before current UTC time
- **THEN** the operation fails with `linkedin_supervision_defer_time_invalid`

#### Scenario: Defer accepts queued publish state

- **WHEN** defer is requested for a variant with `publish_state` `queued` and a valid future `new_scheduled_at_utc`
- **THEN** the operation is allowed under supervised reschedule validation (subject to density/cadence and other existing checks) and MUST NOT fail solely because the variant is queued

#### Scenario: Defer rejects published variant

- **WHEN** defer is requested for a variant with `publish_state` `published`
- **THEN** the operation fails with a stable supervision error and schedule is unchanged
