## ADDED Requirements

### Requirement: Cancelled events remain visible with calm distinct styling

The Flow A LinkedIn variant supervision console MUST keep cancelled LinkedIn schedule items visible on Week and Month when they fall in the visible local range and pass active filters.

Cancelled chips MUST use a distinct but calm visual treatment and an operator-facing Cancelled label. Styling MUST NOT use the alarming failed/blocked treatment.

Cancelled MUST NOT be labeled or implied as LinkedIn API published. Campaign `flow_a_complete` and blog handoff MUST NOT be equated with LinkedIn API published.

A dedicated Cancelled metric chip is NOT required by this requirement (filters MAY already include publication state `cancelled`).

#### Scenario: Cancelled chip visible on Week

- **WHEN** a LinkedIn variant with display state `cancelled` has a schedule on a local day in the visible Week
- **THEN** Week shows a calm cancelled chip with a Cancelled label for that item

#### Scenario: Cancelled chip visible on Month

- **WHEN** a LinkedIn variant with display state `cancelled` has a schedule on a local day in the visible Month
- **THEN** Month shows a calm cancelled chip with a Cancelled label for that item

#### Scenario: Cancelled is not styled as failed

- **WHEN** a cancelled item and a failed item are both visible
- **THEN** the cancelled treatment is visually distinct from failed/blocked alarm styling

### Requirement: Cancelled EventModal answers what, why, and what next

Opening a cancelled calendar item MUST open the EventModal (not a day-agenda dump and not a restored List) and MUST answer three questions in plain operator language:

1. **What is this?** — identity (campaign/variant/audience/channel) and that the item is a cancelled planned LinkedIn publication (not LinkedIn API published).
2. **Why is it cancelled?** — reason, source/phase, and cancelled timestamp when available from schedule-visibility (or equivalent worker fields); when absent, an honest fallback such as “Cancelled by operator” without inventing facts; raw machine codes only in expandable diagnostics.
3. **What can I do now?** — when reopen is available and the session `canMutate`, present Reopen & reschedule (or equivalent); when reopen is unavailable or the variant is not reopen-eligible, state that explicitly and MUST NOT show fake Edit/reschedule controls that imply mutation.

#### Scenario: Cancelled modal explains identity and non-published meaning

- **WHEN** an operator opens a cancelled LinkedIn chip
- **THEN** the EventModal states the item is cancelled and does not claim LinkedIn API published

#### Scenario: Cancelled modal explains why when fields exist

- **WHEN** schedule-visibility provides cancellation reason and/or cancelled_at_utc for the item
- **THEN** the EventModal presents that information in operator language

#### Scenario: Non-reopenable cancelled item has explicit next-step copy

- **WHEN** an operator opens a cancelled item that is not reopen-eligible (or reopen is temporarily deferred inside the same change)
- **THEN** the modal states what the operator can or cannot do next and does not offer fake Edit controls

### Requirement: Operator can reopen and reschedule from a cancelled EventModal

When the approved worker reopen path is shipped, the console MUST allow an authenticated mutating session (`canMutate`) to reopen an eligible cancelled LinkedIn variant from the EventModal.

The happy path MUST:

1. require explicit confirmation before a real reopen
2. collect a new schedule in operator-local wall time (US-040I ScheduleEditor local-first rules; convert to `new_scheduled_at_utc` only at the typed API boundary)
3. default to dry-run and require explicit confirmation for real (`dry_run` false) commit
4. call the authenticated worker reopen endpoint over HTTP only (ADR-0001)
5. on success, show a toast (not a persistent green success banner), refresh schedule-visibility (and pending-supervision as applicable), and present the item as an editable pending/planned supervision target on the calendar at the new local day/time

Anonymous or read-only sessions MUST NOT execute reopen. Failures MUST surface as a failure toast with plain-language mapping of stable worker codes; the console MUST NOT claim success.

US-040K max-2-per-local-day density product rules MUST NOT be implemented by this requirement; existing interim defer saturation/duplicate-slot worker refusals MAY be mapped to plain language if returned.

If reopen must be temporarily deferred inside the same change, this requirement’s mutation scenarios remain unimplemented and the explicit read-only cancelled modal requirement above MUST still hold — mystery cancelled UX is forbidden either way.

#### Scenario: Reopen success toast and pending return

- **WHEN** a real reopen/reschedule succeeds from the cancelled EventModal
- **THEN** the console shows a success toast, refreshes calendar data, and the variant appears as editable pending (not cancelled) at the new local schedule

#### Scenario: Dry-run reopen does not claim committed restore

- **WHEN** a dry-run reopen succeeds
- **THEN** the toast/outcome indicates dry-run validation and the calendar does not treat the variant as restored until a real reopen succeeds

#### Scenario: Reopen failure toast

- **WHEN** reopen fails (not allowed, time invalid, auth, validation, or saturation/duplicate-slot)
- **THEN** the console shows a failure toast with understandable copy and does not present the variant as pending

#### Scenario: Read-only session cannot reopen

- **WHEN** the session cannot mutate
- **THEN** the cancelled modal does not offer a commitable reopen path

### Requirement: Schedule-visibility exposes cancellation context for console honesty

Authenticated `GET /flow-a/schedule-visibility` LinkedIn items MUST include additive nullable cancellation context sufficient for the cancelled EventModal when `publication_state` / source state is cancelled, including at least:

- `cancelled_at_utc` when known
- `cancellation_phase` when known (`pre_queue` / `post_queue` or equivalent)
- `cancellation_reason` when an operator reason was recorded (secret-safe)
- `reopen_eligible` boolean computed by the worker from reopen eligibility rules

These fields MUST NOT include secrets, tokens, or raw LinkedIn API bodies. Absent optional fields MUST be null/omitted rather than invented.

#### Scenario: Cancelled item includes reopen_eligible

- **WHEN** schedule-visibility returns a cancelled LinkedIn variant
- **THEN** the item includes `reopen_eligible` reflecting whether `POST /reopen-linkedin-variant` would be allowed for that provenance

#### Scenario: Cancellation reason is secret-safe

- **WHEN** a cancellation reason is present on campaign supervision metadata
- **THEN** schedule-visibility may expose that reason string without secrets or raw API payloads

### Requirement: Active cancel remains destructive and reopen-gated

Cancel from an active editable pending event in the EventModal MUST remain behind explicit confirmation, MUST call existing `POST /cancel-linkedin-publication`, and MUST remain irreversible except through the approved reopen path.

After cancel success, the console MUST refresh calendar data so the item shows as cancelled (calm chip) rather than silently disappearing without explanation when still in range.

#### Scenario: Cancel confirmation remains required

- **WHEN** an operator initiates cancel from an active pending EventModal
- **THEN** the console requires explicit confirmation before a real cancel mutation

#### Scenario: Cancel outcome is not LinkedIn API published

- **WHEN** a real cancel succeeds
- **THEN** outcome copy does not claim LinkedIn API published and describes cancelled / auto-queue exclusion in qualified language

### Requirement: US-040J Visual DoD and acceptance gates

US-040J MUST require desktop and mobile Visual DoD evidence (screenshots or equivalent browser-driven capture) covering at least:

- cancelled chip on Week
- cancelled chip on Month
- cancelled modal answering what / why / what next
- reopen/reschedule happy path (or explicit interim read-only cancelled copy if reopen deferred inside the same change)
- failure toast for a blocked/failed reopen (or equivalent failure communication if only read-only shipped)
- mobile cancelled modal

Vitest alone MUST NOT mark US-040J Story accepted.

Operator walkthrough on deployed or explicitly agreed preview MUST confirm cancelled items are understandable and the approved next action is obvious before Story accepted.

US-040J implementation MUST NOT mark BL-015 closed, MUST NOT mark US-040G/H/I Story accepted as a side effect, MUST NOT implement US-040K density product rules unless a hard dependency is recorded, MUST NOT activate public URL / Google OIDC / BFF / user-management, MUST NOT call LinkedIn API publish from the console, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT read/write raw mount paths from the browser.

#### Scenario: Visual DoD required before Story accepted

- **WHEN** US-040J implementation and Vitest evidence exist
- **THEN** status language still leaves Story accepted open until Visual DoD + operator walkthrough complete

#### Scenario: BL-015 and prior UX stories remain open

- **WHEN** US-040J implementation lands
- **THEN** status language does not close BL-015 and does not mark US-040G/H/I Story accepted solely because US-040J shipped

#### Scenario: US-040K remains a follow-up

- **WHEN** US-040J implementation is complete
- **THEN** CURRENT-STATE or equivalent records max-2-per-local-day density enforcement as not delivered by this change
