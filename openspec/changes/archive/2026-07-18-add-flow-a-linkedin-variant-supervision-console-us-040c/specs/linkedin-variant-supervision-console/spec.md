## ADDED Requirements

### Requirement: Shared schedule editor from List, Month calendar, and mobile agenda

The Flow A LinkedIn variant supervision console MUST allow an operator to select a future unpublished schedule item from the Month calendar view, the mobile agenda (or equivalent day expansion), or the List view and open the **same** schedule editor component.

The schedule editor MUST collect a new UTC schedule value and optional reason, present dry-run vs real mode, and require explicit confirmation before a committed (`dry_run` false) schedule change.

Published or historical items MUST open as read-only (or refuse schedule mutation) and MUST NOT offer a commit path that would rewrite their schedule.

#### Scenario: Month calendar opens shared schedule editor for editable item

- **WHEN** an operator selects a future unpublished editable item from the Month calendar
- **THEN** the console opens the same schedule editor used by List and mobile agenda for that item

#### Scenario: Mobile agenda opens the same schedule editor

- **WHEN** an operator selects a future unpublished editable item from the mobile agenda (or equivalent)
- **THEN** the console opens the same schedule editor instance/path as Month and List

#### Scenario: Published historical item is read-only for schedule

- **WHEN** an operator selects a published or otherwise historical non-editable item
- **THEN** the console does not allow a committed schedule change for that item

### Requirement: Calendar schedule actions reuse existing worker semantics

Calendar and agenda schedule-modification actions MUST reuse the same business rules and worker mutation semantics already used by list defer/reschedule for LinkedIn pending variants, and MUST use the authenticated editorial-calendar schedule-update API for blog calendar items.

The console MUST NOT introduce a second LinkedIn schedule mutation source of truth and MUST NOT write `editorial-calendar/calendar.json` (or any mount path) from the browser.

Existing list-based edit, defer/reschedule, and cancel affordances for pending LinkedIn variants MUST remain available where already supported.

#### Scenario: LinkedIn schedule edit from calendar calls defer endpoint

- **WHEN** an authenticated operator commits a schedule change for a pending LinkedIn variant from Month or mobile agenda
- **THEN** the console sends `POST /defer-linkedin-variant` (via the typed API client) and does not write campaign files from the browser

#### Scenario: Blog schedule edit calls editorial calendar API

- **WHEN** an authenticated operator commits a schedule change for an editable blog calendar item
- **THEN** the console sends the authenticated worker calendar schedule-update endpoint and does not write `calendar.json` from the browser

#### Scenario: List edit and cancel remain available

- **WHEN** an operator uses the List view after US-040C lands
- **THEN** existing edit and cancel affordances for pending LinkedIn variants remain available alongside defer/reschedule

### Requirement: Schedule mutation dry-run and confirmation

Schedule mutations from the shared schedule editor MUST default to dry-run (`dry_run` true) and MUST make dry-run vs real mode visible before any real mutation.

Committed schedule changes (`dry_run` false) MUST require explicit operator confirmation.

#### Scenario: Dry-run schedule change is visible as non-mutating

- **WHEN** an operator submits the schedule editor with dry-run default
- **THEN** a successful response is presented as validation without claiming the schedule was persisted

#### Scenario: Real schedule change requires confirmation

- **WHEN** an operator selects real (non-dry-run) mode and attempts to commit
- **THEN** the console requires explicit confirmation before sending `dry_run` false

### Requirement: Dual-view refresh and schedule-change outcome messaging

After a successful real schedule change, the console MUST refresh both the Month calendar (schedule-visibility) and the List (pending-supervision and shared model) so both views remain consistent.

The success presentation MUST show at least: the affected item identity, previous schedule, new schedule, and whether related LinkedIn variants were changed or remained separate overrides.

The console MUST NOT claim LinkedIn API published, MUST NOT equate `flow_a_complete` or blog handoff with LinkedIn API published, and MUST NOT claim that schedule edit published blog content.

#### Scenario: Real success refreshes list and calendar

- **WHEN** a real schedule change succeeds
- **THEN** the shared model refreshes from worker HTTP reads and both List and Month calendar reflect the new schedule

#### Scenario: Outcome reports previous and new schedule

- **WHEN** a real schedule change succeeds
- **THEN** the console shows previous schedule, new schedule, and affected item identity

#### Scenario: Blog reschedule reports LinkedIn variants as separate overrides by default

- **WHEN** a real blog calendar schedule change succeeds without a separate LinkedIn defer in the same operator action
- **THEN** the console reports that related LinkedIn variants remained separate overrides (unchanged by the blog calendar write)

### Requirement: Schedule editor validation and failure communication

The console MUST clearly communicate blocked or invalid schedule attempts, including at least:

- unauthorized / invalid API key
- request validation failures (HTTP 422)
- past or invalid time failures
- saturation and duplicate-slot failures when returned by the worker
- unsupported publication/calendar state failures
- existing US-017 defer failure codes when the LinkedIn path is used (`linkedin_supervision_variant_not_pending`, `linkedin_supervision_defer_time_invalid`, `linkedin_supervision_idempotency_conflict`, and related)

Failed attempts MUST NOT be presented as persisted schedule changes.

#### Scenario: Invalid future time failure is visible

- **WHEN** the worker rejects a schedule change for a past or invalid timestamp
- **THEN** the console displays a clear failure and does not claim the schedule changed

#### Scenario: Unsupported state failure is visible

- **WHEN** the worker rejects a schedule change because the item is not eligible (published/historical/unsupported state)
- **THEN** the console displays that failure and does not claim the schedule changed

### Requirement: Schedule mutation does not publish

Schedule edit actions from the supervision console MUST NOT call the LinkedIn publication API and MUST NOT publish blog content, commit/push Git, or bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Schedule edit does not invoke LinkedIn publish

- **WHEN** an operator completes a schedule edit (dry-run or real) from the console
- **THEN** the worker path used does not call LinkedIn publication APIs as part of that edit

### Requirement: US-040C scope preserves visibility baseline and defers later variants

US-040C MUST NOT mark BL-015 closed or US-040C Story accepted by implementation alone.

US-040C MUST preserve the US-040B list + month schedule visibility baseline (dual first-class views, schedule-visibility read, filters, CSS-grid month, mobile agenda) and MUST NOT rewrite that visibility contract except where additive fields are required for schedule editability.

US-040C MUST NOT implement US-040D public URL and Google auth activation, or US-040E polish beyond what schedule-mutation UX requires.

US-040C MUST NOT introduce a backend-for-frontend, database, user-management system, or public hosting change.

US-040C MUST NOT use n8n Execute Command or read/write raw mount paths from the browser.

#### Scenario: Later variants remain out of scope

- **WHEN** US-040C implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040D–US-040E as not implemented (except mutation UX delivered by US-040C) and does not claim BL-015 closed

#### Scenario: US-040B visibility remains first-class

- **WHEN** US-040C schedule mutation is available
- **THEN** List and Month calendar visibility remain dual first-class views and schedule-visibility reads continue to power month placement

### Requirement: Typed client covers schedule-update APIs

The typed API client MUST centralize calls for:

- existing `GET /flow-a/linkedin-variants/pending-supervision`
- existing `GET /flow-a/schedule-visibility`
- existing US-017 `POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`
- the authenticated editorial-calendar schedule-update endpoint introduced for US-040C

Auth MUST remain injectable at the client boundary. Schedule editor and calendar components MUST NOT scatter ad-hoc `fetch` calls for these mutations.

#### Scenario: Schedule editor uses typed client

- **WHEN** the schedule editor submits a LinkedIn or blog schedule change
- **THEN** it uses the typed API client rather than ad-hoc browser filesystem or direct mount writes

## MODIFIED Requirements

### Requirement: Console UI is componentized with operational screen scaffolding

The modernized console MUST structure the UI as componentized operational screens and MUST include implemented boundaries for at least:

- list view (implemented)
- month calendar view (US-040B visibility + US-040C schedule-edit entry points)
- item detail
- schedule editor (US-040C: shared mutation surface from List, Month, and mobile agenda — not scaffold-only)
- status summary
- filters (US-040B: implemented)
- confirmation flows
- shared API and error handling

Full public Google auth activation remains out of scope until US-040D. Polish beyond schedule-mutation UX remains out of scope until US-040E.

#### Scenario: Required component boundaries exist in the frontend package

- **WHEN** the frontend package is inspected after US-040C
- **THEN** distinct component (or module) boundaries exist for list, month calendar, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling

#### Scenario: Schedule editor is no longer scaffold-only

- **WHEN** an operator opens schedule modification from Month, mobile agenda, or List for an editable item
- **THEN** the shared schedule editor supports dry-run, confirmation, and worker-backed commit rather than scaffold-only defer wiring
