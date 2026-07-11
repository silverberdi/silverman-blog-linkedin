## MODIFIED Requirements

### Requirement: Executable script scope boundary

Context governance changes MUST NOT modify executable defaults, logic, or expected-commit behavior in `scripts/flow_a_readiness.py`. Documentation, comments, and help text MAY be corrected. Updates to `DEFAULT_EXPECTED_COMMITS` MUST be performed only via a dedicated OpenSpec change scoped to Flow A readiness defaults (for example `correct-stale-flow-a-readiness-defaults`), not incidental context-alignment work.

#### Scenario: Readiness script defaults reviewed during context governance

- **WHEN** a context-governance-only change is applied
- **THEN** `scripts/flow_a_readiness.py` executable defaults and expected-commit behavior are unchanged

#### Scenario: Readiness defaults updated by dedicated change

- **WHEN** change `correct-stale-flow-a-readiness-defaults` is applied and synced
- **THEN** `DEFAULT_EXPECTED_COMMITS` reflects the documented operational baseline, the known-divergence row for stale defaults is removed from `docs/CURRENT-STATE.md`, and operator docs describe the new milestones
