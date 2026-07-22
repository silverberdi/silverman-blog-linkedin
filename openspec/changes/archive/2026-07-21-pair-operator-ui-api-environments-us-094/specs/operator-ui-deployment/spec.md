## MODIFIED Requirements

### Requirement: Operator UI is configured with an absolute worker API base URL

The separated operator UI SHALL resolve the worker API base URL from deploy-time configuration (runtime-injected non-secret config preferred). The configured value MUST be an absolute `http` or `https` origin suitable for prefixing existing worker route paths.

Configuration examples and docs MUST use non-secret placeholders only (for example `http://192.168.0.194:8010`) and MUST NOT embed API keys, bearer tokens, or secret-like placeholders.

In separated-UI mode the UI MUST also resolve a required non-secret environment label from `SILVERMAN_OPERATOR_UI_ENV_LABEL` with closed values `uat` or `prod`, and MUST enforce UI↔API environment pairing per capability `operator-ui-api-environment-pairing`. US-093 packaging and base-URL injection remain in force; the former “reserved label / pairing not done” outcome is superseded by US-094.

#### Scenario: Configured base URL is used for API calls

- **WHEN** the separated UI is started with a valid absolute `SILVERMAN_OPERATOR_UI_API_BASE_URL` (or equivalent documented config key)
- **THEN** the typed API client prefixes worker route paths with that base URL for browser HTTP calls

#### Scenario: Environment label is required for separated-UI pairing

- **WHEN** the separated UI runs in supported production mode
- **THEN** `SILVERMAN_OPERATOR_UI_ENV_LABEL` MUST be present as `uat` or `prod` and pairing validation against the worker MUST be applied before authenticated supervision or mutation traffic

### Requirement: Missing or invalid UI API configuration fails closed

When the operator console runs in separated-UI mode, the UI MUST fail closed if the worker API base URL configuration is missing, empty, or not a valid absolute `http`/`https` URL. The operator MUST see a clear blocked or configuration-error state that names the required configuration key(s) without revealing secret values.

In that blocked state the UI MUST NOT silently fall back to same-origin relative API calls that would target the UI static server instead of the worker API.

The UI MUST likewise fail closed for missing/invalid environment label or failed UI↔API environment pairing (see `operator-ui-api-environment-pairing`), without silent cross-environment writes.

#### Scenario: Missing API base URL blocks the console

- **WHEN** an operator opens the separated UI and the API base URL config is missing or empty
- **THEN** the UI presents a clear blocked/configuration error and does not load supervision data via relative same-origin API paths

#### Scenario: Invalid API base URL blocks the console

- **WHEN** the configured API base URL is not a valid absolute `http` or `https` URL
- **THEN** the UI presents a clear blocked/configuration error and does not proceed with worker API calls

#### Scenario: Environment pairing failure blocks the console

- **WHEN** separated-UI environment label and API `deployment_environment` disagree or pairing identity cannot be read
- **THEN** the UI presents a clear blocked/pairing error and does not issue authenticated supervision or mutation requests

### Requirement: Topology documentation for separated UI

Operator-facing deployment documentation and CURRENT-STATE topology pointers SHALL briefly describe the separated UI service alongside the worker API (including the intended LAN ports or equivalent), state that the worker remains the HTTP API source of truth, and state that the UI is a client only.

Documentation SHALL describe UAT vs prod UI↔API pairing (env var names and default overlays) per US-094. Documentation MUST NOT claim public console exposure beyond BL-026 accepted exposure and MUST NOT claim full BL-029 CI/UAT stand-up is complete merely because pairing defaults exist.

RUNTIME-STATE SHALL be updated when live deployment flags or topology for pairing change on a running stack.

#### Scenario: CURRENT-STATE points to UI + API topology

- **WHEN** an operator reads CURRENT-STATE runtime topology after US-094 docs updates
- **THEN** the document (or a linked operator deploy doc) identifies both the worker API endpoint and the separated operator UI endpoint as distinct services and describes UAT/prod pairing configuration by env var name

#### Scenario: RUNTIME-STATE updated when pairing goes live

- **WHEN** an operator applies pairing configuration on a live deployed stack
- **THEN** RUNTIME-STATE (or the linked live-ops note) records the non-secret environment identity in effect without secret values
