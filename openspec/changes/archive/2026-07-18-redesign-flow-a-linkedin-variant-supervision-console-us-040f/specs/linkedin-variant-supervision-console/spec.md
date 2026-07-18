## ADDED Requirements

### Requirement: Modern operational UX redesign for US-040F

US-040F MUST redesign the existing React + TypeScript + Vite console as a modern dark operational web app rather than a text-heavy technical status page.

The redesign MUST preserve US-040A–US-040E architecture and worker contracts: same static asset delivery, same typed API client/auth boundary, same shared normalized model, same first-class List and Month views, same shared ScheduleEditor mutation surface, same session states and `canMutate` gating, and no new mutation source of truth.

The shell MUST use available desktop width effectively and provide a structured workspace with concise top app controls, visible session state, refresh, dry-run/commit mode, view navigation, interactive operational metrics, primary content, and contextual detail/action areas.

Visible primary chrome SHOULD minimize endpoint names, worker codes, raw mount/path wording, and policy prose. Technical details MUST remain available through diagnostics/details or documentation references when needed, especially for failures or blocked states.

#### Scenario: Console renders as an app workspace

- **WHEN** the console first renders after US-040F
- **THEN** the first screen includes a modern app shell with top controls, session state, metric summary, filters path, and List or Month content area rather than a centered documentation-like page

#### Scenario: Metrics can focus the operator

- **WHEN** an operator activates an actionable metric such as blocked, failed, due soon, pending, deferred, or recently published
- **THEN** the console applies the relevant filter or navigation state without requiring the operator to configure filters manually

#### Scenario: Technical prose is not the primary interface

- **WHEN** an operator scans the primary shell, List, or Month view
- **THEN** endpoint paths, raw source-state codes, and long publication semantics are not the dominant visible content, while diagnostics remain available in details for troubleshooting

### Requirement: US-040F List and detail UX

The List view MUST be redesigned for fast triage scanning using cards, rows, or an equivalent modern pattern rather than a table-first technical inspection layout.

Each list item MUST make the human-operational fields prominent: title or campaign label, campaign/variant identity, audience/channel where available, schedule, publication state, risk/blocked/failed status, and safe primary actions.

Desktop layouts SHOULD use a master-detail or drawer pattern so selecting an item reveals detail/actions without pushing the entire list or calendar downward. Mobile layouts MUST avoid horizontal table scrolling and SHOULD use stacked cards plus a drawer, bottom sheet, or full-screen detail surface.

#### Scenario: List is scannable

- **WHEN** pending variants are loaded
- **THEN** the List presents scannable item cards or rows with concise state, schedule, identity, and primary actions

#### Scenario: Selection opens contextual detail

- **WHEN** an operator selects a List item
- **THEN** detail and safe actions appear in a contextual panel/drawer or equivalent surface without replacing the List as the primary triage surface

### Requirement: US-040F Calendar UX

The Month calendar MUST remain first-class and MUST communicate schedule density, channel/state, selected day, today, blocked/failed risk, and overflow at a glance.

The Month view MUST NOT turn day cells into full diagnostic forms. Full diagnostics and schedule actions SHOULD remain in selected-day agenda, item detail, or schedule editor surfaces.

Mobile calendar behavior MUST provide a usable month overview plus agenda-style day detail with touch-friendly schedule actions.

#### Scenario: Month communicates schedule and risk

- **WHEN** a month contains routine, blocked, and failed items
- **THEN** the calendar day cells show compact schedule/risk indicators while selected-day agenda exposes item detail and actions

#### Scenario: Mobile calendar remains usable

- **WHEN** the console is viewed at a mobile width
- **THEN** the month overview and selected-day agenda remain usable without horizontal table scrolling

### Requirement: US-040F validation and scope

US-040F MUST include frontend validation covering modern app shell structure, interactive metric filtering/navigation, card/list triage, master-detail or drawer behavior, responsive mobile layout, preservation of List/Month switching, destructive-action separation, and production build success.

Browser screenshots or equivalent browser-driven visual evidence SHOULD be captured when a browser runner is available. If the local environment cannot provide browser capture, implementation notes MUST explicitly state that limitation and keep automated viewport/component evidence in place.

US-040F MUST NOT activate public URL hosting, MUST NOT integrate a live Google/OIDC identity provider, MUST NOT introduce a BFF/database/user-management product, MUST NOT call the LinkedIn publication API, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT use n8n Execute Command, and MUST NOT read or write raw mount paths from the browser.

US-040F MUST NOT mark BL-015 closed or US-040F Story accepted by implementation alone. Further operator-directed UX iteration MAY follow in a subsequent approved change.

#### Scenario: Prior baselines remain intact

- **WHEN** US-040F is implemented
- **THEN** US-040A–US-040E behavior remains available and worker HTTP remains the only path for console data and mutations

#### Scenario: UX evidence exists

- **WHEN** frontend validation runs after US-040F
- **THEN** tests or documented evidence cover the modern shell, metric focus, list cards/master-detail, calendar/agenda, responsive layout, schedule editor, destructive confirmation, and blocked/failed states

#### Scenario: Story acceptance remains gated

- **WHEN** US-040F implementation and OpenSpec alignment land
- **THEN** status language does not mark BL-015 closed or US-040F Story accepted while further UX direction remains open
