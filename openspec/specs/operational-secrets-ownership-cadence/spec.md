# operational-secrets-ownership-cadence

## Purpose

Operator-visible normative ownership and rotation-cadence procedure for **BL-024 / US-059**: who owns each operational secret class and how often to review or rotate — including on-suspicion triggers and blocked/deferred vocabulary — without requiring live key rotation in this change, a secrets vault, US-058 checklist rewrite, BL-025 full token lifecycle rewrite, Flow A/B behavior changes, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

Operator procedure: `docs/operations/operational-secrets-ownership-cadence.md`.

## Requirements

### Requirement: Normative ownership and cadence artifact

The system documentation SHALL publish an operator-facing normative ownership and rotation-cadence procedure at `docs/operations/operational-secrets-ownership-cadence.md` that the system owner can open as the shared meaning of **BL-024 / US-059**. The document MUST identify BL-024 / US-059 as the product story it satisfies as procedure/policy, MUST name the system owner as the default owner for operational secrets in this deployment, MUST state that US-057 live rotation remains deferred unless separately approved, MUST NOT claim to rewrite BL-025 LinkedIn token lifecycle or BL-026 exposure review, and MUST state that BL-024 may close after US-059 Story accepted (with US-057 waived and US-058 accepted).

#### Scenario: Ownership cadence artifact is operator-visible

- **WHEN** a system owner opens the normative ownership and cadence procedure
- **THEN** the document exists at `docs/operations/operational-secrets-ownership-cadence.md`
- **AND** it identifies BL-024 / US-059 as the product story it satisfies as procedure
- **AND** it names ownership for operational secret classes
- **AND** it does not execute live key rotation as part of publishing the procedure

### Requirement: Ownership and cadence table covers secret classes

Normative docs SHALL provide an ownership and cadence table covering at minimum: worker API key paired with n8n `worker_api_key` (same rotation event); provider API keys (DeepSeek / ComfyUI); LinkedIn OAuth client secret and token-store class (with BL-025 as lifecycle detail pointer); GitHub Pages deploy key; and periodic re-audit using the US-058 permissions + secrets-absence procedure. Cadences MUST include the operator-approved defaults: **90 days** for worker/n8n API key and US-058 re-audit; **180 days** for provider keys and LinkedIn client secret; **1 year** for deploy key; plus **on suspected exposure** as an immediate trigger that overrides calendar cadence. Real secret values MUST never appear in the document.

#### Scenario: Table names owner and intervals

- **WHEN** an operator reads the ownership and cadence table
- **THEN** each listed secret class has an owner and a review/rotation interval
- **AND** on-suspicion exposure is listed as an immediate trigger
- **AND** worker API key and n8n `worker_api_key` are documented as a paired rotation

### Requirement: Blocked and deferred cadence outcomes

Normative docs SHALL define how to communicate when a due review or rotation cannot be completed: record `blocked` or `deferred` with a non-secret reason (for example no server access, provider outage, operator decision to defer). Missed or deferred cadence MUST NOT be silently omitted from operator records. Deferred US-057 rotation status remains valid until a separately approved rotation runs.

#### Scenario: Deferred cadence is explicit

- **WHEN** a scheduled rotation due date passes without execution by operator decision
- **THEN** the outcome is recorded as deferred or blocked with a non-secret reason
- **AND** the record does not claim the secret was rotated

### Requirement: Visibility pointers and independence

Normative docs SHALL make the US-059 procedure understandable via the ops artifact plus CURRENT-STATE / GLOSSARY (and light product) pointers after apply. A thin cross-link from the US-058 permissions-review procedure MAY be added and MUST NOT duplicate the US-058 checklist. The US-059 procedure MUST NOT require rotating live keys, rewriting server `.env`, mutating n8n `worker_api_key`, mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, or changing Flow A / Flow B behavior. Existing Worker API key rotation deployment docs MAY be referenced as the execution runbook when a rotation is separately approved.

#### Scenario: Procedure does not rotate or enable LinkedIn publication

- **WHEN** an operator follows the published US-059 ownership and cadence procedure as documentation
- **THEN** the procedure does not instruct live key rotation or n8n `worker_api_key` mutation as a required apply step
- **AND** it does not instruct changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
- **AND** it points to BL-025 for LinkedIn token lifecycle detail rather than redefining it
