## MODIFIED Requirements

### Requirement: Editorial content backlog surface in Authority Manager

Silverman Authority Manager (the existing LinkedIn supervision console product surface) SHALL provide an authenticated UI for operators to list, create, and edit editorial content backlog items defined by capability `editorial-content-backlog`. The UI MUST use the worker HTTP backlog API as its source of truth, MUST present the capture fields (topic, audience, objective, format, priority, status, target date), LinkedIn derivative planning notes, **dependencies** (`depends_on_item_ids` resolved to understandable labels when possible), and **queue order / prioritization** controls in operator-understandable language, and MUST clearly communicate failures or blocked states (including auth/session, validation, dangling dependency, and cycle failures).

The console MUST NOT become a separate Flow B-only application. The backlog surface MUST NOT expose secrets, MUST NOT claim that saving a backlog item publishes to LinkedIn or starts Flow B discovery/gap trigger, MUST NOT implement discovery seed/override from the backlog, and MUST NOT redesign the console chrome or introduce a new UI component kit.

#### Scenario: Authenticated operator can list and create backlog items

- **WHEN** an authenticated operator opens the Authority Manager backlog surface and creates a valid backlog item
- **THEN** the console persists it via the worker backlog API and shows the item in the list with capture fields visible
- **AND** validation or worker errors are shown in plain language without secret material

#### Scenario: Authenticated operator can edit an existing item

- **WHEN** an authenticated operator edits an existing backlog item’s capture fields or LinkedIn derivative notes and saves
- **THEN** the console updates the item via the worker backlog API and shows the updated values

#### Scenario: Authenticated operator can set dependencies

- **WHEN** an authenticated operator assigns one or more existing backlog items as dependencies of another item and saves
- **THEN** the console persists `depends_on_item_ids` via the worker backlog API
- **AND** the list or detail view shows those dependencies in understandable form

#### Scenario: Authenticated operator can prioritize and reprioritize

- **WHEN** an authenticated operator changes an item’s priority and/or queue position (move earlier/later or equivalent) and saves
- **THEN** the console persists the prioritization change via the worker backlog API
- **AND** the list order reflects the updated prioritization contract

#### Scenario: Dependency or priority failures are clear

- **WHEN** the worker rejects a dependency or prioritization write (cycle, dangling reference, validation, or auth failure)
- **THEN** the console shows a plain-language error without secret material
- **AND** does not present the failure as a successful save

#### Scenario: Unauthenticated operator cannot mutate backlog

- **WHEN** the console session is anonymous, expired, or forbidden
- **THEN** backlog mutation controls remain unavailable or fail closed with a clear re-auth cue

#### Scenario: Empty backlog is understandable and not a failure

- **WHEN** an authenticated operator opens the backlog surface and the worker returns an empty list
- **THEN** the UI communicates that no backlog items exist yet
- **AND** does not present emptiness as a system failure or as a blocker for Flow B
