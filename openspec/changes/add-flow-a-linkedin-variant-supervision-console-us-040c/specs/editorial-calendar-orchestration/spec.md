## ADDED Requirements

### Requirement: Authenticated HTTP schedule update for editorial calendar items

The worker SHALL expose `POST /editorial-calendar/update-item-schedule` protected by API-key authentication (`Depends(require_api_key)`).

The endpoint MUST update the scheduled due time of an existing item in the canonical `{editorial_base}/editorial-calendar/calendar.json` through worker logic only. The browser and n8n MUST NOT write `calendar.json` directly.

Request body MUST include:

- `item_id` (string, required)
- `new_due_at_utc` (ISO-8601 UTC with `Z` suffix, required)
- optional `dry_run` (boolean, default `true`)
- optional `reason` (string)
- optional `idempotency_key` (string)
- optional `actor` (string)
- optional `source` (string)
- optional `expected_calendar_fingerprint` (SHA-256 hex of the current raw calendar file)

The endpoint MUST NOT call LinkedIn publication APIs, DeepSeek, ComfyUI, or Git, and MUST NOT publish blog content or perform blog handoff as part of the schedule update.

#### Scenario: Authenticated schedule update accepts dry-run default

- **WHEN** a client with a valid API key calls `POST /editorial-calendar/update-item-schedule` omitting `dry_run`
- **THEN** the worker validates without mutating `calendar.json`

#### Scenario: Unauthenticated schedule update is rejected

- **WHEN** a client calls `POST /editorial-calendar/update-item-schedule` without a valid API key
- **THEN** the worker rejects the request with existing unauthorized semantics and does not mutate `calendar.json`

#### Scenario: Schedule update does not publish

- **WHEN** `POST /editorial-calendar/update-item-schedule` runs with `dry_run` false for an eligible item
- **THEN** the worker does not call LinkedIn publication APIs and does not publish blog content as part of the request

### Requirement: Calendar schedule-update eligibility and validation

`POST /editorial-calendar/update-item-schedule` MUST locate the target by `item_id` and MUST reject missing items with `calendar_item_not_found`.

The endpoint MUST allow schedule changes only for future unpublished editorial items. Items with terminal or historical statuses `completed`, `skipped`, or `failed` MUST be rejected as unsupported for schedule mutation.

`new_due_at_utc` MUST be canonical UTC `Z` and MUST be strictly after current worker UTC time; otherwise the worker MUST fail with a stable code such as `calendar_schedule_time_invalid` and MUST NOT mutate the calendar.

The endpoint MUST validate interim cadence/rescheduling rules (until superseded by an approved BL-021 definition), including at least:

- duplicate blog slot on the same UTC day as another blog item (`calendar_schedule_duplicate_slot`)
- blog-day saturation when the target UTC day already meets the interim maximum Flow A blog items per day (default 1) (`calendar_schedule_saturation`)
- unsupported publication/calendar states (`calendar_schedule_unsupported_state`)

When `editorial-calendar/calendar.json` is missing or invalid, the endpoint MUST fail with the existing calendar missing/invalid semantics and MUST NOT create a calendar file solely to accept a schedule edit.

#### Scenario: Past due time is rejected

- **WHEN** `new_due_at_utc` is not strictly in the future
- **THEN** the worker returns `calendar_schedule_time_invalid` (or equivalent stable code) and `calendar.json` is unchanged

#### Scenario: Completed item is read-only for schedule

- **WHEN** the target item has `status` `completed`
- **THEN** the worker rejects the update with `calendar_schedule_unsupported_state` (or equivalent) and does not change `due_at_utc`

#### Scenario: Duplicate blog day slot is rejected

- **WHEN** another blog calendar item already occupies the UTC day of `new_due_at_utc` under interim one-blog-per-day rules
- **THEN** the worker returns `calendar_schedule_duplicate_slot` or `calendar_schedule_saturation` and does not mutate the calendar

### Requirement: Calendar schedule-update persistence, conflict protection, and dry-run

When `dry_run` is `true`, the worker MUST validate eligibility and rules and MUST return previous and proposed `due_at_utc` without writing `calendar.json`.

When `dry_run` is `false` and validation succeeds, the worker MUST set the item’s `due_at_utc` to `new_due_at_utc`, update calendar `updated_at_utc`, and persist via existing `save_calendar_atomic` semantics.

When `expected_calendar_fingerprint` is supplied, the worker MUST enforce the same concurrent-update protection as `save_calendar_atomic` and MUST return `calendar_completion_concurrent_update` without overwriting concurrent changes when the fingerprint no longer matches.

Successful real updates MUST NOT claim LinkedIn API published and MUST NOT equate calendar status changes with LinkedIn publication.

#### Scenario: Dry-run does not write calendar.json

- **WHEN** `POST /editorial-calendar/update-item-schedule` runs with `dry_run` true for an eligible item
- **THEN** `calendar.json` bytes remain unchanged and the response includes previous and proposed due times

#### Scenario: Real update persists new due_at_utc atomically

- **WHEN** `POST /editorial-calendar/update-item-schedule` runs with `dry_run` false for an eligible item and a matching fingerprint
- **THEN** the item’s `due_at_utc` becomes `new_due_at_utc` and the calendar is replaced atomically

#### Scenario: Concurrent calendar modification is not overwritten

- **WHEN** a real schedule update supplies an `expected_calendar_fingerprint` that no longer matches on-disk `calendar.json`
- **THEN** the worker returns `calendar_completion_concurrent_update`, does not replace the calendar, and leaves concurrent changes intact

### Requirement: Calendar schedule-change audit and idempotency

Real successful schedule updates MUST persist a traceable audit record for the change including at least:

- actor and/or source when supplied (console SHOULD supply `source=linkedin_variant_supervision_console`)
- timestamp UTC
- previous `due_at_utc`
- new `due_at_utc`
- reason when supplied
- idempotency key when supplied
- worker result status

When `idempotency_key` is provided and a prior successful non-dry-run operation used the same key with an identical payload fingerprint, replay MUST return completed success without appending a duplicate audit entry and without a second divergent write.

When `idempotency_key` is provided but the payload differs from the stored proof, the operation MUST fail with a stable idempotency conflict code and MUST NOT mutate the calendar.

#### Scenario: Audit record captures previous and new due times

- **WHEN** a real schedule update succeeds
- **THEN** the persisted audit includes previous `due_at_utc`, new `due_at_utc`, timestamp, and any supplied reason/actor/source/idempotency key

#### Scenario: Idempotent replay does not duplicate audit

- **WHEN** the same `idempotency_key` and identical payload are submitted twice with `dry_run` false
- **THEN** the second call returns completed without a second audit entry for that key
