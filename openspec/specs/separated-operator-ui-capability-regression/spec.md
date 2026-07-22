# separated-operator-ui-capability-regression

## Purpose

Focused capability-regression / smoke evidence that day-to-day operator supervision remains available on the supported separated operator UI → worker API path after US-093 separation and US-094 environment pairing (BL-034 / US-095). Verifies absolute-base reads, representative gated mutations, US-040D auth session gating, and fail-closed config/pairing holds—without redesigning packaging/pairing, implementing Google/OIDC, or claiming public exposure beyond BL-026.

## Requirements

### Requirement: Focused separated-UI capability regression matrix

After operator UI/API separation (US-093) and environment pairing (US-094), the system SHALL provide a focused regression/smoke program that demonstrates day-to-day operator supervision remains available on the supported production path: separated operator UI → worker API over HTTP using `SILVERMAN_OPERATOR_UI_API_BASE_URL` (and paired environment labels where required).

The minimum matrix MUST cover all of the following:

1. Typed client absolute base-URL behavior in separated mode (no relative same-origin fallback when separated config is valid).
2. Schedule visibility read via the typed client against the configured absolute worker origin.
3. Pending-supervision / LinkedIn control-center read (BL-032 Story-accepted path) via the typed client against the configured absolute worker origin.
4. At least one representative authenticated mutation already Story accepted under BL-032, preferring a dry-run-safe or clearly gated action (for example postpone/defer with `dry_run: true`), issued against the configured absolute worker origin—without inventing new endpoints.
5. US-040D auth session gating on the separated UI: sign-in, `canMutate`, and clear session, without implementing Google/OIDC.
6. Retention of US-093 configuration fail-closed and US-094 pairing fail-closed operator-visible blocked states.
7. Confirmation that ADR-0001 remains intact (n8n → worker HTTP only) and that this program does not mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or rewrite Flow/LinkedIn business contracts.

Evidence MUST be collectible via automated tests and/or controlled local/LAN smoke. Documentation of evidence MUST NOT claim public console exposure beyond BL-026 accepted exposure and MUST NOT mark Story accepted solely because tests were written.

#### Scenario: Absolute base URL used for schedule visibility

- **WHEN** the separated UI typed client is configured with a valid absolute worker API base URL and requests schedule visibility
- **THEN** the HTTP call targets `{apiBaseUrl}/flow-a/schedule-visibility` (with required query params) and does not fall back to a UI-origin relative path

#### Scenario: Absolute base URL used for pending-supervision read

- **WHEN** the separated UI typed client is configured with a valid absolute worker API base URL and requests pending-supervision
- **THEN** the HTTP call targets `{apiBaseUrl}/flow-a/linkedin-variants/pending-supervision` and does not fall back to a UI-origin relative path

#### Scenario: Dry-run-safe control-center mutation uses absolute base URL

- **WHEN** an authenticated separated-UI session with `canMutate` true issues a representative BL-032 mutation with dry-run enabled (for example defer/postpone with `dry_run: true`)
- **THEN** the request is sent to the configured absolute worker origin using the existing mutation route and does not introduce a new endpoint

#### Scenario: Auth session gating works without Google

- **WHEN** an operator signs in via the existing US-040D Bearer/session boundary on the separated UI and later clears the session
- **THEN** `canMutate` becomes true only while authenticated for mutations and returns to a non-mutating state after clear session, without requiring Google/OIDC

#### Scenario: Config and pairing blocks remain visible

- **WHEN** separated-UI API base URL configuration is invalid or UI↔API environment pairing fails
- **THEN** the operator still sees the existing clear blocked states and authenticated supervision/mutation traffic does not proceed

#### Scenario: Regression evidence stays honest about exposure and acceptance

- **WHEN** US-095 regression evidence is recorded in docs or checklists
- **THEN** the record does not claim public console exposure beyond BL-026 and does not claim Story accepted without the operator acceptance gate

### Requirement: Separated-UI regression preserves non-goals

The US-095 regression program MUST NOT implement BL-035 Google/OIDC login, MUST NOT stand up full BL-029 CI/UAT beyond what the matrix needs, MUST NOT introduce n8n Execute Command, MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and MUST NOT redesign US-093 packaging or US-094 pairing semantics (verify hold only).

US-096 hard decommission of the embedded worker console is intentionally out of scope for the US-095 program itself; after US-096 lands, regression holds for the separated path MUST remain applicable and MUST NOT depend on restoring the embedded console.

#### Scenario: US-095 does not itself perform US-096 decommission

- **WHEN** US-095 regression work is reviewed in isolation from US-096
- **THEN** that US-095 program is not required to remove the embedded console (removal is owned by US-096)

#### Scenario: Separated regression holds do not require embedded console

- **WHEN** US-096 has decommissioned the embedded console and US-095 hold suites are re-run
- **THEN** those holds continue to validate the separated UI → API path and do not require the worker to serve the former embedded SPA

#### Scenario: Publication enablement unchanged by regression program

- **WHEN** US-095 changes are reviewed for publication guards
- **THEN** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not mutated as part of the regression program
