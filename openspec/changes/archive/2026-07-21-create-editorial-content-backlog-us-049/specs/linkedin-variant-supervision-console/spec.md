## ADDED Requirements

### Requirement: Editorial content backlog surface in Authority Manager

Silverman Authority Manager (the existing LinkedIn supervision console product surface) SHALL provide an authenticated UI for operators to list, create, and edit editorial content backlog items defined by capability `editorial-content-backlog`. The UI MUST use the worker HTTP backlog API as its source of truth, MUST present the US-049 capture fields (topic, audience, objective, format, priority, status, target date) and LinkedIn derivative planning notes in operator-understandable language, and MUST clearly communicate failures or blocked states (including auth/session and validation failures).

The console MUST NOT become a separate Flow B-only application. The backlog surface MUST NOT expose secrets, MUST NOT claim that saving a backlog item publishes to LinkedIn or starts Flow B discovery/gap trigger, MUST NOT implement US-050 dependency/reprioritization UX, and MUST NOT redesign the console chrome or introduce a new UI component kit.

#### Scenario: Authenticated operator can list and create backlog items

- **WHEN** an authenticated operator opens the Authority Manager backlog surface and creates a valid backlog item
- **THEN** the console persists it via the worker backlog API and shows the item in the list with capture fields visible
- **AND** validation or worker errors are shown in plain language without secret material

#### Scenario: Authenticated operator can edit an existing item

- **WHEN** an authenticated operator edits an existing backlog item’s capture fields or LinkedIn derivative notes and saves
- **THEN** the console updates the item via the worker backlog API and shows the updated values

#### Scenario: Unauthenticated operator cannot mutate backlog

- **WHEN** the console session is anonymous, expired, or forbidden
- **THEN** backlog mutation controls remain unavailable or fail closed with a clear re-auth cue

#### Scenario: Empty backlog is understandable and not a failure

- **WHEN** an authenticated operator opens the backlog surface and the worker returns an empty list
- **THEN** the UI communicates that no backlog items exist yet
- **AND** does not present emptiness as a system failure or as a blocker for Flow B
