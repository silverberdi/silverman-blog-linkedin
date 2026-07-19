## ADDED Requirements

### Requirement: Filters live in a header modal (US-040L)

The Flow A LinkedIn variant supervision console MUST NOT render an always-visible FOCUS/Filters dock as permanent primary chrome between the metric summary and the Week/Month calendar surfaces.

The console MUST provide a clear header control labeled **Filters** that opens a focused filters modal.

The filters modal MUST contain the existing filter controls without reducing capability:

- Channel
- Campaign / label
- Blocked only
- Due soon (48h)
- Publication state checkboxes (including `completed` / Published on blog when that publication state is present in the console model)
- Reset

Filters MUST continue to apply consistently to both Week and Month via the shared filter state. Closing the modal MUST NOT clear filters.

#### Scenario: Permanent filters dock is absent

- **WHEN** the console shell is rendered after US-040L
- **THEN** Week/Month are not permanently preceded by a full FOCUS/Filters strip in the primary chrome

#### Scenario: Header Filters opens the modal

- **WHEN** an operator activates the header Filters control
- **THEN** a modal opens containing Channel, Campaign/label, Blocked only, Due soon, publication state checkboxes, and Reset

#### Scenario: Closing the modal keeps filter state

- **WHEN** an operator sets a non-default filter in the modal and then dismisses the modal
- **THEN** Week and Month continue to reflect that filter selection

### Requirement: Active-filter cue on the header Filters control

When any non-default filter is active relative to the console default filter state (channel not `all`, non-empty campaign/label query, blocked-only, due-soon-only, or any selected publication states), the header Filters control MUST surface a calm active cue (badge, count, or equivalent).

The active cue MUST NOT use failed/blocked alarm styling as its only signal. When all filters match defaults, the cue MUST be absent or clearly inactive.

#### Scenario: Badge appears when filtered

- **WHEN** an operator enables blocked-only or selects one or more publication states
- **THEN** the header Filters control shows a calm active cue without requiring the modal to stay open

#### Scenario: Cue clears after reset

- **WHEN** filters return to defaults via Reset or Clear filters
- **THEN** the header active cue is absent or inactive

### Requirement: Metric chip focus remains outside the modal and is reflected inside it

Interactive metric chips MUST remain usable one-click focus shortcuts that write the same shared filter state without requiring the filters modal to apply focus.

When the operator opens the filters modal after a metric-chip focus, the modal MUST reflect the resulting filter controls (toggles, checkboxes, and query fields consistent with that focus).

#### Scenario: Chip focus does not require the modal

- **WHEN** an operator activates a blocked (or equivalent) metric chip
- **THEN** the blocked focus filter applies on Week/Month without opening the filters modal

#### Scenario: Modal reflects chip-applied filters

- **WHEN** an operator applies a metric-chip focus and then opens the Filters modal
- **THEN** the modal controls show the resulting filter state

### Requirement: US-040L Visual DoD and operator walkthrough gates

Automated tests (including Vitest) are necessary but MUST NOT be treated as sufficient for US-040L Story accepted.

US-040L MUST capture Visual DoD evidence (desktop ≈1280 and mobile ≈375, or equivalent) for at least:

- header Filters control visible
- modal opens with the full filter set
- active-filter badge when filtered
- Week/Month uncluttered without a permanent filters dock
- metric chip focus still works
- Reset / clear paths remain obvious

**Story accepted** / Acceptance criteria validated MUST NOT be marked until the content operator completes a live walkthrough on the deployed or explicitly agreed preview console and confirms the calendar feels cleaner and filters remain discoverable.

Vitest/checkbox completion alone MUST NOT imply Story accepted. BL-015 MUST remain open until the backlog completion outcome is operator-validated. US-038–US-040K Story accepted MUST NOT be unset as a side effect of US-040L implementation. US-040M completed-blog mapping MUST NOT be redefined by this requirement.

#### Scenario: Vitest alone does not accept the story

- **WHEN** US-040L implementation and Vitest suites pass without Visual DoD evidence and operator walkthrough
- **THEN** product status MUST NOT mark US-040L Story accepted or Acceptance criteria validated

#### Scenario: Walkthrough required before Story accepted

- **WHEN** Visual DoD evidence exists and the operator completes a walkthrough confirming filters-in-modal UX intent
- **THEN** Story accepted MAY be recorded; otherwise it remains open

### Requirement: US-040L console scope preserves G–K baselines

US-040L MUST preserve:

- Week default + Month secondary calendar-first chrome (no List restoration as primary)
- EventModal + toast feedback
- operator-local primary clock and `*_utc` wire fields (US-040I)
- cancelled reopen path (US-040J)
- local-day density cues and enforcement UX (US-040K)
- session states and `canMutate` gating
- dry-run default + confirm for real
- worker HTTP-only SoT (ADR-0001)
- Week/Month empty-state Clear filters paths
- discoverable hidden-critical failures when filters hide them (via Filters modal surface and/or active-filter cue)
- qualified publication language

US-040L MUST NOT activate public URL / Google OIDC / BFF / user-management, MUST NOT call LinkedIn API publish from the console, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, MUST NOT write editorial mounts from the browser, MUST NOT change US-040M completed-blog mapping semantics, and MUST NOT close BL-015 by implementation alone.

#### Scenario: Prior console baselines remain

- **WHEN** US-040L is implemented
- **THEN** Week remains default, EventModal remains the event surface, local-time helpers remain authoritative for display/placement, density cues remain, reopen remains available for eligible cancelled items, and empty-state Clear filters still clears shared filter state

#### Scenario: No LinkedIn API publish from filters UX

- **WHEN** the Filters modal or active-filter cue is exercised in the console
- **THEN** the console does not invoke LinkedIn publication and only uses worker HTTP read/mutation endpoints already in scope

## MODIFIED Requirements

### Requirement: Filters apply consistently with discoverable critical failures

The console MUST provide filters or toggles for channel, campaign, publication state, blocked items, and due-soon items.

After US-040L, those filter controls MUST be hosted in the header Filters modal rather than an always-visible FOCUS/Filters dock, without reducing filter capability.

Filters MUST apply consistently to both Week and Month views via shared filter state whether the modal is open or closed.

When filters hide critical failure indicators (failed/blocked/integration-critical items), the console MUST keep those hidden critical failures discoverable through a count, warning, or reset / show-critical affordance (at minimum inside the Filters modal when open, with the header active-filter cue indicating that the calendar is filtered while the modal is closed). Critical failures MUST NOT be hidden silently with no signal.

#### Scenario: Filter applies to both views

- **WHEN** an operator filters to channel `linkedin` and switches between Week and Month
- **THEN** both views show only items that satisfy the linkedin channel filter within schedule-visibility (and pending detail) scope

#### Scenario: Hidden critical failures remain discoverable

- **WHEN** active filters exclude one or more critical failure items
- **THEN** the console surfaces a count, warning, or affordance that makes those hidden critical failures discoverable

#### Scenario: Filters are reached from the header modal

- **WHEN** an operator needs the full filter set after US-040L
- **THEN** the operator opens the header Filters control and finds Channel, Campaign/label, Blocked only, Due soon, publication states, and Reset in the modal

### Requirement: Metric chips navigate within Week and Month only

Interactive operational metric chips MUST apply focus filters and MUST navigate or focus within Week or Month calendar cursors so matching work is visible on the calendar.

Metric chips MUST NOT reopen, switch to, or depend on a List view.

Metric chips MUST NOT require the Filters modal to apply focus. Opening the Filters modal after a chip focus MUST reflect the resulting shared filter state.

When no matching item exists for a metric focus, the console MUST keep the calendar surface — including the Week day-column structure or Month day grid — and show an intentional empty or zero-match cue rather than falling back to a list or replacing the calendar with a gridless panel.

#### Scenario: Blocked metric stays on calendar

- **WHEN** an operator activates the blocked metric while on Week or Month
- **THEN** the console applies the blocked focus filter and adjusts the Week or Month cursor toward matching work without opening a List view

#### Scenario: Zero matches do not restore List

- **WHEN** a metric focus matches zero items
- **THEN** the console remains on Week or Month with an intentional empty or zero-match presentation, keeps the calendar day structure visible, and does not open a List

#### Scenario: Chip focus lights the Filters cue

- **WHEN** a metric chip applies a non-default filter
- **THEN** the header Filters control shows its calm active cue and the Filters modal, when opened, reflects that filter state

### Requirement: Operational first screen without marketing landing

The first screen of `GET /flow-a/console/linkedin-variant-supervision` MUST be the usable operational console experience (shell with Week/Month view switcher, status path, header Filters control, and Week content area by default).

The console MUST NOT introduce a marketing-style landing page, promotional hero, or brand splash that replaces or delays the operational console as the first screen.

Auth session banners (anonymous / sign-in guidance) MAY appear inside the operational shell and MUST NOT constitute a separate marketing landing.

After US-040L, the first screen MUST NOT permanently show a full FOCUS/Filters dock ahead of Week/Month.

#### Scenario: First paint is the operational Week console

- **WHEN** an operator opens the supervision console route
- **THEN** the first screen is the operational console shell with Week as the default content area rather than a marketing-style landing page or List home

#### Scenario: First paint has Filters in the header not a permanent dock

- **WHEN** an operator opens the supervision console route after US-040L
- **THEN** the header Filters control is available and a permanent FOCUS/Filters strip does not precede the Week calendar
