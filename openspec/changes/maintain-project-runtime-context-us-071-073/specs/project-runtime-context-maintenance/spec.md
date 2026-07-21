# project-runtime-context-maintenance

## Purpose

Operator-visible normative maintenance of project and runtime context for **BL-030 / US-071 + US-072 + US-073**: update CURRENT-STATE when capabilities change, update RUNTIME-STATE after deploy/live validation, detect contradictions, prevent historical documents from being treated as current, and keep Cursor guidance aligned with repository authority — without establishing CI (BL-029) or mutating LinkedIn publication enablement.

Operator procedure: `docs/operations/project-runtime-context-maintenance.md`.

## ADDED Requirements

### Requirement: Normative maintenance artifact

The system documentation SHALL publish an operator-facing project/runtime context maintenance procedure at `docs/operations/project-runtime-context-maintenance.md` identifying **BL-030 / US-071, US-072, and US-073**, covering when to update CURRENT-STATE and RUNTIME-STATE, how to record contradictions, how to banner or demote historical/bootstrap/archived artifacts, and how Cursor rules must remain subordinate pointers to CONTEXT-AUTHORITY (not volatile inventories). Publishing the procedure MUST NOT establish CI or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Maintenance procedure is operator-visible

- **WHEN** a system owner opens the maintenance procedure
- **THEN** the document exists at `docs/operations/project-runtime-context-maintenance.md`
- **AND** it identifies US-071, US-072, and US-073
- **AND** it states BL-029 is out of scope for this change

### Requirement: Update current and runtime state (US-071)

Normative docs SHALL require CURRENT-STATE updates when capabilities, topology, or completion layers change, and RUNTIME-STATE updates after deployment or live validation (secret-safe facts only). A live RUNTIME-STATE refresh supporting Story accepted MUST be attempted; if server access is unavailable, the outcome MUST be recorded as blocked/deferred without inventing live values.

#### Scenario: Update triggers are defined

- **WHEN** an operator follows the US-071 checklist
- **THEN** CURRENT-STATE and RUNTIME-STATE update triggers are listed
- **AND** RUNTIME-STATE is described as volatile and non-architectural

### Requirement: Contradiction detection and historical demotion (US-072)

Normative docs SHALL provide a contradiction-detection checklist (CURRENT-STATE internal consistency, CURRENT vs RUNTIME, context/ops status headers vs Story accepted, archive paths not cited as active requirements) and require Historical bootstrap banners (or equivalent demotion) for `docs/context/` and other superseded materials so they are not treated as current truth. A depth-C audit evidence file under `docs/operations/` MUST record findings and remediations without secret values.

#### Scenario: Historical material is not treated as current

- **WHEN** an operator reviews `docs/context/` or archived OpenSpec changes
- **THEN** the procedure states they are historical / evidence-only
- **AND** contradictions with CURRENT-STATE are recorded and remediated or explicitly deferred

### Requirement: Cursor and repository guidance alignment (US-073)

Normative docs SHALL require `.cursor/rules` project/engineering guidance to remain aligned with CONTEXT-AUTHORITY (link canonical docs; no volatile capability inventories embedded in rules). Misalignment discovered during the audit MUST be corrected or recorded.

#### Scenario: Cursor rules remain subordinate pointers

- **WHEN** an operator reviews always-on Cursor rules after this change
- **THEN** they point to CURRENT-STATE / CONTEXT-AUTHORITY / GLOSSARY rather than owning volatile status
- **AND** they do not contradict the published maintenance procedure

### Requirement: Visibility and independence

Normative docs SHALL update product pointers and close BL-030 when US-071–US-073 are Story accepted. The procedure MUST NOT require establishing continuous integration (BL-029 remains open) or LinkedIn enablement mutation.

#### Scenario: BL-029 remains open

- **WHEN** BL-030 is closed
- **THEN** product docs still show BL-029 / US-069 / US-070 as open unless separately accepted
