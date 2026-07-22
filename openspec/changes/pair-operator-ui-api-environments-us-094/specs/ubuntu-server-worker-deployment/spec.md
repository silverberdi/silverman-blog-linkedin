## ADDED Requirements

### Requirement: Server env examples document UAT and prod UI↔API pairing defaults

The repository SHALL document non-secret UAT and prod pairing defaults in `deploy/server/` env examples or clearly separated overlays such that each profile sets matching `SILVERMAN_DEPLOYMENT_ENVIRONMENT` and `SILVERMAN_OPERATOR_UI_ENV_LABEL`, and points `SILVERMAN_OPERATOR_UI_API_BASE_URL` at that profile’s worker origin placeholder (UAT UI → UAT API placeholder; prod UI → prod API placeholder).

Examples MUST NOT embed real API keys or bearer tokens. Documenting these defaults MUST NOT claim that a live second UAT stack or full BL-029 CI/UAT stand-up is complete.

#### Scenario: UAT overlay pairs UI label and API base to UAT

- **WHEN** an operator reads the UAT pairing env example
- **THEN** worker and UI environment tokens are `uat` and the UI API base URL placeholder is the UAT worker origin (not the prod placeholder)

#### Scenario: Prod overlay pairs UI label and API base to prod

- **WHEN** an operator reads the prod pairing env example
- **THEN** worker and UI environment tokens are `prod` and the UI API base URL placeholder is the prod worker origin (not the UAT placeholder)

### Requirement: Deploy docs describe dual-service topology and US-094 pairing

Operator deploy documentation for the Ubuntu worker SHALL briefly describe the dual-service topology (worker API on `8010`, operator UI on the chosen UI port), state that browsers use the UI while n8n continues to call the worker HTTP API only, and SHALL describe US-094 UAT/prod UI↔API pairing (env var names, closed `uat`/`prod` vocabulary, and default overlays).

Documentation MUST NOT claim public console exposure beyond BL-026 accepted exposure and MUST NOT claim full BL-029 CI/UAT stand-up is complete merely because pairing defaults and validation exist.

#### Scenario: Deploy guide mentions both services and pairing

- **WHEN** an operator reads the updated ubuntu-server worker deployment guide after US-094
- **THEN** the guide identifies how to reach the separated operator UI and the worker API as distinct LAN endpoints, reiterates ADR-0001 (n8n → worker HTTP only), and documents UAT/prod pairing configuration by env var name

## REMOVED Requirements

### Requirement: Deploy docs describe dual-service topology without claiming US-094

**Reason:** Superseded by US-094 requirement that deploy docs describe dual-service topology **and** UAT/prod pairing (env var names and overlays), while still not claiming public exposure or full BL-029 stand-up.

**Migration:** Follow the ADDED requirement “Deploy docs describe dual-service topology and US-094 pairing.”
