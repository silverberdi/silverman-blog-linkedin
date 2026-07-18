## ADDED Requirements

### Requirement: Calendar-first Week and Month operator chrome (US-040G)

The Flow A LinkedIn variant supervision console MUST be calendar-first. The operator-facing view switcher MUST offer exactly two first-class views labeled `Week` and `Month`.

`Week` MUST be the default view on first load and after hard refresh (unless a documented deep-link explicitly selects Month).

The console MUST NOT present a List tab, list-first landing, or empty list as the default workspace.

#### Scenario: Week is default first paint

- **WHEN** an operator opens `GET /flow-a/console/linkedin-variant-supervision` with no deep-link overriding the view
- **THEN** the first operational content area is the Week calendar view with the view switcher showing Week selected

#### Scenario: View switcher is Week and Month only

- **WHEN** the operator inspects the persistent view switcher
- **THEN** the switcher exposes Week and Month controls and does not expose a List control

#### Scenario: List chrome is absent

- **WHEN** the console shell is rendered after US-040G
- **THEN** no List tab, list landing route, or empty-list home workspace is presented as an operator chrome surface

### Requirement: Week calendar visibility UX

The Week view MUST present a readable local-week layout using day columns (or equivalent day sections on mobile), with day headers, today emphasis, previous/next week navigation, and a one-click Today / This week affordance.

Events MUST render as scannable chips or cards showing at least title or campaign label, channel, local time interpretation, and concise publication state. Raw ids MUST NOT be the primary visible label.

Week MUST NOT use an hour-by-hour time grid as the primary layout for this product density.

On phone viewports, week navigation and event chips MUST remain thumb-friendly and readable without requiring horizontal table scrolling as the only inspection path.

#### Scenario: Week shows day columns and today

- **WHEN** an operator opens Week for the current week
- **THEN** day headers are visible, today is emphasized, and the operator can navigate to previous and next weeks

#### Scenario: Event chips are scannable

- **WHEN** one or more schedule items fall in the visible week
- **THEN** each item appears as a chip or card with title or campaign label, channel, local time, and concise state (not raw id as the primary label)

#### Scenario: Today / This week control

- **WHEN** the operator activates the Today / This week control from Week
- **THEN** the Week cursor returns to the current week with today emphasized

#### Scenario: Mobile week remains usable

- **WHEN** the console is viewed at a mobile width on Week
- **THEN** week navigation and event chips remain usable without horizontal table scrolling as the only layout

### Requirement: Intentional empty Week and Month states

When a visible week or month has zero items after filters, the console MUST show a deliberate empty state with short operator-facing copy and, when filters hid everything, a path to clear or reset filters.

Empty week/month presentations MUST use the dark theme and MUST NOT appear as an unexplained blank content void or system failure.

#### Scenario: Empty week is intentional

- **WHEN** the visible week has no items after filters
- **THEN** the Week view shows a calm empty state (for example that there are no publications this week) and does not present a blank broken panel

#### Scenario: Empty month is intentional

- **WHEN** the visible month has no items after filters
- **THEN** the Month view shows a calm empty state and does not present a blank broken panel

#### Scenario: Filters caused emptiness

- **WHEN** items exist in the shared model but active filters hide all items in the visible week or month
- **THEN** the empty state offers a path to clear or reset filters

### Requirement: Metric chips navigate within Week and Month only

Interactive operational metric chips MUST apply focus filters and MUST navigate or focus within Week or Month calendar cursors so matching work is visible on the calendar.

Metric chips MUST NOT reopen, switch to, or depend on a List view.

When no matching item exists for a metric focus, the console MUST keep the calendar surface and show an intentional empty or zero-match state rather than falling back to a list.

#### Scenario: Blocked metric stays on calendar

- **WHEN** an operator activates the blocked metric while on Week or Month
- **THEN** the console applies the blocked focus filter and adjusts the Week or Month cursor toward matching work without opening a List view

#### Scenario: Zero matches do not restore List

- **WHEN** a metric focus matches zero items
- **THEN** the console remains on Week or Month with an intentional empty or zero-match presentation and does not open a List

### Requirement: Interim calendar action entry points until event modal

Until US-040H ships the focused event modal, clicking an event chip on Week or Month MUST open an interim detail and/or ScheduleEditor surface that preserves existing edit, defer/reschedule, and cancel capabilities (where already supported) via the typed API client and existing worker mutation contracts.

The interim surface MUST be honest: it MUST NOT claim to be the US-040H event modal product, and this requirement MUST NOT be interpreted as shipping US-040H modal chrome or toast feedback.

Day selection MAY provide light focus affordance; it MUST NOT restore a list-like multi-item diagnostic dump as the primary action surface.

#### Scenario: Event chip opens interim actions

- **WHEN** an operator activates an editable event chip on Week or Month
- **THEN** the console opens the interim detail and/or ScheduleEditor path for that item using existing worker HTTP mutations

#### Scenario: Interim path is not claimed as H modal

- **WHEN** the interim detail or ScheduleEditor surface is open after US-040G
- **THEN** the console does not present that surface as the completed US-040H event modal product

#### Scenario: Capabilities remain reachable without List

- **WHEN** List chrome has been removed
- **THEN** pending LinkedIn edit, defer/reschedule, and cancel (where previously supported) remain reachable from calendar event entry points

### Requirement: US-040G Visual DoD and acceptance gates

US-040G MUST require desktop and mobile Visual DoD evidence (screenshots or equivalent browser-driven capture) covering at least:

- Week first paint
- empty week
- dense week
- Month switch
- empty month
- dense month
- Today / This-week control
- proof that List chrome is gone

Vitest or component assertions alone MUST NOT be treated as sufficient for Story accepted.

US-040G Story accepted and Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed console or an explicitly agreed preview and confirms the UX meets calendar-first intent.

Implementation commit and “business outcome demonstrated” MAY occur before that gate. BL-015 MUST remain open until the backlog completion outcome is operator-validated; shipping US-040G code MUST NOT close BL-015 by itself.

If browser capture is unavailable in the implementation environment, status language MUST record that limitation and MUST leave Visual DoD / Story-accepted gates open.

#### Scenario: Visual DoD scenes are required

- **WHEN** US-040G claims visual validation complete for Story accepted
- **THEN** desktop and mobile evidence exists for Week first paint, empty week, dense week, Month switch, empty month, dense month, Today/This-week, and absence of List chrome

#### Scenario: Vitest alone does not accept the story

- **WHEN** only Vitest or component assertions have passed
- **THEN** status language does not mark US-040G Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough gate blocks Story accepted

- **WHEN** implementation is complete but the operator walkthrough on deployed or agreed preview has not confirmed calendar-first UX
- **THEN** US-040G remains not Story accepted and BL-015 remains open

### Requirement: US-040G scope preserves baselines and defers H–K products

US-040G MUST NOT mark BL-015 closed or US-040G Story accepted by implementation alone.

US-040G MUST preserve:

- React + TypeScript + Vite same-origin static delivery
- typed injectable-auth API client
- shared normalized frontend model fed by worker HTTP reads
- ScheduleEditor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog)
- session states and `canMutate` gating
- qualified publication language (`pending`, `queued`, `cancelled`, `flow_a_complete`, blog handoff ≠ LinkedIn API published)

US-040G MUST NOT implement the US-040H event modal + toast product (interim entry points only), MUST NOT implement US-040I local-day bucketing overhaul (interim UTC day placement with local time display is allowed and MUST be documented as debt), MUST NOT implement US-040J cancelled reopen worker path, and MUST NOT implement US-040K max-2-per-local-day enforcement.

US-040G MUST NOT activate public URL hosting, MUST NOT integrate live Google/OIDC, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT read or write raw mount paths from the browser.

#### Scenario: Prior architecture baselines remain

- **WHEN** US-040G is implemented
- **THEN** worker HTTP remains the only console data/mutation path, ScheduleEditor remains the schedule mutation surface, and session/`canMutate` gating remains

#### Scenario: H–K products remain out of apply scope

- **WHEN** US-040G implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040H modal/toasts, US-040I local-day bucketing, US-040J reopen, and US-040K density enforcement as not delivered by this change (aside from G interim action entry points and documented I debt)

#### Scenario: BL-015 remains open

- **WHEN** US-040G implementation lands
- **THEN** status language does not mark BL-015 closed or US-040G Story accepted by implementation alone

## MODIFIED Requirements

### Requirement: Persistent view switcher preserves operator context

The console MUST provide a clear, persistent view switcher suitable for desktop and mobile viewports with labels `Week` and `Month`.

Switching between Week and Month MUST NOT clear filters, selected campaign context, dry-run mode, or unsaved schedule-edit drafts without an explicit warning and operator confirmation.

#### Scenario: Filters survive view switch

- **WHEN** an operator applies filters and then switches from Week to Month (or the reverse)
- **THEN** the same filter selection remains active in the destination view

#### Scenario: Unsaved schedule draft warns before discard on switch

- **WHEN** an unsaved schedule-edit draft exists and the operator attempts to switch views in a way that would discard that draft
- **THEN** the console warns and requires confirmation before discarding the draft

### Requirement: List and calendar share one normalized frontend model

Week view and Month calendar view MUST be backed by the same worker read models or by one shared normalized frontend model derived from those read models so the views cannot disagree about item identity, state, schedule, or available actions.

The shared model MUST incorporate pending-supervision rows for pending operational detail and schedule-visibility rows for Week/Month placement (blog and LinkedIn), normalizing overlapping LinkedIn pending rows to one identity.

#### Scenario: Shared model identity is stable across views

- **WHEN** a pending LinkedIn variant exists in the normalized frontend model
- **THEN** Week and Month views that render that item use the same campaign id, variant id, schedule, and action availability derived from that model

#### Scenario: Refresh updates the shared model

- **WHEN** pending-supervision and schedule-visibility data are refreshed after a successful real mutation
- **THEN** the shared model updates and both Week and Month presentations reflect the new state without a separate divergent calendar cache

### Requirement: Filters apply consistently with discoverable critical failures

The console MUST provide filters or toggles for channel, campaign, publication state, blocked items, and due-soon items.

Filters MUST apply consistently to both Week and Month views.

When filters hide critical failure indicators (failed/blocked/integration-critical items), the console MUST keep those hidden critical failures discoverable through a count, warning, or reset / show-critical affordance. Critical failures MUST NOT be hidden silently with no signal.

#### Scenario: Filter applies to both views

- **WHEN** an operator filters to channel `linkedin` and switches between Week and Month
- **THEN** both views show only items that satisfy the linkedin channel filter within schedule-visibility (and pending detail) scope

#### Scenario: Hidden critical failures remain discoverable

- **WHEN** active filters exclude one or more critical failure items
- **THEN** the console surfaces a count, warning, or affordance that makes those hidden critical failures discoverable

### Requirement: Clear operational affordances

The console MUST provide clear affordances for:

- switching view (Week / Month)
- filtering
- inspecting item detail from calendar event entry points
- rescheduling / deferring where supported
- cancelling where supported
- refreshing data
- dry-run vs commit mode
- Today / This week (and equivalent month today navigation where applicable)

Destructive or irreversible actions (including real cancel) MUST remain protected by confirmation and MUST NOT be placed as peer controls immediately adjacent to routine navigation controls (view switcher and refresh) in a way that invites accidental activation.

Unauthenticated and read-only sessions (`canMutate` false) MUST continue to be prevented from executing mutations (US-040D).

#### Scenario: View switch and refresh are distinct from cancel

- **WHEN** the operator views the operational toolbar
- **THEN** view switching and refresh are clearly available and cancel is not presented as an adjacent peer of those routine navigation controls without confirmation protection

#### Scenario: Dry-run mode remains visible

- **WHEN** the operator uses the console shell
- **THEN** dry-run vs commit mode is clearly visible before real mutations

#### Scenario: Inspect and schedule actions remain reachable from calendar

- **WHEN** an editable future item is selected from a Week or Month event chip (interim entry path)
- **THEN** the operator can inspect detail and open the shared schedule editor where schedule edit is supported

### Requirement: Shared schedule editor from calendar entry points

The Flow A LinkedIn variant supervision console MUST allow an operator to select a future unpublished schedule item from the Week view, the Month calendar view, or mobile day/agenda equivalents and open the **same** schedule editor component.

The schedule editor MUST collect a new UTC schedule value and optional reason, present dry-run vs real mode, and require explicit confirmation before a committed (`dry_run` false) schedule change.

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

### Requirement: Dual-view refresh and schedule-change outcome messaging

After a successful real schedule change, the console MUST refresh Week and Month presentations from the shared model (schedule-visibility and pending-supervision reads as applicable) so both views remain consistent.

The success presentation MUST show at least: the affected item identity, previous schedule, new schedule, and whether related LinkedIn variants were changed or remained separate overrides.

The console MUST NOT claim LinkedIn API published, MUST NOT equate `flow_a_complete` or blog handoff with LinkedIn API published, and MUST NOT claim that schedule edit published blog content.

#### Scenario: Real success refreshes week and month

- **WHEN** a real schedule change succeeds
- **THEN** the shared model refreshes from worker HTTP reads and both Week and Month reflect the new schedule

#### Scenario: Outcome reports previous and new schedule

- **WHEN** a real schedule change succeeds
- **THEN** the console shows previous schedule, new schedule, and affected item identity

#### Scenario: Blog reschedule reports LinkedIn variants as separate overrides by default

- **WHEN** a real blog calendar schedule change succeeds without a separate LinkedIn defer in the same operator action
- **THEN** the console reports that related LinkedIn variants remained separate overrides (unchanged by the blog calendar write)

### Requirement: Console UI is componentized with operational screen scaffolding

The modernized console MUST structure the UI as componentized operational screens and MUST include implemented boundaries for at least:

- week view (US-040G: default first-class)
- month calendar view (density secondary first-class)
- item detail (reachable from calendar event entry points; interim until US-040H modal)
- schedule editor (shared mutation surface from Week, Month, and mobile day/agenda equivalents)
- status summary (at-a-glance operational counts)
- filters
- confirmation flows
- shared API and error handling

List view MUST NOT remain a first-class operator chrome boundary after US-040G.

Full public URL hosting and live Google/OIDC activation remain out of scope (separate security change required).

#### Scenario: Required component boundaries exist in the frontend package

- **WHEN** the frontend package is inspected after US-040G
- **THEN** distinct component (or module) boundaries exist for week, month calendar, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling, and List is not a first-class operator chrome boundary

#### Scenario: Schedule editor remains shared

- **WHEN** an operator opens schedule modification from Week, Month, or mobile day/agenda for an editable item
- **THEN** the shared schedule editor supports dry-run, confirmation, and worker-backed commit

#### Scenario: Public URL activation remains deferred

- **WHEN** US-040G calendar-first UX is present in the console
- **THEN** the console does not activate public URL hosting or live Google/OIDC authentication

### Requirement: Same item recognizable across Week and Month

Week and Month MUST render from the same shared normalized frontend model (fed by worker HTTP reads) so the same logical item is recognizable across views via stable ids, labels, status colors, and detail fields.

The console MUST NOT maintain divergent per-view caches that can disagree about item identity, schedule, or publication state.

#### Scenario: Shared identity across views

- **WHEN** a LinkedIn pending variant exists in the shared model
- **THEN** Week and Month presentations for that item use the same campaign id, variant id, schedule, and display publication state derived from that model

#### Scenario: Refresh updates both views from shared store

- **WHEN** schedule or pending data is refreshed after a successful real mutation
- **THEN** both views reflect the updated shared model without a separate divergent calendar-only cache

### Requirement: Operational first screen without marketing landing

The first screen of `GET /flow-a/console/linkedin-variant-supervision` MUST be the usable operational console experience (shell with Week/Month view switcher, status/filters path, and Week content area by default).

The console MUST NOT introduce a marketing-style landing page, promotional hero, or brand splash that replaces or delays the operational console as the first screen.

Auth session banners (anonymous / sign-in guidance) MAY appear inside the operational shell and MUST NOT constitute a separate marketing landing.

#### Scenario: First paint is the operational Week console

- **WHEN** an operator opens the supervision console route
- **THEN** the first screen is the operational console shell with Week as the default content area rather than a marketing-style landing page or List home

### Requirement: Actionable states have visual priority without alarm fatigue

The console MUST prioritize actionable states visually so blocked or failed (and other critical) items are noticeable in Week and Month presentations without overwhelming normal scheduled content (planned / pending / queued / routine published).

Week MUST remain optimized for “this week’s plan” comprehension with scannable event chips. Month calendar MUST remain optimized for schedule density comprehension (day placement and compact status), not full diagnostic walls inside every day cell.

#### Scenario: Blocked or failed items are noticeable in Week

- **WHEN** the Week contains blocked or failed items among routine scheduled items
- **THEN** those actionable items are visually distinct from routine chips without making every chip appear critical

#### Scenario: Month keeps schedule comprehension

- **WHEN** the Month calendar shows a day with both routine and blocked/failed items
- **THEN** the day remains schedule-comprehensible (time/placement readable) and does not force full diagnostic chrome into every cell

## REMOVED Requirements

### Requirement: List-oriented pending supervision remains a first-class view

**Reason:** US-040G supersedes list-as-first-class UX. Operator feedback rejected list-first triage and empty list landings; calendar-first Week + Month is the normative operator chrome.

**Migration:** Pending supervision capabilities move to Week/Month event entry points (interim detail/ScheduleEditor in G; event modal in H). `GET /flow-a/linkedin-variants/pending-supervision` remains as a worker read for the shared model. Historical US-040A–F List language remains valid only for those stories’ demonstrated scope.

### Requirement: Dual first-class List and Month calendar views

**Reason:** Replaced by calendar-first Week (default) + Month (secondary) dual views under US-040G.

**Migration:** Implement Week + Month switcher; remove List chrome; preserve Month density UX; migrate List capability tests to calendar entry points.

### Requirement: Mobile list stacked layout for visibility

**Reason:** List is removed from operator chrome; mobile usability requirements move to Week and Month responsive layouts.

**Migration:** Cover mobile Week day sections/chips and Month overview + day detail in Visual DoD and Vitest viewport matrix.

### Requirement: List triage vs Month schedule comprehension

**Reason:** List triage is no longer a first-class job. Week owns near-term plan comprehension; Month owns horizon density.

**Migration:** Do not restore List as recovery UI for failures; use calendar empty/error states and interim event detail instead.

### Requirement: US-040F List and detail UX

**Reason:** US-040F List card/master-detail chrome is superseded for future operator UX by calendar-first Week/Month (G) and event modal (H). Keeping List-detail as a normative requirement would block G.

**Migration:** Retain useful detail/drawer implementation patterns only as interim calendar entry points (G D3); H replaces with event modal. US-040F remains historically demonstrated for its story scope.
