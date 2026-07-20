## MODIFIED Requirements

### Requirement: Cross-links without runtime implementation

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. Runtime next-week gap detection is owned by capability `flow-b-calendar-gap-detect` (US-077) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI topic discovery is owned by capability `flow-b-topic-discovery` (US-078) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI blog draft generation is owned by capability `flow-b-blog-draft-generation` (US-079) and MUST NOT be re-implemented inside this documentation-only capability. Runtime blog draft approve/reject presentation is owned by capability `flow-b-blog-draft-approval` (US-080) and MUST NOT be re-implemented inside this documentation-only capability. This capability SHALL NOT require implementing gap trigger or promote-to-`ready/` endpoints.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability's requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** gap trigger and promote-to-`ready/` runtime remain outside this capability's scope
- **AND** settings persistence, gap detect, topic discovery, blog draft generation, and blog draft approve/reject presentation are referenced as separate runtime capabilities when present

### Requirement: Blog-draft-generation runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that AI blog **draft generation** is provided by capability `flow-b-blog-draft-generation` (US-079): authenticated worker HTTP that accepts US-078 topic payloads, generates Markdown + hero image pairs into `blog-posts/pending-approval/` (same pair rules as `ready/`), applies editorial canon and blocking anti-AI-writing rules at draft time, and records durable metadata linking `topic_id` and optional gap context — without writing `blog-posts/ready/` or invoking Flow A publish/package/schedule or LinkedIn API publish. Docs MUST state that approve/reject presentation (US-080), promote (US-081), and gap trigger (US-082) remain separate capabilities.

#### Scenario: Policy points at draft-generation capability

- **WHEN** an operator reads the Flow B simplified policy after US-079 lands
- **THEN** the docs identify the authenticated draft-generation worker path as the runtime step that materializes `pending-approval/` packages
- **AND** the docs do not claim approve/reject, promote, or gap trigger are implemented by draft generation alone

## ADDED Requirements

### Requirement: Blog-draft-approval runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that operator **approve/reject presentation** for pending AI blogs is provided by capability `flow-b-blog-draft-approval` (US-080): authenticated worker HTTP plus Silverman Authority Manager UI that lists/presents drafts from `blog-posts/pending-approval/` (title/topic, body, image, discovery summary; gap week / empty-days when present), supports approve and reject actions, keeps rejected drafts non-publishable, and records approve decisions without promoting to `blog-posts/ready/`. Docs MUST state that promote/move to `ready/` and spill algorithm A remain a separate capability (US-081), and that gap trigger remains US-082. Docs MUST NOT claim a revision-history CMS or mandatory edit-apply loop is required.

#### Scenario: Policy points at approve/reject capability

- **WHEN** an operator reads the Flow B simplified policy after US-080 lands
- **THEN** the docs identify authenticated worker + Silverman Authority Manager as the runtime approve/reject presentation path
- **AND** the docs do not claim promote-to-`ready/`, spill algorithm A, or gap trigger are implemented by this approve/reject capability alone
