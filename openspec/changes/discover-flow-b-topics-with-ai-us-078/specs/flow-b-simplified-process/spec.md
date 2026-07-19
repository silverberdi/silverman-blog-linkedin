## ADDED Requirements

### Requirement: Topic-discovery runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that AI topic **discovery** is provided by capability `flow-b-topic-discovery` (US-078): authenticated worker HTTP that returns authority-aligned topic choices (DeepSeek v1; provider-pluggable seam) using authority brief + editorial canon topic spaces + soft anti-dup, without writing draft packages to `blog-posts/pending-approval/` or `blog-posts/ready/`. Docs MUST state that draft generation (US-079), approve/promote (US-080/US-081), and gap trigger (US-082) remain separate capabilities.

#### Scenario: Policy points at discovery capability

- **WHEN** an operator reads the discovery section of the Flow B simplified policy after US-078 lands
- **THEN** the docs identify the authenticated discovery worker path as the runtime topic-discovery step
- **AND** the docs do not claim draft generation, approve/promote, or gap trigger are implemented by this discovery capability alone

## MODIFIED Requirements

### Requirement: Cross-links without runtime implementation

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. Runtime next-week gap detection is owned by capability `flow-b-calendar-gap-detect` (US-077) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI topic discovery is owned by capability `flow-b-topic-discovery` (US-078) and MUST NOT be re-implemented inside this documentation-only capability. This capability SHALL NOT require implementing gap trigger, draft generation, or approve endpoints.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability’s requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** gap trigger, draft generation, and approve runtime remain outside this capability’s scope
- **AND** settings persistence, gap detect, and topic discovery are referenced as separate runtime capabilities when present

### Requirement: Gap-detect runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that next-week LinkedIn calendar gap **detection** is provided by capability `flow-b-calendar-gap-detect` (US-077): authenticated detect-only worker HTTP that returns `gaps[]` / no-gap for the next operator-local week using settings from `flow-b-gap-operator-settings`, without mutating campaigns or starting drafts. Docs MUST state that detect MAY run for inspection when `gap_trigger_enabled=false`, and that auto-trigger remains a separate fail-closed capability (US-082). Docs MUST distinguish detect from discovery (`flow-b-topic-discovery` / US-078) and MUST NOT claim draft/approve/trigger are implemented by detect.

#### Scenario: Policy points at detect capability

- **WHEN** an operator reads the gap sensor section of the Flow B simplified policy after US-077 lands
- **THEN** the docs identify the authenticated detect-only worker path as the runtime sensor
- **AND** the docs distinguish detect (inspection) from trigger (US-082) and from discovery (US-078)
- **AND** the docs do not claim draft generation or approve/promote are implemented by detect
