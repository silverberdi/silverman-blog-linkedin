## ADDED Requirements

### Requirement: Flow B gap operator settings surface in Authority Manager

Silverman Authority Manager (the existing LinkedIn supervision console product surface) SHALL provide an authenticated UI for operators to view and update Flow B gap operator settings defined by capability `flow-b-gap-operator-settings`. The UI MUST use the worker HTTP settings API as its source of truth, MUST validate or surface worker validation for IANA timezone, time-of-day, non-negative integers, and enums, and MUST clearly communicate failures or blocked states (including auth/session failures).

The console MUST NOT become a separate Flow B-only application. The settings surface MUST NOT expose secrets, MUST NOT claim that saving settings publishes to LinkedIn, and MUST NOT implement gap detect, draft generation, or blog approve/promote flows in this requirement’s scope.

#### Scenario: Authenticated operator can view and save settings

- **WHEN** an authenticated operator opens the Authority Manager settings surface and saves valid gap operator settings
- **THEN** the console persists them via the worker settings API and shows the updated values
- **AND** validation or worker errors are shown in plain language without secret material

#### Scenario: Unauthenticated operator cannot mutate settings

- **WHEN** the console session is anonymous, expired, or forbidden
- **THEN** settings mutation controls remain unavailable or fail closed with a clear re-auth cue

#### Scenario: Settings UI does not enable LinkedIn publish by implication

- **WHEN** an operator saves settings with any gap knobs including `gap_trigger_enabled`
- **THEN** the UI does not present saving settings as enabling LinkedIn API publish
- **AND** auto-trigger remains described as fail-closed while `gap_trigger_enabled` is false
