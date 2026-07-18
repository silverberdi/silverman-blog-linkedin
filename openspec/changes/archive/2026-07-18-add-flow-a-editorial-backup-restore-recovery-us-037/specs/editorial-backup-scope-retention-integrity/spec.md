## ADDED Requirements

### Requirement: US-037 owns restoration and recovery procedure

The editorial backup scope/retention/integrity capability MUST remain limited to defining backup scope, retention, and integrity verification. Restoration testing and the operator recovery procedure MUST be owned by US-037 / `editorial-backup-restore-recovery`.

Operator-facing US-036 materials MUST point operators to the US-037 recovery procedure for restore drills and live recovery steps, without changing US-036 scope inventory, retention rules, package layout, or integrity verification contracts.

#### Scenario: US-036 policy points to US-037 for restore

- **WHEN** an operator reads the US-036 boundary or out-of-scope section in `docs/operations/editorial-backup-scope-retention-integrity.md`
- **THEN** the document states that restore drills and the recovery procedure belong to US-037 and references the US-037 recovery procedure document when present

#### Scenario: Integrity verification still does not restore

- **WHEN** integrity verification completes with any status
- **THEN** source editorial trees outside the inspected backup package are not written, moved, or restored by the verifier (restore remains a US-037 operation)
