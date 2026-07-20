# flow-b-simplified-process

## Purpose

Normative documentation contracts for simplified Flow B (US-074 / US-075): process boundary, Silverman Authority Manager naming, `pending-approval/` eligibility, weekly calendar gap policy, spill algorithm A, and DeepSeek v1 discovery posture. Runtime settings, gap detect, topic discovery, and blog draft generation are separate capabilities (US-076 / US-077 / US-078 / US-079); approve/trigger remain separate (US-080–US-082).

Operator policy: `docs/operations/flow-b-simplified-policy.md`.

## Requirements

### Requirement: Simplified Flow B process boundary

The system documentation SHALL define Flow B as: weekly gap or explicit trigger → AI topic discovery → AI blog draft in `blog-posts/pending-approval/` → operator approve/reject in **Silverman Authority Manager** → on approve, promote to `blog-posts/ready/` → same path as Flow A. The **only** mandatory human gate SHALL be blog approval. After blog approval there SHALL be **no** mandatory LinkedIn review (optional Flow A supervision only).

#### Scenario: Process documented for operators

- **WHEN** an operator reads the normative Flow B simplified policy and glossary Flow B entry
- **THEN** the documented path matches weekly-gap/explicit-trigger → discovery → `pending-approval/` → Authority Manager approve/reject → `ready/` → Flow A
- **AND** LinkedIn after blog approval is described as optional supervision only (not a second mandatory gate)

### Requirement: Authority positioning and non-goals

Normative Flow B docs SHALL encode the career/authority objective (senior leadership / Solutions Architect / digital transformation / AI; ≥ ~USD 7,000 positioning) as **authority/referent**, not news rebroadcast. P4 non-goals SHALL include: revision-history CMS, structured feedback loops, thematic duplication engines, audience-balancing schedulers, BL-020 as a prerequisite, and news-spreader discovery.

#### Scenario: Non-goals and authority objective visible

- **WHEN** an operator reads the normative Flow B simplified policy
- **THEN** the authority/referent objective is stated
- **AND** the listed P4 non-goals are present (including news-spreader discovery and BL-020 not required)

### Requirement: Silverman Authority Manager naming

Normative docs SHALL name the operator product surface **Silverman Authority Manager** and SHALL state that Flow B approve/reject extends that surface (not a separate Flow B-only application).

#### Scenario: Product surface named

- **WHEN** an operator reads glossary and Flow B policy for the console product name
- **THEN** **Silverman Authority Manager** is the named surface for Flow B blog approve/reject extension

### Requirement: Publication eligibility via pending-approval

Normative docs SHALL state that unapproved drafts in `blog-posts/pending-approval/` MUST NOT publish blog or LinkedIn, Flow A MUST NOT consume that folder as publish input, and on approve drafts are promoted to `blog-posts/ready/` before Flow A MAY run.

#### Scenario: Eligibility gate documented

- **WHEN** an operator reads eligibility rules in the Flow B simplified policy
- **THEN** `pending-approval/` is non-publishable and non-consumable by Flow A
- **AND** approve promotes to `ready/` before Flow A eligibility

### Requirement: Weekly calendar gap trigger policy

Normative docs SHALL define the gap sensor as a **next** operator-local week (Mon–Sun) scan where a gap day has **0** LinkedIn posts (`pending`/`queued`/`published`); days with ≥1 are not gaps. Defaults SHALL include Friday afternoon local run intent, `min_lead_days` 5, `max_drafts_per_weekly_run` 2, knobs via DB+UI (US-076), orchestration **n8n Schedule → worker HTTP** with worker no-op when disabled or outside window, and ISO-week idempotency key `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}`.

#### Scenario: Gap policy defaults documented

- **WHEN** an operator reads the gap sensor section of the Flow B simplified policy
- **THEN** next-week scan, gap=0, Friday intent, min_lead_days 5, max 2 drafts, n8n→HTTP, and the ISO-week idempotency key are documented

### Requirement: Spill algorithm A and discovery posture

Normative docs SHALL document spill algorithm A for post-approve LinkedIn scheduling: (1) target-week gap days chronological → (2) other days in target week with capacity under max 2 → (3) forward day-by-day after the week. Discovery posture SHALL state DeepSeek-only v1 with provider-pluggable path for later models, and authority thesis inputs (not RSS/news as primary driver).

#### Scenario: Spill and discovery posture documented

- **WHEN** an operator reads spill and discovery sections of the Flow B simplified policy
- **THEN** spill algorithm A steps are listed in order
- **AND** DeepSeek v1 plus pluggable intent and non-news discovery posture are stated

### Requirement: Cross-links without runtime implementation

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. Runtime next-week gap detection is owned by capability `flow-b-calendar-gap-detect` (US-077) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI topic discovery is owned by capability `flow-b-topic-discovery` (US-078) and MUST NOT be re-implemented inside this documentation-only capability. Runtime AI blog draft generation is owned by capability `flow-b-blog-draft-generation` (US-079) and MUST NOT be re-implemented inside this documentation-only capability. Runtime blog draft approve/reject presentation is owned by capability `flow-b-blog-draft-approval` (US-080) and MUST NOT be re-implemented inside this documentation-only capability. Runtime promote-to-`ready/` and spill algorithm A scheduling are owned by capability `flow-b-blog-draft-promotion` (US-081) and MUST NOT be re-implemented inside this documentation-only capability. This capability SHALL NOT require implementing gap trigger (US-082) endpoints.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability's requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** gap trigger runtime remains outside this capability's scope
- **AND** settings persistence, gap detect, topic discovery, blog draft generation, blog draft approve/reject presentation, and promote/spill A are referenced as separate runtime capabilities when present

### Requirement: Operator-settings runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that editable gap operator settings are persisted via DB + Silverman Authority Manager UI (US-076 / `flow-b-gap-operator-settings`), with documented defaults including `gap_trigger_enabled=false`, and that sensor/trigger runtime stories consume those settings.

#### Scenario: Policy points at settings capability

- **WHEN** an operator reads the gap sensor / settings section of the Flow B simplified policy after US-076 lands
- **THEN** the docs identify Postgres + Authority Manager UI as the settings SoT path (not env-only long-term)
- **AND** defaults including fail-closed `gap_trigger_enabled` remain documented

### Requirement: Gap-detect runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that next-week LinkedIn calendar gap **detection** is provided by capability `flow-b-calendar-gap-detect` (US-077): authenticated detect-only worker HTTP that returns `gaps[]` / no-gap for the next operator-local week using settings from `flow-b-gap-operator-settings`, without mutating campaigns or starting drafts. Docs MUST state that detect MAY run for inspection when `gap_trigger_enabled=false`, and that auto-trigger remains a separate fail-closed capability (US-082). Docs MUST distinguish detect from discovery (`flow-b-topic-discovery` / US-078) and MUST NOT claim draft/approve/trigger are implemented by detect.

#### Scenario: Policy points at detect capability

- **WHEN** an operator reads the gap sensor section of the Flow B simplified policy after US-077 lands
- **THEN** the docs identify the authenticated detect-only worker path as the runtime sensor
- **AND** the docs distinguish detect (inspection) from trigger (US-082) and from discovery (US-078)
- **AND** the docs do not claim draft generation or approve/promote are implemented by detect

### Requirement: Topic-discovery runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that AI topic **discovery** is provided by capability `flow-b-topic-discovery` (US-078): authenticated worker HTTP that returns authority-aligned topic choices (DeepSeek v1; provider-pluggable seam) using authority brief + editorial canon topic spaces + soft anti-dup, without writing draft packages to `blog-posts/pending-approval/` or `blog-posts/ready/`. Docs MUST state that draft generation (US-079), approve/promote (US-080/US-081), and gap trigger (US-082) remain separate capabilities.

#### Scenario: Policy points at discovery capability

- **WHEN** an operator reads the discovery section of the Flow B simplified policy after US-078 lands
- **THEN** the docs identify the authenticated discovery worker path as the runtime topic-discovery step
- **AND** the docs do not claim draft generation, approve/promote, or gap trigger are implemented by this discovery capability alone

### Requirement: Blog-draft-generation runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that AI blog **draft generation** is provided by capability `flow-b-blog-draft-generation` (US-079): authenticated worker HTTP that accepts US-078 topic payloads, generates Markdown + hero image pairs into `blog-posts/pending-approval/` (same pair rules as `ready/`), applies editorial canon and blocking anti-AI-writing rules at draft time, and records durable metadata linking `topic_id` and optional gap context — without writing `blog-posts/ready/` or invoking Flow A publish/package/schedule or LinkedIn API publish. Docs MUST state that approve/reject presentation (US-080), promote (US-081), and gap trigger (US-082) remain separate capabilities.

#### Scenario: Policy points at draft-generation capability

- **WHEN** an operator reads the Flow B simplified policy after US-079 lands
- **THEN** the docs identify the authenticated draft-generation worker path as the runtime step that materializes `pending-approval/` packages
- **AND** the docs do not claim approve/reject, promote, or gap trigger are implemented by draft generation alone

### Requirement: Blog-draft-approval runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that operator **approve/reject presentation** for pending AI blogs is provided by capability `flow-b-blog-draft-approval` (US-080): authenticated worker HTTP plus Silverman Authority Manager UI that lists/presents drafts from `blog-posts/pending-approval/` (title/topic, body, image, discovery summary; gap week / empty-days when present), supports approve and reject actions, keeps rejected drafts non-publishable, and records approve decisions without promoting to `blog-posts/ready/`. Docs MUST state that promote/move to `ready/` and spill algorithm A are provided by capability `flow-b-blog-draft-promotion` (US-081) when that runtime exists, and that gap trigger remains US-082. Docs MUST NOT claim a revision-history CMS or mandatory edit-apply loop is required.

#### Scenario: Policy points at approve/reject capability

- **WHEN** an operator reads the Flow B simplified policy after US-080 lands
- **THEN** the docs identify authenticated worker + Silverman Authority Manager as the runtime approve/reject presentation path
- **AND** the docs do not claim promote-to-`ready/`, spill algorithm A, or gap trigger are implemented by this approve/reject capability alone

### Requirement: Blog-draft-promotion runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that operator **promote** of approved AI blogs onto the Flow A path is provided by capability `flow-b-blog-draft-promotion` (US-081): authenticated worker HTTP (and Silverman Authority Manager promote affordance) that moves approved `blog-posts/pending-approval/` packages to `blog-posts/ready/`, records durable approval/promotion metadata, reuses Flow A publish/package/schedule/optional supervision without a second mandatory LinkedIn approval queue, and applies spill algorithm A when scheduling LinkedIn variants from Flow B–origin blogs under US-040K max 2. Docs MUST state that gap trigger remains a separate capability (US-082). Docs MUST NOT claim US-081 auto-publishes blog or LinkedIn without Flow A guards.

#### Scenario: Policy points at promote capability

- **WHEN** an operator reads the Flow B simplified policy after US-081 lands
- **THEN** the docs identify authenticated promote-to-`ready/` plus spill algorithm A runtime as the US-081 capability
- **AND** the docs do not claim gap trigger (US-082) is implemented by promote alone
- **AND** the docs do not claim promote auto-publishes without Flow A
