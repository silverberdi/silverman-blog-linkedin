## ADDED Requirements

### Requirement: Week and Month surface local-day density (US-040K)

The Flow A LinkedIn variant supervision console MUST surface operator-local day density on Week and Month so that:

- a local day with **2** density members looks **full** (calm visual cue — not failed/blocked alarm styling)
- a local day with **3+** density members remains **visible** with a distinct over-capacity cue and no hidden chips
- a conflict attempt (placing a third member) is understandable **before** commit when using ScheduleEditor / reopen schedule pick

Density membership MUST follow the same inclusion set as the worker US-040K rule (live planned LinkedIn pending/queued including deferred pending, published items still shown, blog items shown; cancelled and failed excluded).

Day bucketing MUST use US-040I `localDayKey` (operator-local), not UTC day.

#### Scenario: Full day cue at two publications

- **WHEN** a local day has exactly 2 density members on Week or Month
- **THEN** the console presents a calm full-day density cue for that day

#### Scenario: Over-full day remains visible

- **WHEN** a local day has 3 or more density members
- **THEN** all events remain visible on Week/Month with an over-capacity cue and chips are not removed to satisfy the cap

#### Scenario: Local midnight boundary matches US-040I

- **WHEN** an item’s UTC timestamp falls near local midnight
- **THEN** density occupancy for that item uses the same local day as Week/Month placement

### Requirement: Client-side density validation on reschedule defer and reopen

Reschedule/defer (ScheduleEditor) and cancelled reopen schedule flows MUST validate the max-2 operator-local-day cap **client-side** using the current schedule-visibility snapshot before commit, and MUST still rely on worker enforcement.

Prefer prevention in the picker (disable or warn saturated local days where `others_on_day >= 2` excluding the item being edited) over cryptic post-submit codes alone.

Anonymous or read-only sessions (`canMutate` false) MUST NOT commit schedule changes. Dry-run default and confirm-for-real semantics MUST remain.

#### Scenario: Picker blocks or warns a third placement

- **WHEN** an authenticated mutating operator selects a target local day that already has 2 density members (excluding the item being moved)
- **THEN** the console blocks or clearly warns before commit with plain language that the day already has 2 publications

#### Scenario: Client and server both refuse over-capacity

- **WHEN** a commit is attempted that would exceed 2 density members on the target local day
- **THEN** the console does not claim success and surfaces a failure outcome if the worker refuses

### Requirement: Plain-language density and timezone errors

The console MUST map US-040K density and timezone worker codes to plain-language toast/modal copy. Density messaging MUST be human (e.g. “This day already has 2 publications”) and MUST NOT rely only on raw `*_saturation` or machine codes in the primary UI.

Expandable diagnostics MAY still show raw codes.

#### Scenario: Density refusal is plain language

- **WHEN** defer or reopen fails with the LinkedIn local-day density code
- **THEN** the operator-facing toast/modal states that the day already has 2 publications (or equivalent plain language)

#### Scenario: Timezone failure is understandable

- **WHEN** a mutation fails because operator timezone is missing or invalid
- **THEN** the console communicates a clear blocked state without claiming schedule success

### Requirement: Fix path for grandfathered over-capacity days

For local days that already have 3+ density members, the console MUST offer a clear path to fix density by moving events through the EventModal / ScheduleEditor (reschedule/defer or reopen flows as applicable). The console MUST NOT silently delete or auto-redistribute events.

#### Scenario: Operator can open and move an event off an over-full day

- **WHEN** an operator opens an event on an over-full local day and reschedules it to an under-capacity local day
- **THEN** the happy path remains EventModal → schedule edit → toast → calendar refresh, and the source day density decreases after a successful real mutation

### Requirement: US-040K Visual DoD and operator walkthrough gates

Automated tests (including Vitest) are necessary but MUST NOT be treated as sufficient for US-040K Story accepted.

US-040K MUST capture Visual DoD evidence (desktop ≈1280 and mobile ≈375, or equivalent) for at least:

- local day at 2 publications (full cue)
- attempt to place a 3rd (plain-language block)
- Month density cue
- existing 3+ day still visible with fix path
- local-midnight boundary occupancy

**Story accepted** / Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed or explicitly agreed preview console and confirms the density rule is obvious and prevents a spammy plan.

Vitest/checkbox completion alone MUST NOT imply Story accepted. BL-015 MUST remain open until the backlog completion outcome is operator-validated. US-040G/H/I/J Story accepted MUST NOT be closed as a side effect of US-040K implementation.

#### Scenario: Vitest alone does not accept the story

- **WHEN** US-040K implementation and Vitest suites pass without Visual DoD evidence and operator walkthrough
- **THEN** product status MUST NOT mark US-040K Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough required before Story accepted

- **WHEN** Visual DoD evidence exists and the operator completes a walkthrough confirming max-2 density UX intent
- **THEN** Story accepted MAY be recorded; otherwise it remains open

### Requirement: US-040K console scope preserves G–J baselines

US-040K MUST preserve:

- Week default + Month secondary calendar-first chrome (no List restoration as primary)
- EventModal + toast feedback
- operator-local primary clock and `*_utc` wire fields (US-040I)
- cancelled reopen path (US-040J)
- session states and `canMutate` gating
- dry-run default + confirm for real
- worker HTTP-only SoT (ADR-0001)
- qualified publication language

US-040K MUST NOT activate public URL / Google OIDC / BFF / user-management, MUST NOT call LinkedIn API publish from the console, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT write editorial mounts from the browser.

#### Scenario: Prior console baselines remain

- **WHEN** US-040K is implemented
- **THEN** Week remains default, EventModal remains the event surface, local-time helpers remain authoritative for display/placement, and reopen remains available for eligible cancelled items

#### Scenario: No LinkedIn API publish from density UX

- **WHEN** density cues or density refusals are exercised in the console
- **THEN** the console does not invoke LinkedIn publication and only uses worker HTTP read/mutation endpoints

## MODIFIED Requirements

### Requirement: Operator can reopen and reschedule from a cancelled EventModal

When the approved worker reopen path is shipped, the console MUST allow an authenticated mutating session (`canMutate`) to reopen an eligible cancelled LinkedIn variant from the EventModal.

The happy path MUST:

1. require explicit confirmation before a real reopen
2. collect a new schedule in operator-local wall time (US-040I ScheduleEditor local-first rules; convert to `new_scheduled_at_utc` only at the typed API boundary)
3. default to dry-run and require explicit confirmation for real (`dry_run` false) commit
4. call the authenticated worker reopen endpoint over HTTP only (ADR-0001)
5. on success, show a toast (not a persistent green success banner), refresh schedule-visibility (and pending-supervision as applicable), and present the item as an editable pending/planned supervision target on the calendar at the new local day/time

Anonymous or read-only sessions MUST NOT execute reopen. Failures MUST surface as a failure toast with plain-language mapping of stable worker codes; the console MUST NOT claim success.

US-040K max-2-per-local-day density product rules MUST be enforced on reopen schedule pick and commit (client-side prevention + worker refusal mapping with plain-language density errors). Existing interim defer saturation/duplicate-slot worker refusals MUST remain mapped to plain language when returned.

If reopen must be temporarily deferred inside the same change, this requirement’s mutation scenarios remain unimplemented and the explicit read-only cancelled modal requirement above MUST still hold — mystery cancelled UX is forbidden either way.

#### Scenario: Reopen success toast and pending return

- **WHEN** a real reopen/reschedule succeeds from the cancelled EventModal
- **THEN** the console shows a success toast, refreshes calendar data, and the variant appears as editable pending (not cancelled) at the new local schedule

#### Scenario: Dry-run reopen does not claim committed restore

- **WHEN** a dry-run reopen succeeds
- **THEN** the toast/outcome indicates dry-run validation and the calendar does not treat the variant as restored until a real reopen succeeds

#### Scenario: Reopen failure toast

- **WHEN** reopen fails (not allowed, time invalid, auth, validation, saturation/duplicate-slot, or local-day density)
- **THEN** the console shows a failure toast with understandable copy and does not present the variant as pending

#### Scenario: Read-only session cannot reopen

- **WHEN** the session cannot mutate
- **THEN** the cancelled modal does not offer a commitable reopen path

#### Scenario: Reopen onto a full local day is blocked in plain language

- **WHEN** the operator attempts reopen onto a local day that already has 2 density members
- **THEN** the console blocks or fails with plain language that the day already has 2 publications and does not claim success
