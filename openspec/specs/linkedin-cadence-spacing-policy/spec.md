# linkedin-cadence-spacing-policy

## Purpose

Operator-visible ratification of LinkedIn campaign spacing (US-020 72h), frequency planning assumptions, blog frequency strategy expectations, interim coexistence with US-040K density and BL-019 gap trigger, and the normative “cadence conflict” definition consumed by later BL-021 stories (US-087–US-089) — without changing publish-time guard behavior.

Operator policy: `docs/operations/linkedin-cadence-spacing-policy.md`.

## Requirements

### Requirement: Normative LinkedIn cadence spacing policy artifact

The system documentation SHALL publish an operator-facing normative policy at `docs/operations/linkedin-cadence-spacing-policy.md` that calendar, scheduler, and console implementers can open as the shared meaning of LinkedIn cadence spacing and frequency for **BL-021 / US-051**. The policy MUST cross-link the existing publish-time guard operator contract in `docs/deployment/linkedin-publication-prerequisites.md` (US-020 section) and MUST NOT claim that this documentation change alone marks US-051 or BL-021 Story accepted.

#### Scenario: Policy artifact is operator-visible

- **WHEN** an operator or implementer opens the normative LinkedIn cadence spacing policy
- **THEN** the document exists at `docs/operations/linkedin-cadence-spacing-policy.md`
- **AND** it identifies BL-021 / US-051 as the product story it satisfies as policy
- **AND** it links the US-020 publish-time sequence and cadence guard prerequisites section
- **AND** it states that Story accepted / BL-021 closure require operator review beyond this docs change

### Requirement: Ratify US-020 same-campaign 72-hour spacing

Normative docs SHALL ratify the existing US-020 publish-time cadence rule as the normative LinkedIn **campaign** spacing rule: within one campaign, successful publications (`publish_state` `published` with valid stored `published_at` evidence) MUST be separated by a minimum real interval of **72 hours** (3 days). Cross-campaign independence MUST remain unchanged (one campaign’s publications MUST NOT gate another campaign’s). The policy MUST state that the worker publish-due / auto-queue path remains the authoritative enforcement of this rule and that this capability MUST NOT introduce a second cadence engine, weaken the guard, or invent a disagreeing constant.

#### Scenario: Spacing rule matches live publish-time guard meaning

- **WHEN** an operator reads the spacing section of the LinkedIn cadence spacing policy
- **THEN** minimum **72 hours** between successful same-campaign publications with evidence is stated as normative
- **AND** cross-campaign independence is stated
- **AND** the policy cites US-020 / `linkedin_publish_blocked_cadence` as the live enforcement meaning
- **AND** the policy forbids documenting a second conflicting cadence interval as authoritative

### Requirement: LinkedIn and blog frequency planning assumptions

Normative docs SHALL reaffirm the LinkedIn frequency planning assumption as filling toward approximately **two** LinkedIn publications per operator-local day via the interim **US-040K** density cap, unless a later approved OpenSpec change explicitly supersedes that number. Normative docs SHALL also reaffirm blog frequency at **strategy level**: blogs are paced to support LinkedIn filling (Flow A packaging of ready blogs; Flow B weekly gap fills bounded by `max_drafts_per_weekly_run`, default 2) and this story MUST NOT require automating a blog cadence engine.

#### Scenario: Frequency assumptions documented without automation

- **WHEN** an operator reads the frequency section of the LinkedIn cadence spacing policy
- **THEN** LinkedIn planning ≈ fill toward ~2 publications per operator-local day via US-040K is stated
- **AND** blog frequency is stated as strategy-level (supporting LinkedIn fill; no blog cadence automation required by US-051)
- **AND** the policy does not claim US-051 supersedes the US-040K max-2 number

### Requirement: Interim coexistence of density and gap controls

Normative docs SHALL clarify that **US-040K** local-day density (max 2 publications per operator-local day) and the **BL-019** Flow B gap trigger remain **interim coexisting controls** with US-020 cadence. Density MUST NOT be equated with cadence 72h spacing. The gap trigger MUST NOT be described as bypassing publish-time cadence. This story MUST NOT document a supersession of density or gap unless a later approved change does so explicitly.

#### Scenario: Density and gap are distinct from cadence

- **WHEN** an operator reads the coexistence section of the LinkedIn cadence spacing policy
- **THEN** US-040K density and BL-019 gap trigger are labeled interim coexisting controls
- **AND** density ≠ cadence 72h is stated explicitly
- **AND** gap trigger does not bypass cadence is stated explicitly
- **AND** no supersession of density or gap is claimed by US-051

### Requirement: Cadence conflict definition for later BL-021 stories

Normative docs SHALL define **cadence conflict** (for **US-087**, **US-088**, and **US-089**) as: at the variant’s `scheduled_at_utc` (or a proposed slot), a real publish-due / auto-queue path would refuse or skip for **cadence** — the same gate operators observe as `linkedin_publish_blocked_cadence` and related auto-queue cadence skip. Cadence conflict MUST NOT mean density-full alone, OAuth missing, publication enablement off, or sequence block alone. Sequence MUST remain documented as **distinct** from cadence conflict unless a later approved story expands conflict UX to include sequence.

#### Scenario: Cadence conflict is publish-time cadence gate only

- **WHEN** an implementer of US-087 / US-088 / US-089 reads the cadence conflict definition
- **THEN** conflict is defined as the US-020 cadence refuse/skip condition at `scheduled_at_utc` or proposed slot
- **AND** density-full alone, OAuth missing, and enablement-off are explicitly excluded from the cadence-conflict meaning
- **AND** sequence is stated as distinct from cadence conflict

### Requirement: Blocked-state vocabulary and non-duplication of US-020

Normative docs SHALL communicate failures and blocked states in plain language that distinguishes at least: cadence block (`linkedin_publish_blocked_cadence` / related cadence skip), sequence block, density-full / local-day saturation, publication enablement off, and OAuth / credentials action required. The docs-only change MUST NOT modify worker publish-time cadence evaluation, env defaults, n8n workflows, LinkedIn publish-due cron, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. US-020 / BL-007 MUST remain closed and authoritative at send time.

#### Scenario: Docs-only scope preserves publish-time guard

- **WHEN** this capability’s change tasks are completed
- **THEN** the normative policy includes clear blocked-state distinctions including cadence vs density vs enablement vs OAuth vs sequence
- **AND** no worker cadence math, cron, n8n, or enablement changes are introduced by this capability
- **AND** CURRENT-STATE (or equivalent ops pointer) references the policy as the shared cadence meaning without claiming Story accepted solely from the proposal
