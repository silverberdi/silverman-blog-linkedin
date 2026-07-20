# flow-b-simplified-process

## MODIFIED Requirements

### Requirement: Cross-links without runtime implementation

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. Runtime next-week gap detection is owned by capability `flow-b-calendar-gap-detect` (US-077) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI topic discovery is owned by capability `flow-b-topic-discovery` (US-078) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI blog draft generation is owned by capability `flow-b-blog-draft-generation` (US-079) and MUST NOT be re-implemented inside this documentation-only capability. This capability SHALL NOT require implementing gap trigger or approve endpoints.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability's requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** gap trigger and approve runtime remain outside this capability's scope
- **AND** settings persistence, gap detect, topic discovery, and blog draft generation are referenced as separate runtime capabilities when present

## ADDED Requirements

### Requirement: Blog-draft-generation runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that AI blog **draft generation** is provided by capability `flow-b-blog-draft-generation` (US-079): authenticated worker HTTP that accepts US-078 topic payloads, generates Markdown + hero image pairs into `blog-posts/pending-approval/` (same pair rules as `ready/`), applies editorial canon and blocking anti-AI-writing rules at draft time, and records durable metadata linking `topic_id` and optional gap context — without writing `blog-posts/ready/` or invoking Flow A publish/package/schedule or LinkedIn API publish. Docs MUST state that approve/promote (US-080/US-081) and gap trigger (US-082) remain separate capabilities.

#### Scenario: Policy points at draft-generation capability

- **WHEN** an operator reads the Flow B simplified policy after US-079 lands
- **THEN** the docs identify the authenticated draft-generation worker path as the runtime step that materializes `pending-approval/` packages
- **AND** the docs do not claim approve/promote or gap trigger are implemented by draft generation alone
