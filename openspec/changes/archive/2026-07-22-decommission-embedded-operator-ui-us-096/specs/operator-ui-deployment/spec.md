## ADDED Requirements

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

## MODIFIED Requirements

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
