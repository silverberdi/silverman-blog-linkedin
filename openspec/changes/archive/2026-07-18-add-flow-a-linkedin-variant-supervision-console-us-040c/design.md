## Context

US-040A/B delivered the Flow A LinkedIn variant supervision console as React + TypeScript + Vite under `frontend/linkedin-variant-supervision-console/`, served at `GET /flow-a/console/linkedin-variant-supervision`. Baseline includes:

- Dual first-class List + Month calendar **visibility** (`GET /flow-a/schedule-visibility` + `GET /flow-a/linkedin-variants/pending-supervision`)
- Shared normalized model / store; CSS-grid month + mobile agenda; filters; dark theme
- List Stories 1–3 mutations via US-017 (`POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`)
- `ScheduleEditor` scaffold used only by list defer forms; calendar is visibility-only
- Dry-run default, real-mutation confirmation, enablement display-only, qualified language

US-040C (BL-015) must let operators **modify future unpublished schedules** from Month calendar, mobile agenda, or List through one shared editor—without a second mutation SoT, without LinkedIn API publish, and without browser filesystem writes (ADR-0001).

**Constraints:** browser → worker HTTP only; reuse `save_calendar_atomic` / fingerprint conflict protection for calendar writes; LinkedIn schedule changes remain pending-only via US-017 defer; `pending` / `queued` / `cancelled` / `flow_a_complete` ≠ LinkedIn API published; blog handoff ≠ LinkedIn API published; BL-021 not closed—use interim cadence-reschedule rules until superseded.

## Goals / Non-Goals

**Goals:**

- Shared `ScheduleEditor` entry from List, Month, and mobile agenda for eligible future unpublished items.
- LinkedIn: reuse US-017 defer/reschedule as the only LinkedIn schedule mutation SoT (additive audit/source only if needed).
- Blog/editorial calendar: authenticated worker schedule-update API → canonical `calendar.json` with validation, idempotency, conflict protection, dry-run, audit.
- Cadence/reschedule validation (past, format, saturation, duplicate slots, unsupported states).
- Dry-run visible; explicit confirm for real commits; dual-view refresh + previous/new + related-variant outcome messaging.
- Preserve US-040A/B visibility and list edit/cancel/defer affordances.

**Non-Goals:**

- US-040D public Google auth; US-040E polish beyond mutation UX.
- BFF/DB/user-mgmt/public hosting; LinkedIn API publish; enablement bypass; Flow B.
- Auto-cascading LinkedIn variant schedules when a blog calendar item moves (report as separate overrides unless operator mutates LinkedIn explicitly).
- Closing BL-015 / BL-021 or marking US-040C Story accepted from apply alone.

## Decisions

### D1 — One shared ScheduleEditor; three entry points

**Choice:** Promote `ScheduleEditor` into the single schedule-mutation surface. Month cell, mobile agenda row, and List (defer/reschedule path) open the same editor with the same dry-run + confirmation flow. Preserve separate list edit/cancel panels; do not replace them.

**Why:** AC requires the same editor from all three surfaces and reuse of worker semantics.

**Alternatives considered:** Calendar-only editor distinct from list defer — rejected (second UX/SoT risk). Drag-drop reschedule widgets — rejected (overweight; implies divergent mutation UX).

### D2 — Channel-specific mutation endpoints; unified console orchestration

**Choice:** Console typed client orchestrates by `channel`:

| Channel | Mutation SoT | Endpoint |
|---------|--------------|----------|
| LinkedIn (`pending` only) | US-017 | Existing `POST /defer-linkedin-variant` |
| Blog (editorial calendar) | `calendar.json` | New authenticated `POST /editorial-calendar/update-item-schedule` (path fixed below) |

No unified “mega” mutation endpoint that writes both stores in one opaque call for US-040C. Related LinkedIn variants after a blog reschedule remain **separate overrides** unless the operator also defers them; success UI MUST report that outcome.

**Why:** Preserves LinkedIn pending-only defer contracts and calendar atomic write patterns; avoids inventing a parallel LinkedIn writer.

**Alternatives considered:** Single composite endpoint that always cascades LinkedIn — rejected (violates US-017 single-variant defer semantics and “related variants remained separate” AC). Browser writes `calendar.json` — rejected (ADR-0001 / AC).

### D3 — Editorial calendar schedule-update API

**Choice:** Add:

`POST /editorial-calendar/update-item-schedule`

Authenticated (`require_api_key`). Request body (normative fields refined in delta spec):

- `item_id` (required)
- `new_due_at_utc` (required, ISO-8601 UTC `Z`)
- `dry_run` (optional, default `true`)
- `reason` (optional)
- `idempotency_key` (optional)
- `actor` / `source` (optional; console SHOULD send `source=linkedin_variant_supervision_console`, `actor=operator`)
- `expected_calendar_fingerprint` (optional but recommended; SHA-256 of current raw `calendar.json` as returned by a prior read/visibility response or a dedicated fingerprint field)

Behavior:

1. Load `editorial-calendar/calendar.json`; reject if missing/invalid with stable codes.
2. Locate item by `item_id`; reject `calendar_item_not_found`.
3. Eligibility: only future **unpublished** editorial items may mutate schedule. Allowed statuses: at least `planned`, `scheduled` (and `due` only if still unpublished and not terminal). **Forbidden / read-only:** `completed`, `skipped`, `failed`, and any item whose display/publication mapping is historical published/completed handoff. Reject past `new_due_at_utc` (`calendar_schedule_time_invalid` or equivalent).
4. Validate cadence/reschedule interim rules (D5).
5. Dry-run: validate + return previous/new preview; **no** file write.
6. Real write: update item `due_at_utc`, append schedule-audit entry, bump calendar `updated_at_utc`, persist via existing `save_calendar_atomic` with fingerprint conflict → `calendar_completion_concurrent_update`.
7. MUST NOT call LinkedIn, DeepSeek, ComfyUI, Git, or blog publish/handoff paths.

Response MUST include: status, dry_run flag, `item_id`, `previous_due_at_utc`, `new_due_at_utc`, audit summary, idempotency result, and (when known) `related_linkedin_variants_outcome` hint for the console (`unchanged_separate_overrides` default).

**Why:** Explicit worker contract; reuses atomic persistence already specified for calendar completion writes.

### D4 — LinkedIn schedule mutation remains US-017 defer

**Choice:** Calendar/list schedule edits for LinkedIn `pending` variants call `POST /defer-linkedin-variant` only. Published / queued / cancelled / failed LinkedIn items are read-only in the schedule editor. Additive optional request fields `actor` / `source` MAY be accepted and recorded on `operator_supervision` / `deferral_history` when supplied; omit if already covered by existing `actor` + `reason` without a breaking contract change.

**Why:** AC: “reuse or extend… instead of introducing a second mutation source of truth.”

**Alternatives considered:** New `POST /reschedule-linkedin-variant` — rejected (duplicate SoT). Allow reschedule of `queued` — rejected (US-017 pending-only; queued already past supervision window for defer).

### D5 — Interim cadence / rescheduling validation (until BL-021 closes)

**Choice:** Encode interim rules in worker validation for US-040C (document as interim; supersede when BL-021 defines normative cadence):

| Rule | Blog (calendar) | LinkedIn (defer) |
|------|-----------------|------------------|
| Past / non-future | Reject `new_due_at_utc` ≤ now UTC | Existing `linkedin_supervision_defer_time_invalid` (strictly future) |
| Invalid format | Reject non-canonical UTC `Z` | Existing defer parse/validation |
| Unsupported state | Reject terminal/historical statuses (D3) | Reject non-`pending` |
| Duplicate slot | Reject another **blog** item with the same UTC day key (UTC date of `due_at_utc`) when interim blog density is 1/day | Reject exact duplicate `scheduled_at_utc` for another **pending/queued** variant in the **same campaign** (same instant) |
| Saturation | Reject if target UTC day already has ≥ interim max blog items (default **1** Flow A blog item/day) | Reject if applying the new time would place ≥ **2** variants of the same campaign on the same UTC day **and** within **72h** of another variant’s `scheduled_at_utc` in that campaign (interim alignment with US-020 72h spirit for **schedule intent**; publish-time cadence remains authoritative at send) |

Stable error codes (examples; exact strings fixed in delta specs): `calendar_schedule_time_invalid`, `calendar_schedule_duplicate_slot`, `calendar_schedule_saturation`, `calendar_schedule_unsupported_state`, plus existing LinkedIn supervision codes.

**Why:** US-040C AC requires validation against cadence/rescheduling rules; BL-021 is still open; interim rules keep operators safe without inventing BL-021 closure.

**Alternatives considered:** Block all real calendar mutations until BL-021 closes — rejected (user story requires US-040C now; prerequisite is SHOULD, not MUST). Soft-warn only — rejected (AC requires validation failures communicated).

### D6 — Dry-run, confirmation, dual-view refresh, outcome messaging

**Choice:**

- Default `dry_run=true` for schedule commits (calendar API + LinkedIn defer).
- Real mutation requires explicit confirmation (reuse `ConfirmationFlow`).
- After real success: coordinated refresh of **both** `GET /flow-a/schedule-visibility` and `GET /flow-a/linkedin-variants/pending-supervision` (same pattern as list mutations today).
- Success banner MUST show: affected item identity, previous schedule, new schedule, channel, and whether related LinkedIn variants **changed** or **remained separate overrides** (blog path defaults to separate; LinkedIn self-change is the affected item).

### D7 — Audit persistence

**Choice:**

- **LinkedIn:** Continue `operator_supervision.deferral_history[]` (`previous_scheduled_at_utc`, `new_scheduled_at_utc`, `deferred_at_utc`, `reason`) + idempotency proofs; ensure console supplies reason/idempotency_key; record actor/source per D4.
- **Blog:** Append `schedule_change_history[]` (or equivalent) on the calendar item and/or a calendar-level audit array with: actor, source, timestamp UTC, previous `due_at_utc`, new `due_at_utc`, reason, idempotency key, worker result status. Idempotent replay with same key+payload returns completed without duplicate history rows.

### D8 — Eligibility surfacing in shared model

**Choice:** Extend schedule-visibility / shared model with `schedule_editable: boolean` (and optional `schedule_edit_block_reason`) so Month/agenda/List open the editor only for editable items; published/historical show read-only detail. List keeps existing edit/defer/cancel for pending LinkedIn independently.

### D9 — Stack and calendar UI preserved

**Choice:** Keep React + TypeScript + Vite; CSS-grid month; no new calendar mutation library; no second frontend app/server; static assets continue under worker static path.

### D10 — HTTP boundary / security / deploy

**Choice:** All reads/writes via authenticated worker HTTP (ADR-0001). No n8n Execute Command. No secrets in frontend source, built assets, logs, or browser storage. Path validation confined to editorial base. Deploy remains build frontend → copy static into image / worker tree; no public hosting change.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Interim cadence rules diverge from future BL-021 | Document as interim in CURRENT-STATE + specs; single validation module easy to retarget |
| Blog reschedule leaves LinkedIn times stale vs calendar join | Explicit outcome: “related LinkedIn variants remained separate overrides”; no silent cascade |
| Concurrent calendar editors overwrite | Fingerprint + `calendar_completion_concurrent_update` via `save_calendar_atomic` |
| Operators confuse schedule edit with LinkedIn API publish | Qualified language; dry-run default; no publish calls on this path |
| Scope creep into US-040D/E | Explicit non-goals; tasks exclude public auth and polish beyond mutation UX |

## Migration Plan

1. Implement worker calendar schedule-update + tests; optional additive LinkedIn audit fields.
2. Promote ScheduleEditor + client/store wiring; rebuild static assets.
3. Update CURRENT-STATE / progress-checklist / user-stories only for demonstrated US-040C criteria; leave BL-015 open; US-040D–E not done.
4. Rollback: revert route registration and static assets; calendar file remains valid if writes were atomic; LinkedIn defer remains prior US-017 behavior.

## Open Questions

- Exact response field for schedule-visibility fingerprint (embed `calendar_fingerprint` on schedule-visibility when calendar loads vs require client to omit fingerprint and accept last-write-wins with higher conflict rate). **Default at apply:** include optional `calendar_fingerprint` on schedule-visibility when calendar is readable; client SHOULD send it on real calendar updates.
- Whether `due` status calendar items remain editable if still unpublished. **Default:** editable if not terminal (`completed`/`skipped`/`failed`) and new time is future; otherwise read-only.
- Whether interim LinkedIn same-day saturation is enforced at defer time or warning-only. **Default:** hard reject with stable code (can soften later via BL-021).
