## MODIFIED Requirements

### Requirement: Schedule items appear on the correct calendar day

The Month calendar MUST show each included Flow A blog post and LinkedIn variant on the correct **operator-local** calendar day according to the local calendar date of the stored UTC timestamp (`scheduled_at_utc` for LinkedIn; mapped `due_at_utc` for blog) in the browser’s timezone.

Week day columns MUST use the same local-day bucketing rule so Week and Month cannot disagree about which local day an item occupies.

UTC day-of-month derived solely from the `Z` timestamp MUST NOT be the primary placement rule after US-040I.

Each calendar item presentation MUST include at least:

- title or campaign label
- campaign id where available
- variant id where available
- audience where available
- channel (`blog` or `linkedin`)
- publication state (operator-facing display state)
- scheduled time (operator-local interpretation with timezone cue on Week chips and in EventModal; Month chips MAY omit clock time when density requires it, with full local datetime available in the EventModal)

#### Scenario: LinkedIn pending variant lands on local calendar day

- **WHEN** a LinkedIn variant has `scheduled_at_utc` whose operator-local calendar date falls on a day in the visible local month
- **THEN** the Month calendar places that item on that local day with channel `linkedin` and the required identity/state/time fields

#### Scenario: Blog calendar item lands on local due day

- **WHEN** an editorial calendar blog item has `due_at_utc` whose operator-local calendar date falls on a day in the visible local month and is included by the schedule-visibility read
- **THEN** the Month calendar places that item on that local day with channel `blog` and the required identity/state/time fields

#### Scenario: Near-midnight item is not placed on the wrong local day

- **WHEN** a stored UTC instant falls on a different UTC calendar date than the operator’s local calendar date
- **THEN** Week and Month place the item on the operator-local calendar date, not the UTC calendar date

### Requirement: Explicit timezone handling for schedules

The console MUST use **operator-local** date and time as the primary visible clock for routine Week, Month, and EventModal schedule displays, with a visible timezone cue (for example a short timezone name such as `CST`).

UTC MAY remain the storage and worker wire format (`*_utc` fields). Raw UTC ISO values and UTC day keys MAY appear only in expandable diagnostics or secondary technical detail — they MUST NOT be the primary routine clock.

Calendar day placement for Week and Month MUST follow the operator-local day-bucketing rule based on stored UTC timestamps interpreted in the browser timezone.

Routine empty, error, and help copy MUST NOT instruct the operator to “think in UTC” or enter UTC wall-clock digits for normal schedule work.

#### Scenario: Primary displays use local time with timezone cue

- **WHEN** an item with `scheduled_at_utc` is shown on a Week chip, in Month-driven EventModal detail, or in the EventModal schedule line
- **THEN** the primary presentation uses operator-local date and/or time with a visible timezone cue

#### Scenario: UTC is diagnostic-only for routine work

- **WHEN** an operator views an event without expanding diagnostics
- **THEN** the primary surface does not require reading or entering UTC as the routine clock

#### Scenario: Routine copy does not coach UTC thinking

- **WHEN** the operator reads ScheduleEditor help, empty-state guidance, or mapped `*_time_invalid` error copy
- **THEN** the copy does not instruct the operator to think in UTC for routine edits

### Requirement: Shared schedule editor from calendar entry points

The Flow A LinkedIn variant supervision console MUST allow an operator to select a future unpublished schedule item from the Week view, the Month calendar view, or mobile day/agenda equivalents and open the **same** schedule editor component (embedded in the EventModal after US-040H).

The schedule editor MUST collect a new schedule value in **operator-local** wall time (with timezone cue), convert to the existing worker `*_utc` wire fields only at the typed API client boundary, accept an optional reason, present dry-run vs real mode, and require explicit confirmation before a committed (`dry_run` false) schedule change.

Client-side and operator-facing validation MUST enforce that the new schedule is strictly after now in absolute time, explained in local terms. Moving an event earlier than its previous schedule MUST be allowed when the new absolute time is still after now. The worker remains authoritative for absolute-time rejection codes.

Published or historical items MUST open as read-only (or refuse schedule mutation) and MUST NOT offer a commit path that would rewrite their schedule.

#### Scenario: Week opens shared schedule editor for editable item

- **WHEN** an operator selects a future unpublished editable item from the Week view
- **THEN** the console opens the same schedule editor used by Month and mobile day/agenda equivalents for that item

#### Scenario: Month opens the same schedule editor

- **WHEN** an operator selects a future unpublished editable item from the Month calendar
- **THEN** the console opens the same schedule editor instance/path as Week

#### Scenario: Published historical item is read-only for schedule

- **WHEN** an operator selects a published or otherwise historical non-editable item
- **THEN** the console does not allow a committed schedule change for that item

#### Scenario: Schedule editor is local-first at the API boundary

- **WHEN** an operator submits a new schedule from ScheduleEditor
- **THEN** the picker value is interpreted as operator-local wall time and the typed client sends the existing `new_scheduled_at_utc` or `new_due_at_utc` field as UTC ISO without requiring the operator to enter UTC digits

#### Scenario: Earlier-than-previous future move is allowed

- **WHEN** an operator chooses a new local time that is still strictly after now but earlier than the item’s previous schedule
- **THEN** the console does not block the change solely because it is earlier than the previous schedule

## ADDED Requirements

### Requirement: Operator-local Week and Month navigation (US-040I)

Week and Month navigation cursors (Today / This week, previous/next week, previous/next month, week and month labels) MUST be based on the operator’s **local** calendar, not UTC calendar weeks or months as the primary chrome.

Week labels and Month labels MUST NOT present `(UTC)` as the primary clock identity after US-040I.

#### Scenario: Today uses local calendar

- **WHEN** an operator activates Today / This week from Week
- **THEN** the Week cursor returns to the local week containing the operator’s local today

#### Scenario: Month label is local

- **WHEN** an operator views Month
- **THEN** the month label reflects the operator-local month without a primary `(UTC)` clock label

### Requirement: US-040I Visual DoD and acceptance gates

US-040I MUST require desktop and mobile Visual DoD evidence (screenshots or equivalent browser-driven capture) covering at least:

- local times on Week with timezone cue
- local times on Month / EventModal with timezone cue
- near-midnight day placement (item on correct local day)
- reschedule earlier-but-still-future
- proof that routine UI does not force UTC thinking (ScheduleEditor labels/help and primary surfaces)

Vitest or component assertions alone MUST NOT be treated as sufficient for Story accepted.

US-040I Story accepted and Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed console or an explicitly agreed preview and confirms the local-time UX feels coherent in the operator’s timezone.

Implementation commit and “business outcome demonstrated” MAY occur before that gate. BL-015 MUST remain open until the backlog completion outcome is operator-validated; shipping US-040I code MUST NOT close BL-015 by itself.

US-040I MUST NOT mark US-040G or US-040H Story accepted as a side effect of this change.

If browser capture is unavailable in the implementation environment, status language MUST record that limitation and MUST leave Visual DoD / Story-accepted gates open.

#### Scenario: Visual DoD scenes are required

- **WHEN** US-040I claims visual validation complete for Story accepted
- **THEN** desktop and mobile evidence exists for local times with timezone cue on Week/Month/modal, near-midnight local-day placement, earlier-but-still-future reschedule, and absence of routine UTC coaching

#### Scenario: Vitest alone does not accept the story

- **WHEN** only Vitest or component assertions have passed
- **THEN** status language does not mark US-040I Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough gate blocks Story accepted

- **WHEN** implementation is complete but the operator walkthrough on deployed or agreed preview has not confirmed local-time UX
- **THEN** US-040I remains not Story accepted and BL-015 remains open

### Requirement: US-040I scope preserves baselines and defers J–K products

US-040I MUST NOT mark BL-015 closed or US-040I Story accepted by implementation alone.

US-040I MUST preserve:

- React + TypeScript + Vite same-origin static delivery
- typed injectable-auth API client
- shared normalized frontend model fed by worker HTTP reads
- ScheduleEditor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog) and existing correct/cancel contracts with `*_utc` wire fields
- session states and `canMutate` gating
- Week (default) + Month calendar-first chrome without List restoration
- EventModal + toast feedback interaction model from US-040H
- Postgres editorial calendar SoT separation from LinkedIn variant campaign-metadata schedules
- qualified publication language (`pending`, `queued`, `cancelled`, `flow_a_complete`, blog handoff ≠ LinkedIn API published; dry-run ≠ real mutation)

US-040I MUST NOT implement US-040J cancelled reopen worker path, and MUST NOT implement US-040K max-2-per-local-day density enforcement (local day helpers MAY exist for reuse; K product rules MUST NOT ship here).

US-040I MUST NOT activate public URL hosting, MUST NOT integrate live Google/OIDC, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, MUST NOT read or write raw mount paths from the browser, MUST NOT migrate campaign metadata schedules into Postgres, and MUST NOT add new worker mutation routes or non-`*_utc` schedule wire fields unless a separate design amendment explicitly justifies them.

#### Scenario: Prior architecture baselines remain

- **WHEN** US-040I is implemented
- **THEN** worker HTTP remains the only console data/mutation path, ScheduleEditor / US-017 semantics remain the mutation surface inside the EventModal, session/`canMutate` gating remains, List chrome is not restored, and `*_utc` wire fields remain

#### Scenario: J–K products remain out of apply scope

- **WHEN** US-040I implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040J reopen and US-040K density enforcement as not delivered by this change

#### Scenario: BL-015 remains open

- **WHEN** US-040I implementation lands
- **THEN** status language does not mark BL-015 closed or US-040I Story accepted by implementation alone
