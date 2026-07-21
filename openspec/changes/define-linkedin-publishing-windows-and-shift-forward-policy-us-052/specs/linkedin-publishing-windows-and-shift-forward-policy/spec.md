# linkedin-publishing-windows-and-shift-forward-policy

## Purpose

Operator-visible normative preferred LinkedIn publishing windows (local-day / clock guidance), strategy-level audience balancing (variant packaging remains Flow A), shift-forward reschedule rules when a candidate slot is cadence-infeasible under the US-051/US-020 cadence-conflict meaning, residual US-087 warning obligation, and fail-closed “no feasible slot” bounds for US-088 — without implementing schedule-time code, console warning UI, or changing publish-time 72h math.

Operator policy: `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md`.

Prerequisite meaning: `docs/operations/linkedin-cadence-spacing-policy.md` / capability `linkedin-cadence-spacing-policy` (US-051).

## ADDED Requirements

### Requirement: Normative publishing windows and shift-forward policy artifact

The system documentation SHALL publish an operator-facing normative policy at `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md` that calendar and scheduler implementers can open as the shared meaning of preferred LinkedIn publishing windows and shift-forward reschedule rules for **BL-021 / US-052**. The policy MUST cross-link the US-051 cadence spacing policy and editorial `#linkedin-distribution-strategy` preferred windows, and MUST NOT claim that this documentation change alone marks US-052 or BL-021 Story accepted.

#### Scenario: Policy artifact is operator-visible

- **WHEN** an operator or implementer opens the normative LinkedIn publishing windows and shift-forward policy
- **THEN** the document exists at `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md`
- **AND** it identifies BL-021 / US-052 as the product story it satisfies as policy
- **AND** it links the US-051 cadence spacing policy (cadence conflict meaning)
- **AND** it states that Story accepted / BL-021 closure require operator review beyond this docs change

### Requirement: Preferred publishing windows at strategy level

Normative docs SHALL define preferred LinkedIn publishing windows for variant placement at strategy level as: preferred operator-local days **Tuesday, Wednesday, Thursday**; preferred local clock windows **08:00–10:00** or **16:00–18:00**; operator timezone **America/Bogota**. The policy MUST cross-link `content-strategy/silverman-editorial-system.md` `#linkedin-distribution-strategy` and MUST state that these windows are placement guidance — not a second publish-time cadence engine. Publish-time same-campaign **72 hours** between successful `published` evidence (US-020 / US-051) remains authoritative at send.

#### Scenario: Preferred windows match editorial guidance without new cadence math

- **WHEN** an operator reads the publishing windows section of the US-052 policy
- **THEN** Tue–Thu preferred days, 08:00–10:00 or 16:00–18:00 local clock windows, and America/Bogota are stated
- **AND** the policy cross-links editorial `#linkedin-distribution-strategy`
- **AND** the policy states windows are not a second publish-time cadence engine
- **AND** US-020 / US-051 72h publish-time authority at send is restated

### Requirement: Audience balancing remains strategy-level; packaging stays Flow A

Normative docs SHALL state that audience-segment balancing for LinkedIn variants is **strategy-level** (editorial audience sequencing / lenses already in editorial canon) and that variant **packaging** ownership remains Flow A. This capability MUST NOT move packaging ownership out of Flow A and MUST NOT invent a Flow B-owned audience balancer.

#### Scenario: Packaging ownership unchanged

- **WHEN** an operator reads the audience balancing section of the US-052 policy
- **THEN** audience balancing is described as strategy-level sequencing from editorial canon
- **AND** Flow A packaging ownership is stated as unchanged
- **AND** the policy does not assign packaging ownership to Flow B

### Requirement: Shift-forward when candidate slot is cadence-infeasible

Normative docs SHALL define rescheduling rules: when a candidate `scheduled_at_utc` (or proposed slot) is **cadence-infeasible** under the US-051 cadence-conflict meaning (same gate as live `linkedin_publish_blocked_cadence` / related cadence skip), the system MUST **shift forward** to the next **feasible** slot. A feasible slot MUST satisfy: not cadence-conflicted; remaining capacity under interim US-040K max **2** publications per operator-local day; and existing distribution strategy constraints for the scheduling path in use (stagger / spill rules as applicable). The policy MUST forbid silently keeping an infeasible time as if it will send. The policy MUST NOT reimplement or weaken the US-020 publish-time cadence guard and MUST NOT invent a second cadence engine or disagreeing 72h constant.

#### Scenario: Cadence-infeasible candidate requires forward shift

- **WHEN** an implementer of US-088 reads the shift-forward section
- **THEN** cadence-infeasible candidates MUST shift forward to the next feasible slot
- **AND** feasible slots MUST also respect US-040K max 2/local day and existing strategy constraints
- **AND** silently keeping an infeasible `scheduled_at_utc` as sendable is forbidden
- **AND** a second cadence engine or disagreeing 72h constant is forbidden

### Requirement: Fail-closed bounds when no feasible slot exists

Normative docs SHALL define fail-closed bounds for schedule-time placement (consumed by **US-088**): forward search MUST be finite with a documented default horizon of **28 operator-local days** from the original candidate local day; there MUST be no infinite scan; if no feasible slot is found within the horizon, scheduling MUST fail closed with a structured operator-visible error (exact error shape owned by US-088). The policy MUST state that this docs change does not itself implement the scan.

#### Scenario: No feasible slot within horizon fails closed

- **WHEN** an implementer of US-088 reads the no-feasible-slot bounds
- **THEN** the default forward search horizon is documented as 28 operator-local days
- **AND** infinite scan is forbidden
- **AND** failure to find a feasible slot within bounds requires fail-closed structured error (US-088)
- **AND** the policy states executable enforcement is US-088, not this docs change

### Requirement: Residual cadence conflict still requires US-087 warning

Normative docs SHALL state that if a Scheduled item remains cadence-conflicted after placement (edge case), the console MUST still show the **US-087** cadence-conflict warning. This capability MUST NOT implement the console warning UI.

#### Scenario: Residual conflict warning obligation documented

- **WHEN** an implementer of US-087 or US-088 reads the residual-conflict section
- **THEN** residual cadence-conflicted Scheduled items MUST still show the US-087 warning
- **AND** this capability does not claim to implement the warning UI

### Requirement: Blocked-state communication and non-duplication of US-020

Normative docs SHALL communicate failures and blocked states in plain language that distinguishes at least: cadence conflict / cadence block; density-full / local-day saturation; no feasible slot within documented bounds; and (by reference to US-051) sequence, enablement-off, and OAuth as distinct non-cadence classes. The docs-only change MUST NOT modify worker publish-time cadence evaluation, schedule placement code, env defaults, n8n workflows, LinkedIn publish-due cron, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. US-020 / BL-007 MUST remain closed and authoritative at send time.

#### Scenario: Docs-only scope preserves publish-time guard and schedule code

- **WHEN** this capability’s change tasks are completed
- **THEN** the normative policy includes clear blocked-state distinctions including cadence vs density vs no-feasible-slot
- **AND** no worker cadence math, schedule shift-forward code, cron, n8n, or enablement changes are introduced by this capability
- **AND** CURRENT-STATE (or equivalent ops pointer) references the policy as the shared windows / shift-forward meaning without claiming Story accepted solely from the proposal
