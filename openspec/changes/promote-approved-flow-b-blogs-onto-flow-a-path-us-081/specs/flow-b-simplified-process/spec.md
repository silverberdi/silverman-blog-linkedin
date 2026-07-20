## ADDED Requirements

### Requirement: Blog-draft-promotion runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that operator **promote** of approved AI blogs onto the Flow A path is provided by capability `flow-b-blog-draft-promotion` (US-081): authenticated worker HTTP (and Silverman Authority Manager promote affordance) that moves approved `blog-posts/pending-approval/` packages to `blog-posts/ready/`, records durable approval/promotion metadata, reuses Flow A publish/package/schedule/optional supervision without a second mandatory LinkedIn approval queue, and applies spill algorithm A when scheduling LinkedIn variants from Flow B–origin blogs under US-040K max 2. Docs MUST state that gap trigger remains a separate capability (US-082). Docs MUST NOT claim US-081 auto-publishes blog or LinkedIn without Flow A guards.

#### Scenario: Policy points at promote capability

- **WHEN** an operator reads the Flow B simplified policy after US-081 lands
- **THEN** the docs identify authenticated promote-to-`ready/` plus spill algorithm A runtime as the US-081 capability
- **AND** the docs do not claim gap trigger (US-082) is implemented by promote alone
- **AND** the docs do not claim promote auto-publishes without Flow A

## MODIFIED Requirements

### Requirement: Blog-draft-approval runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that operator **approve/reject presentation** for pending AI blogs is provided by capability `flow-b-blog-draft-approval` (US-080): authenticated worker HTTP plus Silverman Authority Manager UI that lists/presents drafts from `blog-posts/pending-approval/` (title/topic, body, image, discovery summary; gap week / empty-days when present), supports approve and reject actions, keeps rejected drafts non-publishable, and records approve decisions without promoting to `blog-posts/ready/`. Docs MUST state that promote/move to `ready/` and spill algorithm A are provided by capability `flow-b-blog-draft-promotion` (US-081) when that runtime exists, and that gap trigger remains US-082. Docs MUST NOT claim a revision-history CMS or mandatory edit-apply loop is required.

#### Scenario: Policy points at approve/reject capability

- **WHEN** an operator reads the Flow B simplified policy after US-080 lands
- **THEN** the docs identify authenticated worker + Silverman Authority Manager as the runtime approve/reject presentation path
- **AND** the docs do not claim promote-to-`ready/`, spill algorithm A, or gap trigger are implemented by this approve/reject capability alone

### Requirement: Cross-links without runtime implementation

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. Runtime next-week gap detection is owned by capability `flow-b-calendar-gap-detect` (US-077) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI topic discovery is owned by capability `flow-b-topic-discovery` (US-078) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI blog draft generation is owned by capability `flow-b-blog-draft-generation` (US-079) and MUST NOT be re-implemented inside this documentation-only capability. Runtime blog draft approve/reject presentation is owned by capability `flow-b-blog-draft-approval` (US-080) and MUST NOT be re-implemented inside this documentation-only capability. Runtime promote-to-`ready/` and spill algorithm A scheduling are owned by capability `flow-b-blog-draft-promotion` (US-081) and MUST NOT be re-implemented inside this documentation-only capability. This capability SHALL NOT require implementing gap trigger (US-082) endpoints.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability's requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** gap trigger runtime remains outside this capability's scope
- **AND** settings persistence, gap detect, topic discovery, blog draft generation, blog draft approve/reject presentation, and promote/spill A are referenced as separate runtime capabilities when present
