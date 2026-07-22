# operator-ui-deployment

## Purpose

Packaging, configuration, and LAN deployment of Silverman Authority Manager as a deployable UI artifact/service distinct from the FastAPI worker API (BL-034 / US-093 + US-094 + US-095). Covers absolute worker API base URL configuration, fail-closed misconfig behavior, worker CORS allowlist for UI origins, UAT/prod UI↔API environment pairing (env label + health agreement), focused capability-regression evidence for the separated production path, ADR-0001 n8n→worker HTTP-only preservation, and topology documentation pointers.

## Requirements

### Requirement: Separated operator UI is a distinct deployable artifact

The system SHALL provide a deployable operator UI artifact or service for Silverman Authority Manager that is distinct from the FastAPI worker API process. After US-096, the supported production path for the operator console MUST be exclusively that separated UI artifact/service; worker-embedded static delivery MUST NOT remain a supported or compatibility production path.

The separated UI artifact MUST be produced from the existing React + TypeScript + Vite console package (`frontend/linkedin-variant-supervision-console/` or its successor path) rather than a greenfield UI rewrite.

The separated UI MUST serve only static client assets (HTML/JS/CSS and non-secret runtime config). It MUST NOT mount the editorial filesystem as a browser source of truth and MUST NOT perform LinkedIn publication, Flow A/B pipeline work, or n8n orchestration inside the UI process.

#### Scenario: Distinct UI service exists beside the worker

- **WHEN** an operator inspects the US-093/US-096 deployment artifacts for the operator console
- **THEN** a UI image or equivalent service definition exists that can be built and started independently of rebuilding the worker API image as the only delivery mechanism

#### Scenario: UI process does not own editorial SoT

- **WHEN** the separated operator UI container or service is running
- **THEN** it does not treat host editorial mounts as the browser source of truth and does not replace worker HTTP contracts for supervision or publication

#### Scenario: Worker embed is not a supported production path

- **WHEN** an operator reviews production deployment guidance after US-096
- **THEN** the guidance does not present worker-embedded console static files as a supported or compatibility production path

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

### Requirement: Worker allows browser calls from configured UI origins

The worker API SHALL support an explicit allowlist of operator UI origins (environment configuration) so browsers running the separated UI can call authenticated worker HTTP routes cross-origin. When the allowlist is empty or unset, the worker MUST NOT open a wildcard CORS policy for arbitrary origins.

Docs and env examples MUST document the allowlist variable by name and MUST NOT print real secret values.

#### Scenario: Allowlisted UI origin can call the worker

- **WHEN** `SILVERMAN_OPERATOR_UI_ORIGINS` (or equivalent) includes the separated UI origin and a browser on that origin calls an authenticated worker route with valid credentials
- **THEN** the browser CORS preflight/response policy permits the call according to the allowlist

#### Scenario: Empty allowlist does not wildcard CORS

- **WHEN** the UI origin allowlist is empty or unset
- **THEN** the worker does not advertise Access-Control-Allow-Origin for arbitrary foreign origins

### Requirement: n8n orchestration remains worker HTTP only after UI separation

UI separation MUST NOT introduce n8n Execute Command nodes or n8n direct filesystem orchestration for Flow A/B or LinkedIn publication. n8n MUST continue to call the worker API over HTTP only (ADR-0001). The separated UI MUST NOT become an n8n execution target for pipeline work.

#### Scenario: n8n still targets the worker API

- **WHEN** an operator reviews Flow A/B n8n workflow exports after US-093
- **THEN** orchestration nodes that reach silverman-blog-linkedin continue to use HTTP Request (or equivalent HTTP) against the worker base URL and do not add Execute Command for worker file I/O

### Requirement: Topology documentation for separated UI

Operator-facing deployment documentation and CURRENT-STATE topology pointers SHALL briefly describe the separated UI service alongside the worker API (including the intended LAN ports or equivalent), state that the worker remains the HTTP API source of truth and is API-only for operator console purposes after US-096, and state that the UI is a client only.

Documentation SHALL describe UAT vs prod UI↔API pairing (env var names and default overlays) per US-094. Documentation MUST NOT present the embedded worker console as a supported or compatibility production path. Documentation MUST NOT claim public console exposure beyond BL-026 accepted exposure and MUST NOT claim full BL-029 CI/UAT stand-up is complete merely because pairing defaults exist.

RUNTIME-STATE SHALL be updated when live deployment flags or topology for pairing or console delivery change on a running stack.

#### Scenario: CURRENT-STATE points to UI + API topology

- **WHEN** an operator reads CURRENT-STATE runtime topology after US-096 docs updates
- **THEN** the document (or a linked operator deploy doc) identifies the worker API endpoint and the separated operator UI endpoint as distinct services, describes UAT/prod pairing configuration by env var name, and does not list worker-embedded console serving as a supported or compatibility production path

#### Scenario: RUNTIME-STATE updated when live topology changes

- **WHEN** an operator applies US-096 decommission (or pairing) configuration on a live deployed stack
- **THEN** RUNTIME-STATE (or the linked live-ops note) records the non-secret topology in effect without secret values

### Requirement: Worker API has no operator UI surface after hard independence

After BL-034 / US-096, the worker API image and process MUST NOT ship operator-console static assets and MUST NOT serve the former embedded console routes (including `GET /flow-a/console/linkedin-variant-supervision` and its asset paths) as a UI surface.

The worker build/deploy path MUST NOT require embedding the SPA (`build:embedded`, copying console assets into `src/.../static/`, or equivalent). API builds MUST succeed without a frontend production build step.

#### Scenario: API image has no console SPA surface

- **WHEN** an operator inspects the worker API image or running process after US-096
- **THEN** it does not ship or serve the operator-console SPA as an embedded UI

#### Scenario: API build without frontend prod embed

- **WHEN** an operator builds the worker API without running a frontend production embed step
- **THEN** the API build succeeds

### Requirement: Operator UI remains HTTP-only client of the worker

The operator UI artifact MUST remain a distinct project/service that consumes the worker only via configured HTTP (`SILVERMAN_OPERATOR_UI_API_BASE_URL` plus US-094 pairing as applicable).

The UI MUST NOT embed worker Python, editorial/data mounts as browser source of truth, API business logic, or secret material belonging to the API.

#### Scenario: UI consumes worker only over configured HTTP

- **WHEN** the separated operator UI runs in supported production mode
- **THEN** it calls the worker through the typed client using the configured absolute API base URL and does not mount editorial data or embed API secrets

### Requirement: Exclusive supported production topology is separated UI to API

The supported production topology for Silverman Authority Manager MUST be exclusively separated UI → worker API over HTTP. n8n MUST continue to call the worker API only (ADR-0001); the UI MUST NOT become an n8n execution target.

Operator-facing docs (CURRENT-STATE, ubuntu deploy guide, and RUNTIME-STATE when live topology notes change) MUST NOT present the embedded worker console as a supported or compatibility production path after US-096.

#### Scenario: Docs drop embedded compatibility as production path

- **WHEN** an operator reads CURRENT-STATE or the ubuntu deploy guide after US-096 docs updates
- **THEN** the documents describe `:8011` (or the documented UI port) as the supported console and do not present worker-embedded console serving as a supported or compatibility production path

#### Scenario: n8n still targets worker only

- **WHEN** an operator reviews Flow A/B n8n workflow exports after US-096
- **THEN** orchestration continues to use HTTP against the worker and does not target the UI or add Execute Command for worker file I/O

### Requirement: Separated production path includes capability-regression evidence

The supported production path for Silverman Authority Manager as a separated UI artifact MUST be backed by focused capability-regression evidence (US-095) showing that schedule visibility, BL-032 control-center reads, at least one representative gated/dry-run mutation, and US-040D auth session gating remain available when the UI calls the worker via the configured absolute `SILVERMAN_OPERATOR_UI_API_BASE_URL` (with pairing labels applied where required).

US-093 packaging (distinct UI artifact, runtime base URL injection, CORS allowlist) and US-094 pairing enforcement remain in force; this requirement does not redesign them. Evidence MAY be automated tests and/or controlled local/LAN smoke and MUST NOT claim public console exposure beyond BL-026.

#### Scenario: Regression evidence required for separated path claim

- **WHEN** docs or checklists claim day-to-day supervision remains available on the separated UI production path after US-095
- **THEN** they cite focused regression evidence covering absolute-base reads, a representative gated/dry-run mutation, auth session gating, and existing config/pairing fail-closed holds

#### Scenario: No relative fallback in separated mode during regression

- **WHEN** separated-UI mode has a valid absolute API base URL under regression
- **THEN** typed client calls continue to use that absolute origin and do not silently fall back to UI same-origin relative API paths

#### Scenario: US-093 packaging not redesigned by US-095

- **WHEN** US-095 regression work is applied
- **THEN** the distinct UI artifact/service model and runtime API base URL injection from US-093 remain the packaging approach (verify hold; no packaging redesign required)

### Requirement: Server env examples document Google OIDC configuration

The repository SHALL document server-local environment variables required for Google (OIDC) operator-console authentication (US-097) in `deploy/server/` env examples (worker and/or UI as applicable).

Examples MUST:

- name configuration keys for Google OAuth client ID, client secret, redirect URI, and any enablement / session-signing keys used by the implementation;
- use non-secret placeholders only;
- state that client secrets and session signing material MUST NOT be embedded in frontend source, rendered HTML, or committed docs;
- state that public Cloudflare Tunnel topology remains US-099 (not activated by documenting Google env vars).

#### Scenario: Env example names Google OIDC keys

- **WHEN** an operator opens the server env example for Google console auth
- **THEN** the example lists the Google OIDC-related configuration keys by name with non-secret placeholders

#### Scenario: Env example does not embed real secrets

- **WHEN** the Google OIDC env example is scanned
- **THEN** it does not contain real Google client secrets, refresh tokens, worker API keys, or session signing secrets

### Requirement: Topology docs distinguish Google identity from public exposure

Operator-facing deployment documentation and CURRENT-STATE topology pointers SHALL briefly state when Google (OIDC) identity/allowlist is activated on the separated LAN UI (`:8011`), without claiming that the console is publicly exposed via Cloudflare Tunnel (US-099) and without claiming US-098 JWT-only console→API cutover.

#### Scenario: CURRENT-STATE records Google identity without public claim

- **WHEN** US-097 docs updates are applied after implementation
- **THEN** CURRENT-STATE (or linked ops doc) records Google identity/allowlist on the separated UI and explicitly does not claim US-099 public front-only topology or Story accepted solely from implementation
