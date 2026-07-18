## ADDED Requirements

### Requirement: Dual first-class List and Month calendar views

The Flow A LinkedIn variant supervision console MUST provide two first-class views in the same console: `List` and `Month calendar`. Neither view MUST replace, permanently hide, or weaken the other.

The list view MUST remain the detail-heavy operational surface for pending LinkedIn variants, including campaign id, variant id, audience, `scheduled_at_utc`, publication state, draft content visibility where supported, issues, integration failures, and available edit/defer/cancel actions via existing US-017 POSTs.

The month calendar view MUST be a first-class schedule visibility surface for upcoming Flow A blog posts and LinkedIn variants (see schedule-visibility requirements), not a disposable scaffold.

#### Scenario: Both views are reachable as first-class

- **WHEN** an operator opens the supervision console
- **THEN** both List and Month calendar views are available through a clear view switcher and neither requires the other to be abandoned permanently

#### Scenario: List retains pending operational detail

- **WHEN** the operator uses the List view
- **THEN** pending LinkedIn variant rows still present the Stories 1–3 detail fields and US-017-backed actions without requiring calendar interaction

### Requirement: Persistent view switcher preserves operator context

The console MUST provide a clear, persistent view switcher suitable for desktop and mobile viewports.

Switching between List and Month calendar MUST NOT clear filters, selected campaign context, dry-run mode, or unsaved schedule-edit drafts without an explicit warning and operator confirmation.

#### Scenario: Filters survive view switch

- **WHEN** an operator applies filters and then switches from List to Month calendar (or the reverse)
- **THEN** the same filter selection remains active in the destination view

#### Scenario: Unsaved schedule draft warns before discard on switch

- **WHEN** an unsaved schedule-edit draft exists and the operator attempts to switch views in a way that would discard that draft
- **THEN** the console warns and requires confirmation before discarding the draft

### Requirement: Month calendar visibility UX

The Month calendar view MUST present a full month grid for the current month with previous/next month navigation, a today marker, selected-day state, and clear empty-day states.

The calendar MUST use a dark visual theme with readable contrast, stable spacing, clear hierarchy, and touch targets suitable for mobile operation.

On phone viewports, the calendar MUST provide an agenda-style day expansion (or equivalent) for the selected day instead of forcing horizontal table scrolling as the only way to inspect that day’s items.

#### Scenario: Navigate months and see today

- **WHEN** an operator opens Month calendar
- **THEN** the current month is shown with a today marker and the operator can navigate to previous and next months

#### Scenario: Empty day is understandable

- **WHEN** a day in the visible month has no schedule items after filters
- **THEN** the day presents a clear empty state and is not shown as a system failure

#### Scenario: Mobile uses agenda expansion

- **WHEN** the console is viewed at a mobile width and the operator selects a day with items
- **THEN** those items are inspectable via an agenda-style expansion (or equivalent) without requiring horizontal scrolling of the month table

### Requirement: Schedule items appear on the correct calendar day

The Month calendar MUST show each included Flow A blog post and LinkedIn variant on the correct calendar day according to the documented UTC day-bucketing rule for `scheduled_at_utc`.

Each calendar item presentation MUST include at least:

- title or campaign label
- campaign id where available
- variant id where available
- audience where available
- channel (`blog` or `linkedin`)
- publication state (operator-facing display state)
- scheduled time

#### Scenario: LinkedIn pending variant lands on scheduled UTC day

- **WHEN** a LinkedIn variant has `scheduled_at_utc` falling on a UTC calendar day in the visible month
- **THEN** the Month calendar places that item on that day with channel `linkedin` and the required identity/state/time fields

#### Scenario: Blog calendar item lands on due UTC day

- **WHEN** an editorial calendar blog item has `due_at_utc` falling on a UTC calendar day in the visible month and is included by the schedule-visibility read
- **THEN** the Month calendar places that item on that day with channel `blog` and the required identity/state/time fields

### Requirement: Publication states are distinguished without false LinkedIn published claims

The console MUST distinguish operator-facing display states covering at least: planned, pending, queued, published, deferred, cancelled, blocked, and failed.

The console MUST NOT imply that `pending` or `queued` content has already been published to the LinkedIn API.

The console MUST NOT equate campaign `flow_a_complete`, blog handoff, or editorial calendar `completed` with LinkedIn API published.

#### Scenario: Pending is not labeled LinkedIn API published

- **WHEN** a LinkedIn item has display state `pending`
- **THEN** the presentation does not label it as LinkedIn API published

#### Scenario: Queued is not labeled LinkedIn API published

- **WHEN** a LinkedIn item has display state `queued`
- **THEN** the presentation does not label it as LinkedIn API published

### Requirement: Same item recognizable across List and Month calendar

List and Month calendar MUST render from the same shared normalized frontend model (fed by worker HTTP reads) so the same logical item is recognizable across views via stable ids, labels, status colors, and detail fields.

The console MUST NOT maintain divergent per-view caches that can disagree about item identity, schedule, or publication state.

#### Scenario: Shared identity across views

- **WHEN** a LinkedIn pending variant exists in the shared model
- **THEN** List and Month calendar presentations for that item use the same campaign id, variant id, schedule, and display publication state derived from that model

#### Scenario: Refresh updates both views from shared store

- **WHEN** schedule or pending data is refreshed after a successful real list mutation
- **THEN** both views reflect the updated shared model without a separate divergent calendar-only cache

### Requirement: Filters apply consistently with discoverable critical failures

The console MUST provide filters or toggles for channel, campaign, publication state, blocked items, and due-soon items.

Filters MUST apply consistently to both List and Month calendar views.

When filters hide critical failure indicators (failed/blocked/integration-critical items), the console MUST keep those hidden critical failures discoverable through a count, warning, or reset / show-critical affordance. Critical failures MUST NOT be hidden silently with no signal.

#### Scenario: Filter applies to both views

- **WHEN** an operator filters to channel `linkedin` and switches between List and Month calendar
- **THEN** both views show only items that satisfy the linkedin channel filter (List within its pending operational scope; calendar within schedule-visibility items)

#### Scenario: Hidden critical failures remain discoverable

- **WHEN** active filters exclude one or more critical failure items
- **THEN** the console surfaces a count, warning, or affordance that makes those hidden critical failures discoverable

### Requirement: Explicit timezone handling for schedules

The console MUST display dates and times with explicit timezone handling, including the stored UTC schedule and a useful operator-local interpretation.

Calendar day placement MUST follow the documented UTC day-bucketing rule based on stored UTC timestamps.

#### Scenario: UTC and local times are both visible

- **WHEN** an item with `scheduled_at_utc` is shown in List or Month calendar detail
- **THEN** the UI presents the stored UTC value and an operator-local interpretation

### Requirement: Worker schedule-visibility read aggregation

The worker MUST expose an authenticated read-only schedule-visibility aggregation HTTP endpoint for the console (path fixed at implementation and documented; recommended `GET /flow-a/schedule-visibility`) that returns Flow A blog and LinkedIn schedule items for month visibility without mutating campaign metadata, calendar files, or LinkedIn publication state.

The endpoint MUST support constraining results to a month (or equivalent UTC range) suitable for month navigation.

The endpoint MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git, and MUST NOT invoke US-017 mutation routes on the server.

The browser MUST obtain schedule-visibility data through this worker HTTP capability (or the typed client wrapping it). The browser MUST NOT read raw mounted files or infer schedule state from filesystem paths.

`GET /flow-a/linkedin-variants/pending-supervision` MUST remain available as the pending-window read for list operational detail and MUST NOT be removed by this capability.

#### Scenario: Authenticated schedule-visibility read returns items

- **WHEN** an authenticated client requests the schedule-visibility endpoint for a month that contains blog and LinkedIn schedule facts
- **THEN** the response includes items with channel, identity fields, `scheduled_at_utc`, and publication display state, and performs no campaign or calendar file mutation

#### Scenario: Unauthenticated schedule-visibility read is rejected

- **WHEN** a client requests the schedule-visibility endpoint without a valid API key
- **THEN** the worker rejects the request with existing unauthorized semantics and does not return schedule payloads

#### Scenario: Browser does not read mount paths

- **WHEN** the Month calendar loads schedule data
- **THEN** it uses the typed API client against worker HTTP only and does not read editorial mount paths from the browser

### Requirement: Partial and blocked schedule reads are communicated

The schedule-visibility read and console MUST clearly communicate partial-data and blocked-state context when campaign, calendar, variant, or integration state cannot be read completely, including secret-safe issues and integration-failure context where applicable.

LinkedIn publication enablement off MUST remain display-only technical context: it MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and MUST NOT be used as a reason to invent LinkedIn API published success.

#### Scenario: Calendar missing still allows LinkedIn schedule rows when available

- **WHEN** `editorial-calendar/calendar.json` is missing or invalid and LinkedIn campaign variants with schedules exist
- **THEN** the console or schedule-visibility response still returns available LinkedIn items and clearly reports calendar read failure

#### Scenario: Enablement off does not claim published

- **WHEN** LinkedIn publication enablement is false
- **THEN** schedule visibility still presents pending/queued items without labeling them LinkedIn API published

### Requirement: Mobile list stacked layout for visibility

On phone viewports, the List view MUST present pending operational rows as readable stacked rows or cards suitable for touch use.

#### Scenario: Mobile list is stacked

- **WHEN** the console List view is shown at a mobile width with pending rows present
- **THEN** rows render as stacked readable blocks rather than a single horizontally scrolled dense table as the only layout

### Requirement: Frontend validation covers calendar visibility contracts

US-040B MUST include frontend validation covering at least:

- month calendar UX behavior (navigation, day placement, empty states)
- filter application consistency across List and Month calendar
- dual-view shared-model identity consistency
- desktop viewport and mobile viewport (including agenda-style day expansion or equivalent)

Production build success for the existing React + TypeScript + Vite console MUST continue to hold.

#### Scenario: Dual-view consistency is tested

- **WHEN** frontend validation for US-040B runs
- **THEN** automated tests assert the same logical item identity/state appears consistently for List and Month calendar from the shared model

#### Scenario: Desktop and mobile calendar viewports are covered

- **WHEN** frontend validation for US-040B runs
- **THEN** evidence covers desktop-width and mobile-width presentations including calendar agenda/day expansion behavior

### Requirement: US-040B scope preserves prior console work and defers later variants

US-040B MUST NOT mark BL-015 closed or US-040B Story accepted by implementation alone.

US-040B MUST NOT implement US-040C calendar schedule mutation / new calendar mutation SoT, US-040D public URL and Google auth activation, or US-040E polish beyond what visibility UX requires.

US-040B MUST NOT introduce a backend-for-frontend, database, user-management system, or public hosting change.

US-040B MUST NOT call the LinkedIn publication API, bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, use n8n Execute Command, or read raw mount paths from the browser.

US-040B MUST preserve the React + TypeScript + Vite static-asset delivery and Stories 1–3 list mutation behavior delivered by prior console work.

#### Scenario: Later variants remain out of scope

- **WHEN** US-040B implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040C–US-040E as not implemented (except visibility surfaces delivered by US-040B)

#### Scenario: No calendar mutation SoT introduced

- **WHEN** an operator uses the Month calendar in the US-040B console
- **THEN** the console does not persist schedule changes through a new calendar mutation source of truth and does not write calendar files from the browser

## MODIFIED Requirements

### Requirement: List-oriented pending supervision remains a first-class view

The modernized console MUST preserve the existing list-oriented pending-variant supervision experience as a first-class view, including presentation of pending rows and operator edit, defer, and cancel actions via existing US-017 POSTs with dry-run default and confirmation for real cancel.

The list view MUST NOT be removed, permanently hidden, or degraded to a secondary-only surface by the introduction of the Month calendar visibility view.

Month calendar visibility (US-040B) MUST coexist as an equally first-class view; coexistence MUST NOT reduce list operational parity for pending supervision.

#### Scenario: List view remains primary operational surface

- **WHEN** an operator opens the modernized supervision console
- **THEN** a list-oriented pending-variant supervision view is available as a first-class view and supports the Stories 1–3 supervision actions already delivered

#### Scenario: Calendar visibility does not replace list

- **WHEN** the Month calendar visibility view is present in the console
- **THEN** the list view remains reachable and continues to present pending supervision rows without requiring calendar interaction

### Requirement: Console UI is componentized with operational screen scaffolding

The modernized console MUST structure the UI as componentized operational screens and MUST include implemented or scaffolded boundaries for at least:

- list view (implemented)
- month calendar view (US-040B: implemented visibility UX; not mutation)
- item detail
- schedule editor (scaffold / list defer forms only until US-040C)
- status summary
- filters (US-040B: implemented)
- confirmation flows
- shared API and error handling

Full schedule mutation behavior from the calendar remains out of scope until US-040C and MUST NOT be required for US-040B acceptance.

#### Scenario: Required component boundaries exist in the frontend package

- **WHEN** the frontend package is inspected after US-040B
- **THEN** distinct component (or module) boundaries exist for list, month calendar, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling

#### Scenario: Calendar visibility does not imply US-040C complete

- **WHEN** the Month calendar visibility view is shown without calendar schedule mutation
- **THEN** the console does not claim US-040C is complete and does not invent a new calendar mutation source of truth

### Requirement: List and calendar share one normalized frontend model

List view and month calendar view MUST be backed by the same worker read models or by one shared normalized frontend model derived from those read models so the views cannot disagree about item identity, state, schedule, or available actions.

The shared model MUST incorporate pending-supervision rows for list operations and schedule-visibility rows for month placement (blog and LinkedIn), normalizing overlapping LinkedIn pending rows to one identity.

#### Scenario: Shared model identity is stable across views

- **WHEN** a pending LinkedIn variant exists in the normalized frontend model
- **THEN** list and calendar views that render that item use the same campaign id, variant id, schedule, and action availability derived from that model

#### Scenario: List refresh updates the shared model

- **WHEN** pending-supervision and schedule-visibility data are refreshed after a successful real mutation
- **THEN** the shared model updates and both list and calendar presentations reflect the new state without a separate divergent calendar cache

### Requirement: Browser API access uses a typed client with injectable auth

All browser calls to worker supervision APIs MUST go through a typed API client (or equivalent centralized boundary).

The client MUST centralize request construction, response typing, and error mapping for at least:

- `GET /flow-a/linkedin-variants/pending-supervision`
- the authenticated schedule-visibility GET introduced for US-040B
- `POST /correct-linkedin-variant`
- `POST /defer-linkedin-variant`
- `POST /cancel-linkedin-publication`

Auth credentials MUST be injectable at the API-client boundary (for example via a headers provider) so a future Google/OIDC bearer token or secure session cookie (US-040D) can replace the current API-key header mechanism without changing list or calendar business components.

Frontend source, rendered HTML, logs, and browser storage MUST NOT embed API keys, bearer tokens, OAuth tokens, operational secrets, or secret-like placeholders.

#### Scenario: Business components do not call fetch directly for worker APIs

- **WHEN** list or calendar components load pending supervision or schedule-visibility data or submit edit/defer/cancel
- **THEN** those components use the typed API client rather than ad-hoc `fetch`/`XMLHttpRequest` calls scattered across view code

#### Scenario: Auth provider can be swapped without editing list components

- **WHEN** the auth header provider implementation is replaced at the API-client boundary
- **THEN** list and calendar business components do not require changes to continue calling the same client methods

#### Scenario: Secrets are absent from frontend artifacts

- **WHEN** frontend source and built console assets are scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present

### Requirement: Frontend validation covers build and key UX contracts

US-040A build and list validation requirements remain in force. After US-040B, frontend validation MUST also cover month calendar visibility UX, filter consistency across views, dual-view shared-model identity, and desktop plus mobile viewports for both List and Month calendar (including mobile agenda-style day expansion or equivalent).

US-040B MUST include frontend validation appropriate to the React + TypeScript + Vite stack covering at least:

- production build success
- key component behavior for the list-oriented supervision experience
- month calendar visibility behavior and filters
- API error mapping for auth/validation and known supervision failure codes
- desktop viewport usability of the list and calendar console
- mobile viewport usability of the list and calendar console

#### Scenario: Production build succeeds

- **WHEN** the frontend production build command is run for the supervision console
- **THEN** the build completes successfully and emits static artifacts consumable by the worker

#### Scenario: API error mapping is tested

- **WHEN** the typed client receives unauthorized or known US-017 supervision failure responses
- **THEN** automated tests assert those responses map to clear operator-facing error states without silent success

#### Scenario: Desktop and mobile viewports are covered

- **WHEN** frontend validation for US-040B runs
- **THEN** evidence covers both a desktop-width and a mobile-width presentation of the list and month calendar visibility console
