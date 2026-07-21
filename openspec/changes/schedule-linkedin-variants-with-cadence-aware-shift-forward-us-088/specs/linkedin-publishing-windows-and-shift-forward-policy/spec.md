## MODIFIED Requirements

### Requirement: Fail-closed bounds when no feasible slot exists

Normative docs SHALL define fail-closed bounds for schedule-time placement (consumed and **enforced** by **US-088**): forward search MUST be finite with a documented default horizon of **28 operator-local days** from the original candidate local day; there MUST be no infinite scan; if no feasible slot is found within the horizon, scheduling MUST fail closed with a structured operator-visible error. Exact error code/shape for runtime enforcement is owned by capability `linkedin-distribution-scheduling-model` (US-088; code `linkedin_schedule_no_feasible_slot`). Preferred windows and shift-forward feasibility rules in this capability remain the policy source; US-088 MUST NOT change the numeric horizon or preferred-window definitions without a later approved OpenSpec change.

#### Scenario: No feasible slot within horizon fails closed

- **WHEN** an implementer or operator reads the no-feasible-slot bounds
- **THEN** the default forward search horizon is documented as 28 operator-local days
- **AND** infinite scan is forbidden
- **AND** failure to find a feasible slot within bounds requires fail-closed structured error enforced by US-088 schedule-time placement
- **AND** the policy states preferred windows / horizon numbers are not redefined by US-088

### Requirement: Shift-forward when candidate slot is cadence-infeasible

Normative docs SHALL define rescheduling rules: when a candidate `scheduled_at_utc` (or proposed slot) is **cadence-infeasible** under the US-051 cadence-conflict meaning (same gate as live `linkedin_publish_blocked_cadence` / related cadence skip), the system MUST **shift forward** to the next **feasible** slot. A feasible slot MUST satisfy: not cadence-conflicted; remaining capacity under interim US-040K max **2** publications per operator-local day; and existing distribution strategy constraints for the scheduling path in use (stagger / spill rules as applicable). The policy MUST forbid silently keeping an infeasible time as if it will send. The policy MUST NOT reimplement or weaken the US-020 publish-time cadence guard and MUST NOT invent a second cadence engine or disagreeing 72h constant. Executable schedule-time enforcement of these rules for new placements is owned by **US-088** (`linkedin-distribution-scheduling-model`); replan of already-Scheduled conflicts remains **US-089**.

#### Scenario: Cadence-infeasible candidate requires forward shift

- **WHEN** an implementer of US-088 reads the shift-forward section
- **THEN** cadence-infeasible candidates MUST shift forward to the next feasible slot
- **AND** feasible slots MUST also respect US-040K max 2/local day and existing strategy constraints
- **AND** silently keeping an infeasible `scheduled_at_utc` as sendable is forbidden
- **AND** a second cadence engine or disagreeing 72h constant is forbidden
- **AND** executable new-placement enforcement is identified as US-088 (not US-089 replan)
