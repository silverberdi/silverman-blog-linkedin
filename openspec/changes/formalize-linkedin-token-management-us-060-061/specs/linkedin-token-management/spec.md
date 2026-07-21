# linkedin-token-management

## Purpose

Operator-visible normative LinkedIn token management SoT for **BL-025 / US-060 + US-061**: secure storage, renewal/expiration, revocation, invalid-token detection, recovery, and development vs production separation — ratifying existing `linkedin-oauth-token-lifecycle` worker behavior without requiring a live invalid-token incident, publication enablement mutation, Flow A/B changes, or a secrets vault.

Operator procedure: `docs/operations/linkedin-token-management.md`.

## ADDED Requirements

### Requirement: Normative LinkedIn token management artifact

The system documentation SHALL publish an operator-facing normative LinkedIn token management procedure at `docs/operations/linkedin-token-management.md` that the system owner can open as the shared meaning of **BL-025 / US-060 and US-061**. The document MUST identify those product stories, MUST state that Story accepted may close BL-025 when both stories’ acceptance criteria are satisfied by the published procedure (plus optional status metadata evidence), MUST NOT require inventing an invalid token for acceptance when current OAuth status is healthy, and MUST NOT instruct mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as part of this procedure.

#### Scenario: Token management artifact is operator-visible

- **WHEN** a system owner opens the normative LinkedIn token management procedure
- **THEN** the document exists at `docs/operations/linkedin-token-management.md`
- **AND** it identifies BL-025 / US-060 and US-061
- **AND** it does not require a live invalid-token incident solely to accept the stories

### Requirement: Secure storage, renewal, and revocation (US-060)

Normative docs SHALL describe secure token storage (server-local OAuth env vars; host secrets directory / token store path classes with expected restrictive modes; never commit or log token cleartext), renewal and expiration behavior (refresh-before-publish when a refresh token exists; reauthorization when refresh is missing, expired, or fails), and revocation (clear or replace token store and reauthorize; revoke application access in LinkedIn Developer / account settings when appropriate). Docs MUST call out when production lacks a stored refresh token that access-token expiry requires reauthorization.

#### Scenario: Storage and renewal rules are documented

- **WHEN** an operator follows the US-060 sections of the SoT
- **THEN** storage locations and modes are named without secret values
- **AND** renewal vs reauthorization paths are distinguished
- **AND** revocation steps are described without printing tokens

### Requirement: Invalid detection, credential separation, and recovery (US-061)

Normative docs SHALL describe how invalid or action-required token states are detected (including `GET /linkedin/oauth/status` metadata and fail-closed publication / provider `action_required` codes such as reauthorization required), how development and production credentials are separated (distinct server vs local env and token-store path classes — a second LinkedIn Developer App is optional, not required by this procedure), and a recovery runbook (status → authorize → callback → status verify → dry-run publish as appropriate). Outcome vocabulary MUST communicate healthy vs action_required / blocked states without secret values.

#### Scenario: Detection and recovery are documented without forcing failure

- **WHEN** an operator follows the US-061 sections while OAuth status is currently healthy
- **THEN** detection signals and recovery steps are still fully documented
- **AND** the procedure does not require deliberately invalidating a working token to complete the reading
- **AND** development vs production separation guidance is present

### Requirement: Visibility, independence, and existing lifecycle ratification

Normative docs SHALL make the BL-025 SoT understandable via the ops artifact plus CURRENT-STATE / GLOSSARY (and light product) pointers after apply. The procedure MUST ratify existing `linkedin-oauth-token-lifecycle` behavior rather than contradict it, MUST NOT change Flow A / Flow B publish/package/schedule/discover/draft/promote behavior, and MUST NOT require live key rotation of unrelated BL-024 secrets. Thin cross-links from LinkedIn publication prerequisites and US-059 cadence documentation MAY be added.

#### Scenario: Procedure does not mutate LinkedIn publication enablement

- **WHEN** an operator completes the documented BL-025 token management procedure as published
- **THEN** the procedure does not instruct changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`
- **AND** it does not instruct unrelated worker API key rotation
