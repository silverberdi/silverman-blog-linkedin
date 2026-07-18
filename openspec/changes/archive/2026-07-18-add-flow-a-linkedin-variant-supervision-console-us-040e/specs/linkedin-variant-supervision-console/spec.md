## MODIFIED Requirements

### Requirement: Console UI is componentized with operational screen scaffolding

The modernized console MUST structure the UI as componentized operational screens and MUST include implemented boundaries for at least:

- list view (implemented)
- month calendar view (US-040B visibility + US-040C schedule-edit entry points)
- item detail
- schedule editor (US-040C: shared mutation surface from List, Month, and mobile agenda — not scaffold-only)
- status summary (US-040E: at-a-glance operational counts — not sparse technical metadata only)
- filters (US-040B: implemented)
- confirmation flows
- shared API and error handling

Full public URL hosting and live Google/OIDC activation remain out of scope after US-040D readiness (separate security change required). US-040E delivers operational usability and safety polish on top of the A–D baselines.

#### Scenario: Required component boundaries exist in the frontend package

- **WHEN** the frontend package is inspected after US-040E
- **THEN** distinct component (or module) boundaries exist for list, month calendar, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling

#### Scenario: Schedule editor is no longer scaffold-only

- **WHEN** an operator opens schedule modification from Month, mobile agenda, or List for an editable item
- **THEN** the shared schedule editor supports dry-run, confirmation, and worker-backed commit rather than scaffold-only defer wiring

#### Scenario: Status summary provides operational counts

- **WHEN** schedule and/or pending supervision data is loaded into the shared model
- **THEN** the status summary presents at-a-glance operational counts rather than only sparse technical metadata

#### Scenario: Public URL activation remains deferred after polish

- **WHEN** US-040E polish is present in the console
- **THEN** the console does not activate public URL hosting or live Google/OIDC authentication

## ADDED Requirements

### Requirement: At-a-glance operational counts

The supervision console MUST provide at-a-glance counts visible from the operational shell for at least:

- upcoming
- pending
- due soon
- deferred
- blocked
- failed
- recently published

Counts MUST be derived from the shared normalized frontend model fed by existing worker HTTP reads (`GET /flow-a/linkedin-variants/pending-supervision` and `GET /flow-a/schedule-visibility`) unless an approved thin additive read-only field is required and documented in the same change.

Count semantics MUST use qualified publication language:

- `pending` and `queued` MUST NOT be counted or labeled as LinkedIn API published
- `cancelled` MUST NOT be labeled as LinkedIn API published
- campaign `flow_a_complete` and blog handoff MUST NOT be treated as LinkedIn API published
- recently published MUST reflect display state `published` and/or `linkedinApiPublished` evidence within the documented recent window — not inferred from lifecycle metadata alone

Due soon MUST reuse the console’s existing due-soon window (48 hours) unless a superseding approved change replaces it.

#### Scenario: Counts appear after data load

- **WHEN** an authenticated operator has loaded pending-supervision and/or schedule-visibility data
- **THEN** the status summary presents counts for upcoming, pending, due soon, deferred, blocked, failed, and recently published

#### Scenario: Pending is not counted as LinkedIn API published

- **WHEN** items exist with display state `pending`
- **THEN** those items contribute to the pending count and are not labeled or counted as LinkedIn API published in the recently published count solely because they are pending

#### Scenario: Empty zero counts are understandable

- **WHEN** no items match a count category
- **THEN** that count shows zero (or equivalent empty) without presenting the zero as a system failure

### Requirement: Actionable states have visual priority without alarm fatigue

The console MUST prioritize actionable states visually so blocked or failed (and other critical) items are noticeable in List and Month presentations without overwhelming normal scheduled content (planned / pending / queued / routine published).

List view MUST remain optimized for scanning and triage density. Month calendar MUST remain optimized for schedule comprehension (day placement and compact status), not full diagnostic walls inside every day cell.

#### Scenario: Blocked or failed items are noticeable in List

- **WHEN** the List contains blocked or failed items among routine pending rows
- **THEN** those actionable items are visually distinct from routine rows without making every row appear critical

#### Scenario: Month keeps schedule comprehension

- **WHEN** the Month calendar shows a day with both routine and blocked/failed items
- **THEN** the day remains schedule-comprehensible (time/placement readable) and does not force full List-style diagnostic chrome into every cell

### Requirement: Concise operator-facing labels with expandable diagnostics

The console MUST present concise operator-facing labels for technical publication display states (at least planned, pending, queued, published, deferred, cancelled, blocked, failed).

Detailed diagnostic codes and issue text (including known US-017 / calendar schedule-update codes and HTTP auth/validation failures already mapped by the typed client) MUST remain available in expandable details, detail panels, or equivalent disclosure UI when needed.

Primary chrome MUST prefer the concise label. The console MUST NOT remove operator access to diagnostic codes for failed or blocked outcomes.

#### Scenario: Concise label is shown for pending

- **WHEN** an item has display state `pending`
- **THEN** the primary presentation uses a concise operator-facing label and does not claim LinkedIn API published

#### Scenario: Diagnostic code remains available on failure

- **WHEN** a mutation or read failure includes a known worker diagnostic code
- **THEN** the operator can reveal that code (or equivalent tied text) via expandable details or an equivalent disclosure without treating the failure as success

### Requirement: Clear operational affordances

The console MUST provide clear affordances for:

- switching view (List / Month calendar)
- filtering
- inspecting item detail
- rescheduling / deferring where supported
- cancelling where supported
- refreshing data
- dry-run vs commit mode

Destructive or irreversible actions (including real cancel) MUST remain protected by confirmation and MUST NOT be placed as peer controls immediately adjacent to routine navigation controls (view switcher and refresh) in a way that invites accidental activation.

Unauthenticated and read-only sessions (`canMutate` false) MUST continue to be prevented from executing mutations (US-040D).

#### Scenario: View switch and refresh are distinct from cancel

- **WHEN** the operator views the operational toolbar
- **THEN** view switching and refresh are clearly available and cancel is not presented as an adjacent peer of those routine navigation controls without confirmation protection

#### Scenario: Dry-run mode remains visible

- **WHEN** the operator uses the console shell
- **THEN** dry-run vs commit mode is clearly visible before real mutations

#### Scenario: Inspect and schedule actions remain reachable

- **WHEN** an editable future item is selected from List, Month, or mobile agenda
- **THEN** the operator can inspect detail and open the shared schedule editor where schedule edit is supported

### Requirement: List triage vs Month schedule comprehension

The List view MUST remain optimized for scanning and bulk operational triage of pending LinkedIn supervision.

The Month calendar MUST remain optimized for schedule comprehension of upcoming blog and LinkedIn items.

The console MUST NOT force one view to carry both jobs poorly (for example by removing List operational detail or by turning Month cells into full edit/diagnostic forms).

Both views MUST remain first-class and reachable through the persistent view switcher without clearing filters, dry-run mode, or unsaved schedule drafts without warning (US-040B).

#### Scenario: List retains triage detail

- **WHEN** the operator uses List after US-040E polish
- **THEN** pending operational detail and supported edit/defer/cancel actions remain available for scanning and triage

#### Scenario: Month retains schedule comprehension

- **WHEN** the operator uses Month calendar after US-040E polish
- **THEN** day placement, month navigation, and schedule comprehension remain usable without requiring List interaction

### Requirement: Keyboard and touch accessibility for operational controls

The console MUST preserve keyboard accessibility for laptop use and touch accessibility for mobile use on primary operational controls (view switch, filters, refresh, dry-run toggle, list/calendar interaction, detail, schedule editor, confirmation).

Interactive controls MUST expose a visible focus indication for keyboard users. Primary touch targets on mobile MUST remain suitable for finger activation (MUST NOT regress below the mobile usability baseline delivered by US-040B).

Critical actions MUST NOT rely on hover-only disclosure.

#### Scenario: Keyboard can reach primary shell controls

- **WHEN** an operator uses keyboard focus on a desktop-width console
- **THEN** primary shell controls (including view switch and refresh) are reachable and show a visible focus indication

#### Scenario: Mobile touch targets remain usable

- **WHEN** the console is shown at a mobile width
- **THEN** primary actions in the shell and active view remain touch-operable without requiring hover

### Requirement: Dark theme consistency across console states

The console MUST keep the dark visual theme consistent across loading, empty, error, detail, confirmation, and success states, with readable contrast and stable spacing aligned to the existing dark console baseline.

#### Scenario: Empty state uses dark theme

- **WHEN** the List or Month presents an empty operational state
- **THEN** the empty presentation uses the dark theme and is not shown as a light marketing surface

#### Scenario: Error and success states use dark theme

- **WHEN** the console shows an error banner or a success outcome banner
- **THEN** those states use dark-theme-consistent chrome distinct from a light marketing page

#### Scenario: Confirmation and detail use dark theme

- **WHEN** the operator opens item detail or a confirmation flow
- **THEN** those surfaces use dark-theme-consistent presentation

### Requirement: Operational first screen without marketing landing

The first screen of `GET /flow-a/console/linkedin-variant-supervision` MUST be the usable operational console experience (shell with view switcher / status / filters path and List or Month content area).

The console MUST NOT introduce a marketing-style landing page, promotional hero, or brand splash that replaces or delays the operational console as the first screen.

Auth session banners (anonymous / sign-in guidance) MAY appear inside the operational shell and MUST NOT constitute a separate marketing landing.

#### Scenario: First paint is the operational console

- **WHEN** an operator opens the supervision console route
- **THEN** the first screen is the operational console shell rather than a marketing-style landing page

### Requirement: Desktop and mobile visual validation for US-040E

US-040E MUST include desktop and mobile visual validation evidence via screenshots or equivalent UI checks covering at least:

- dense lists
- empty lists
- dense months
- empty months
- blocked items
- long titles
- switching views
- schedule editing

Production build success for the existing React + TypeScript + Vite console MUST continue to hold. Secrets audits for frontend source and built assets MUST continue to pass.

#### Scenario: Visual validation matrix is covered

- **WHEN** US-040E frontend validation runs
- **THEN** evidence covers desktop-width and mobile-width presentations for dense/empty list, dense/empty month, blocked items, long titles, view switching, and schedule editing

#### Scenario: Production build still succeeds

- **WHEN** the frontend production build command is run after US-040E polish
- **THEN** the build completes successfully and emits static artifacts consumable by the worker

### Requirement: US-040E scope preserves A–D baselines and does not close BL-015 alone

US-040E MUST NOT mark BL-015 closed or US-040E Story accepted by implementation or propose alone.

US-040E MUST preserve:

- US-040A React + TypeScript + Vite static-asset delivery
- US-040B dual first-class List + Month visibility, filters, and shared model
- US-040C shared ScheduleEditor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog)
- US-040D session states and `canMutate` gating (public URL hosting and Google/OIDC activation remain deferred)

US-040E MUST prefer frontend UX polish on existing worker HTTP APIs and MUST NOT introduce a new mutation source of truth unless strictly required and approved within this change’s apply scope as a thin additive contract.

US-040E MUST NOT activate public URL hosting, MUST NOT integrate a live Google OAuth/OIDC identity provider, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT read or write raw mount paths from the browser.

#### Scenario: Prior baselines remain first-class after polish

- **WHEN** US-040E polish is implemented
- **THEN** List and Month remain dual first-class views, shared ScheduleEditor remains the schedule mutation surface, typed injectable auth with session/`canMutate` gating remains, and worker HTTP remains the only path for console data and mutations

#### Scenario: Public URL and Google remain not activated

- **WHEN** US-040E implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records that public URL hosting and Google/OIDC authentication are not activated and still require a separate security change before internet exposure

#### Scenario: BL-015 remains open until acceptance

- **WHEN** US-040E implementation lands
- **THEN** status language does not mark BL-015 closed or US-040E Story accepted by implementation alone

### Requirement: US-040E failures and outcomes are clearly communicated

US-040E polish MUST keep failures and blocked states clearly communicated and outcomes understandable to the content operator, including loading/empty/error/success/confirmation presentations and existing auth, validation, and supervision failure mappings.

Failed or blocked attempts MUST NOT be presented as successful schedule, cancel, or content changes. The console MUST NOT equate `pending`, `queued`, `cancelled`, `flow_a_complete`, or blog handoff with LinkedIn API published.

#### Scenario: Blocked state remains understandable after polish

- **WHEN** blocked or failed items are present
- **THEN** the console communicates that actionable state clearly without claiming LinkedIn API published

#### Scenario: Failed mutation is not shown as success

- **WHEN** a supervised mutation fails after polish
- **THEN** the console shows a clear failure or blocked outcome and does not present the action as persisted
