# warning-and-test-quality-baseline

## Purpose

Operator-visible normative warning and test quality baseline for **BL-028 / US-067 + US-068**: run the full suite(s), inventory warnings, correct cheap root causes, separate inherited vs new warnings, document the baseline, and maintain zero new warnings attributable to a change — without establishing CI (BL-029), mutating Flow A/B behavior, or mutating LinkedIn publication enablement.

Operator procedure: `docs/operations/warning-and-test-quality-baseline.md`.

## Requirements

### Requirement: Normative baseline artifact

The system documentation SHALL publish an operator-facing normative warning and test quality baseline procedure at `docs/operations/warning-and-test-quality-baseline.md` identifying **BL-028 / US-067 and US-068**, including how to run the primary pytest suite (and frontend Vitest when applicable), how to inventory warnings, how to separate **inherited** (documented baseline) from **new** (must not ship without fix or explicit justification), and the standing rule that changes MUST NOT introduce new warnings attributable to that change. Publishing the procedure alone MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or establish CI.

#### Scenario: Baseline procedure is operator-visible

- **WHEN** a system owner opens the normative baseline procedure
- **THEN** the document exists at `docs/operations/warning-and-test-quality-baseline.md`
- **AND** it identifies BL-028 / US-067 and US-068
- **AND** it states the zero-new-warnings-attributable-to-change rule

### Requirement: Full suite run and inventory (US-067)

Normative docs SHALL instruct operators to run the full suite, inventory warnings (category / module / message class — not secrets), and correct root causes where safe and cheap. A dated evidence file under `docs/operations/` MUST record pass/fail counts and warning inventory from at least one baseline run supporting Story accepted.

#### Scenario: Suite run and inventory are defined

- **WHEN** an operator follows the US-067 checklist
- **THEN** the procedure names how to invoke pytest (and Vitest if in scope)
- **AND** outcomes record suite results and warning inventory without secret values

### Requirement: Inherited vs new and documented baseline (US-068)

Normative docs SHALL separate inherited warnings (listed in the dated baseline) from new warnings introduced by a change, document the baseline as the shared meaning of “known quality problems,” and require maintainers to keep zero new warnings attributable to their change. Remaining inherited items MAY be deferred to later remediation or BL-029 automation without blocking BL-028 closure when the baseline is explicit.

#### Scenario: Inherited and new warnings are distinguishable

- **WHEN** an operator compares a change’s suite output to the documented baseline
- **THEN** warnings already listed as inherited are identifiable
- **AND** new warnings not in the baseline are treated as regressions to fix or justify
- **AND** the baseline document states the zero-new-warnings maintenance rule

### Requirement: Visibility and independence

Normative docs SHALL update CURRENT-STATE / GLOSSARY / light product pointers after apply. The procedure MUST NOT require establishing continuous integration (BL-029 remains separate), Flow A/B behavior changes, or LinkedIn publication enablement mutation.

#### Scenario: Procedure does not establish CI

- **WHEN** an operator completes the published BL-028 procedure
- **THEN** it does not require a GitHub Actions workflow as acceptance
- **AND** it does not instruct changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
