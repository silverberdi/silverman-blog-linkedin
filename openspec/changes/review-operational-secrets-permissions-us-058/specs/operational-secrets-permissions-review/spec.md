# operational-secrets-permissions-review

## Purpose

Operator-visible normative procedure for **BL-024 / US-058**: review permissions on operational secrets (least privilege; who/what can read; expected locations) and confirm secrets are absent from Git, logs, and n8n workflow exports — including blocked / confirmed-clean / finding vocabulary and optional evidence template (env var names only) — without requiring live key rotation (US-057 deferred), ownership/cadence definition (US-059), a secrets-management platform, auth middleware rewrite, Flow A/B behavior changes, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

Operator procedure: `docs/operations/operational-secrets-permissions-review.md`.

## ADDED Requirements

### Requirement: Normative operational secrets permissions review artifact

The system documentation SHALL publish an operator-facing normative permissions and secrets-absence review procedure at `docs/operations/operational-secrets-permissions-review.md` that the system owner can open as the shared meaning of **BL-024 / US-058**. The document MUST identify BL-024 / US-058 as the product story it satisfies as procedure/policy, MUST state that Story accepted and BL-024 closure require operator review beyond this documentation change (and that US-059 remains open), MUST state that US-057 key rotation remains deferred/waived and MUST NOT be executed as part of this procedure, and MUST NOT claim to close BL-024, US-059, BL-025, or BL-026.

#### Scenario: Permissions review artifact is operator-visible

- **WHEN** a system owner or operator opens the normative operational secrets permissions review procedure
- **THEN** the document exists at `docs/operations/operational-secrets-permissions-review.md`
- **AND** it identifies BL-024 / US-058 as the product story it satisfies as procedure
- **AND** it states that Story accepted / BL-024 closure require operator review beyond this docs change
- **AND** it states US-057 rotation remains deferred and is not performed by this procedure
- **AND** it does not mark US-059, BL-025, or BL-026 closed

### Requirement: Permissions review checklist covers secret-bearing surfaces

Normative docs SHALL provide a least-privilege permissions review checklist covering at minimum: worker process / container access to secrets; n8n credential and workflow variable holders (including `worker_api_key`); Docker/compose mounts for secrets and editorial/shared paths; OAuth/token store files and parent secrets directories; GitHub Pages deploy keys and related SSH known_hosts; and related service access that can read operational secrets. The checklist MUST name expected locations (server-local `.env`, host secrets directory / container mount paths as documented in deployment guides) and MUST instruct operators never to commit real secret values. The checklist MUST remain secrets-focused and MUST NOT absorb full BL-026 service-exposure scope (open ports, unrelated attack surface) as required US-058 content.

#### Scenario: Least-privilege checklist names surfaces and locations

- **WHEN** an operator follows the permissions review section
- **THEN** worker, n8n, Docker/compose mounts, OAuth/token files, deploy keys, and related secret-read access are listed
- **AND** expected secret locations such as server-local `.env` and secrets directories are named
- **AND** real secret values are forbidden in committed evidence
- **AND** BL-026 full exposure review is not required to complete the US-058 checklist

### Requirement: Secrets absence from Git, logs, and workflow exports

Normative docs SHALL provide a written checklist to confirm operational secrets are absent from: (1) Git / version-controlled files (no real `.env` values, no live tokens in committed workflow JSON or docs); (2) worker logs and HTTP responses (env var names only; no Bearer token values or client secrets); (3) n8n workflow exports (placeholders or expressions referencing credential names such as `worker_api_key` only — no real API keys or OAuth tokens). Optional automated scan aids MAY be documented; a mandatory secrets-management platform or new CI product MUST NOT be required to publish this procedure. Historical API-key rotation docs and `verify-worker-api-key-rotation.sh` MAY be referenced as context and MUST NOT be invoked as required US-058 rotation steps.

#### Scenario: Absence checklist covers Git, logs, and exports

- **WHEN** an operator follows the secrets-absence confirmation section
- **THEN** Git, logs/HTTP responses, and n8n workflow export hygiene checks are defined
- **AND** placeholders / env var names are the only allowed committed forms
- **AND** live key rotation is not required to complete the absence checklist

### Requirement: Review outcome vocabulary communicates blocked, clean, and findings

Normative docs SHALL define outcome vocabulary for each check and for the overall review: `blocked` when a check cannot be completed (for example no server access, export unavailable, mount not inspectable); `confirmed clean` when the check completed and no secret exposure or excessive permission was found; `finding — remediation required` when exposure or excessive permission was found. Findings MUST record path classes, env var **names**, and permission modes only — never secret values. Incomplete or blocked checks MUST NOT be recorded as `confirmed clean`. Deferred US-057 rotation MUST NOT by itself be recorded as a US-058 secrets-absence failure.

#### Scenario: Blocked is distinct from confirmed clean and findings

- **WHEN** an operator cannot access the server secrets directory during review
- **THEN** that check is recorded as `blocked` with a non-secret reason
- **AND** the overall review is not claimed as fully `confirmed clean` while any required check remains blocked
- **WHEN** a committed workflow export contains a live-looking API key value
- **THEN** the check is recorded as `finding — remediation required` using env var / field names only
- **AND** the finding text does not include the secret value

### Requirement: Visibility pointers and optional evidence template

Normative docs SHALL make the US-058 procedure understandable via the ops artifact plus CURRENT-STATE / GLOSSARY (and light product) pointers after apply. An optional checklist or evidence template MAY be published under `docs/operations/`; when present it MUST instruct operators to keep secrets out of git and to use env var names only in committed evidence. A thin cross-link from `docs/deployment/ubuntu-server-worker-deployment.md` MAY be added for discoverability and MUST NOT duplicate or reopen live rotation steps as US-058 requirements. Publishing the procedure MUST NOT alone mark US-058 Story accepted or close BL-024.

#### Scenario: Evidence template forbids secret values

- **WHEN** an optional US-058 evidence template exists under `docs/operations/`
- **THEN** it instructs operators not to commit real secrets
- **AND** it instructs use of env var names only in committed evidence
- **AND** CURRENT-STATE / product progress leave Story accepted and BL-024 open pending operator review

### Requirement: Independence from rotation, cadence, enablement, and pipelines

The US-058 procedure and capability MUST NOT require rotating live keys, rewriting server `.env`, mutating n8n `worker_api_key`, defining ownership/rotation cadence (US-059), formalizing LinkedIn token lifecycle (BL-025), mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, or changing Flow A / Flow B publish/package/schedule/discover/draft/promote behavior. Existing secret-safety norms (no secrets in HTTP responses/docs/commits; env-only keys; ADR-0001 HTTP-only) remain in force.

#### Scenario: Procedure does not rotate or enable LinkedIn publication

- **WHEN** an operator completes the documented US-058 review procedure as published
- **THEN** the procedure does not instruct live key rotation or n8n `worker_api_key` mutation
- **AND** it does not instruct changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
- **AND** it does not redefine US-059 ownership/cadence or BL-025 token lifecycle
