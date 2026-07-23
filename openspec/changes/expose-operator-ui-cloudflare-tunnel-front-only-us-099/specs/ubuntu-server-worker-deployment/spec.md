## MODIFIED Requirements

### Requirement: Deploy docs describe dual-service topology and US-094 pairing

Operator deploy documentation for the Ubuntu worker SHALL briefly describe the dual-service topology (worker API on `8010`, operator UI on the chosen UI port), state that browsers use the separated UI while n8n continues to call the worker HTTP API only, and SHALL describe US-094 UAT/prod UI↔API pairing (env var names, closed `uat`/`prod` vocabulary, and default overlays).

After US-096, documentation MUST state that the supported operator console path is exclusively the separated UI service and MUST NOT present worker-embedded `GET /flow-a/console/linkedin-variant-supervision` (or equivalent) as a supported or compatibility production path. Documentation MUST note that former worker console URLs fail closed with a clear operator-visible outcome.

When US-099 is active, documentation MUST describe Cloudflare Tunnel (or equivalent) front-only public UI exposure, private worker API, and private UI→API hop at a topology level without embedding secrets or tunnel tokens. Documentation MUST NOT claim full BL-029 CI/UAT stand-up is complete merely because pairing defaults, validation, or public UI topology exist. Documentation MUST NOT claim Story accepted solely from docs updates.

#### Scenario: Deploy guide mentions both services and pairing

- **WHEN** an operator reads the updated ubuntu-server worker deployment guide after US-096
- **THEN** the guide identifies how to reach the separated operator UI and the worker API as distinct LAN endpoints, reiterates ADR-0001 (n8n → worker HTTP only), documents UAT/prod pairing configuration by env var name, and does not present the embedded worker console as a supported or compatibility production path

#### Scenario: Deploy guide notes decommissioned worker console URLs

- **WHEN** an operator reads the updated ubuntu-server worker deployment guide after US-096
- **THEN** the guide states that former worker console URLs fail closed and that operators should use the separated UI port (default `8011`)

#### Scenario: Deploy guide describes US-099 front-only topology when in scope

- **WHEN** an operator reads the ubuntu-server worker deployment guide after US-099 docs updates
- **THEN** the guide describes UI-only public ingress via Cloudflare Tunnel (or equivalent), private API, and private UI→API hop without printing secrets or claiming the worker API is internet-public
