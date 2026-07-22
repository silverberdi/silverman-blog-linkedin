## MODIFIED Requirements

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
