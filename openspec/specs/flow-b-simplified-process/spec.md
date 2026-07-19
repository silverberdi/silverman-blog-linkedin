# flow-b-simplified-process

## Purpose

Normative documentation contracts for simplified Flow B (US-074 / US-075): process boundary, Silverman Authority Manager naming, `pending-approval/` eligibility, weekly calendar gap policy, spill algorithm A, and DeepSeek v1 discovery posture. Runtime sensor/settings/discovery/approve are separate capabilities (US-076–US-082).

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

US-074/US-075 documentation SHALL cross-link weekly gap policy and operator-settings. Policy docs remain the normative source for process boundary, eligibility, gap semantics, spill algorithm A, and discovery posture. Runtime persistence and UI for operator settings are owned by capability `flow-b-gap-operator-settings` (US-076) and MUST NOT be re-implemented inside this documentation-only capability. This capability SHALL NOT require implementing gap detect, trigger, discovery, or approve endpoints.

#### Scenario: Docs-only scope preserved for US-074/US-075

- **WHEN** this documentation capability’s requirements are evaluated
- **THEN** normative docs and glossary/editorial alignment exist for simplified Flow B
- **AND** gap detect, trigger, discovery, and approve runtime remain outside this capability’s scope

### Requirement: Operator-settings runtime cross-link

Normative Flow B simplified policy and related product docs SHALL state that editable gap operator settings are persisted via DB + Silverman Authority Manager UI (US-076 / `flow-b-gap-operator-settings`), with documented defaults including `gap_trigger_enabled=false`, and that sensor/trigger runtime stories consume those settings.

#### Scenario: Policy points at settings capability

- **WHEN** an operator reads the gap sensor / settings section of the Flow B simplified policy after US-076 lands
- **THEN** the docs identify Postgres + Authority Manager UI as the settings SoT path (not env-only long-term)
- **AND** defaults including fail-closed `gap_trigger_enabled` remain documented
