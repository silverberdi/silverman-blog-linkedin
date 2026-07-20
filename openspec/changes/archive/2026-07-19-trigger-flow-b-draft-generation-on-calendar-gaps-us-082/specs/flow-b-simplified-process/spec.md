## ADDED Requirements

### Requirement: Gap-trigger runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that weekly **gap trigger** orchestration is provided by capability `flow-b-calendar-gap-trigger` (US-082): authenticated worker HTTP that, when `gap_trigger_enabled` is true and the operator-local weekly window is satisfied, consumes next-week gap detect and starts discovery + draft generation into `blog-posts/pending-approval/` up to `max_drafts_per_weekly_run`, with ISO-week idempotency key `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}`, orchestration via **n8n Schedule → worker HTTP** (repo export `active: false` until operator activation), and clean no-ops when disabled, outside window, no gap, or idempotent. Docs MUST state that trigger does **not** auto-publish blog or LinkedIn, does **not** skip the blog approval gate (US-080/US-081), and does **not** mark LinkedIn API published. Docs MUST NOT claim US-082 Story accepted or BL-019 closed without operator Story accepted gates.

#### Scenario: Policy points at gap-trigger capability

- **WHEN** an operator reads the gap sensor / trigger section of the Flow B simplified policy after US-082 lands
- **THEN** the docs identify the authenticated gap-trigger worker path plus inactive-until-activated n8n Schedule→HTTP orchestration as the runtime trigger
- **AND** the docs state fail-closed default `gap_trigger_enabled=false`, ISO-week idempotency, and pending-approval-only outputs
- **AND** the docs do not claim LinkedIn API published or BL-019 closed merely because trigger is implemented

## MODIFIED Requirements

### Requirement: Cross-links without runtime implementation

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. Runtime next-week gap detection is owned by capability `flow-b-calendar-gap-detect` (US-077) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI topic discovery is owned by capability `flow-b-topic-discovery` (US-078) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI blog draft generation is owned by capability `flow-b-blog-draft-generation` (US-079) and MUST NOT be re-implemented inside this documentation-only capability. Runtime blog draft approve/reject presentation is owned by capability `flow-b-blog-draft-approval` (US-080) and MUST NOT be re-implemented inside this documentation-only capability. Runtime promote-to-`ready/` and spill algorithm A scheduling are owned by capability `flow-b-blog-draft-promotion` (US-081) and MUST NOT be re-implemented inside this documentation-only capability. Runtime gap trigger orchestration is owned by capability `flow-b-calendar-gap-trigger` (US-082) and MUST NOT be re-implemented inside this documentation-only capability.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability's requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** settings persistence, gap detect, topic discovery, blog draft generation, blog draft approve/reject presentation, promote/spill A, and gap trigger are referenced as separate runtime capabilities when present

### Requirement: Blog-draft-promotion runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that operator **promote** of approved AI blogs onto the Flow A path is provided by capability `flow-b-blog-draft-promotion` (US-081): authenticated worker HTTP (and Silverman Authority Manager promote affordance) that moves approved `blog-posts/pending-approval/` packages to `blog-posts/ready/`, records durable approval/promotion metadata, reuses Flow A publish/package/schedule/optional supervision without a second mandatory LinkedIn approval queue, and applies spill algorithm A when scheduling LinkedIn variants from Flow B–origin blogs under US-040K max 2. Docs MUST state that gap trigger is provided by capability `flow-b-calendar-gap-trigger` (US-082) when that runtime exists. Docs MUST NOT claim US-081 auto-publishes blog or LinkedIn without Flow A guards.

#### Scenario: Policy points at promote capability

- **WHEN** an operator reads the Flow B simplified policy after US-081 lands
- **THEN** the docs identify authenticated promote-to-`ready/` plus spill algorithm A runtime as the US-081 capability
- **AND** the docs do not claim gap trigger (US-082) is implemented by promote alone
- **AND** the docs do not claim promote auto-publishes without Flow A
