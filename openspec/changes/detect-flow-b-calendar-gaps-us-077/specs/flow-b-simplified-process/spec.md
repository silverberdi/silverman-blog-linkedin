## ADDED Requirements

### Requirement: Gap-detect runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that next-week LinkedIn calendar gap **detection** is provided by capability `flow-b-calendar-gap-detect` (US-077): authenticated detect-only worker HTTP that returns `gaps[]` / no-gap for the next operator-local week using settings from `flow-b-gap-operator-settings`, without mutating campaigns or starting drafts. Docs MUST state that detect MAY run for inspection when `gap_trigger_enabled=false`, and that auto-trigger remains a separate fail-closed capability (US-082).

#### Scenario: Policy points at detect capability

- **WHEN** an operator reads the gap sensor section of the Flow B simplified policy after US-077 lands
- **THEN** the docs identify the authenticated detect-only worker path as the runtime sensor
- **AND** the docs distinguish detect (inspection) from trigger (US-082) and do not claim discovery/draft/approve are implemented

## MODIFIED Requirements

### Requirement: Cross-links without runtime implementation

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. Runtime next-week gap detection is owned by capability `flow-b-calendar-gap-detect` (US-077) and MUST NOT be re-implemented inside this documentation-only capability. This capability SHALL NOT require implementing gap trigger, discovery, or approve endpoints.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability’s requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** gap trigger, discovery, and approve runtime remain outside this capability’s scope
- **AND** settings persistence and gap detect are referenced as separate runtime capabilities when present
