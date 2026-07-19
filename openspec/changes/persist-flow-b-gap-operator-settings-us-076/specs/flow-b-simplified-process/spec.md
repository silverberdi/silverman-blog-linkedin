## MODIFIED Requirements

### Requirement: Cross-links without runtime implementation

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. This capability SHALL NOT require implementing gap detect, trigger, discovery, or approve endpoints.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability’s requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** gap detect, trigger, discovery, and approve runtime remain outside this capability’s scope

## ADDED Requirements

### Requirement: Operator-settings runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that editable gap operator settings are persisted via DB + Silverman Authority Manager UI (US-076 / `flow-b-gap-operator-settings`), with documented defaults including `gap_trigger_enabled=false`, and that sensor/trigger runtime stories consume those settings.

#### Scenario: Policy points at settings capability

- **WHEN** an operator reads the gap sensor / settings section of the Flow B simplified policy after US-076 lands
- **THEN** the docs identify Postgres + Authority Manager UI as the settings SoT path (not env-only long-term)
- **AND** defaults including fail-closed `gap_trigger_enabled` remain documented
