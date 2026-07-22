## MODIFIED Requirements

### Requirement: Deploy docs describe dual-service topology and US-094 pairing

Operator deploy documentation for the Ubuntu worker SHALL briefly describe the dual-service topology (worker API on `8010`, operator UI on the chosen UI port), state that browsers use the separated UI while n8n continues to call the worker HTTP API only, and SHALL describe US-094 UAT/prod UI↔API pairing (env var names, closed `uat`/`prod` vocabulary, and default overlays).

After US-096, documentation MUST state that the supported operator console path is exclusively the separated UI service and MUST NOT present worker-embedded `GET /flow-a/console/linkedin-variant-supervision` (or equivalent) as a supported or compatibility production path. Documentation MUST note that former worker console URLs fail closed with a clear operator-visible outcome.

Documentation MUST NOT claim public console exposure beyond BL-026 accepted exposure and MUST NOT claim full BL-029 CI/UAT stand-up is complete merely because pairing defaults and validation exist.

#### Scenario: Deploy guide mentions both services and pairing

- **WHEN** an operator reads the updated ubuntu-server worker deployment guide after US-096
- **THEN** the guide identifies how to reach the separated operator UI and the worker API as distinct LAN endpoints, reiterates ADR-0001 (n8n → worker HTTP only), documents UAT/prod pairing configuration by env var name, and does not present the embedded worker console as a supported or compatibility production path

#### Scenario: Deploy guide notes decommissioned worker console URLs

- **WHEN** an operator reads the updated ubuntu-server worker deployment guide after US-096
- **THEN** the guide states that former worker console URLs fail closed and that operators should use the separated UI port (default `8011`)

## ADDED Requirements

### Requirement: Worker image build does not embed the operator console SPA

The isolated Ubuntu server worker image build MUST NOT require a frontend production embed step (`build:embedded`, copying console assets into the worker package static tree, or equivalent) for a successful API image build after US-096.

Compose comments and deploy scripts MUST treat `silverman-operator-ui` as the exclusive supported console service and MUST NOT instruct operators to embed the SPA into the worker for production.

#### Scenario: Worker Dockerfile does not require build embedded

- **WHEN** an operator follows the documented worker image build after US-096
- **THEN** the instructions do not require `npm run build:embedded` (or equivalent) before building the worker API image

#### Scenario: Compose treats separated UI as exclusive console

- **WHEN** an operator inspects server compose comments or UI service docs after US-096
- **THEN** the separated operator UI service is described as the supported console path and the worker is not described as hosting a compatibility console SPA
