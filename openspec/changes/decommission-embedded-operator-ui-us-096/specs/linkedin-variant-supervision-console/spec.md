## MODIFIED Requirements

### Requirement: Worker HTTP is the source of truth for console data

The supervision console MUST obtain pending-variant, calendar-alignment, and blocked-state display data through authenticated worker HTTP. The browser or operator UI MUST NOT treat raw mount file paths as the source of truth.

The worker MUST expose the thin authenticated read-only aggregation endpoint `GET /flow-a/linkedin-variants/pending-supervision` that returns the required per-variant fields without mutating campaign metadata, calendar files, or LinkedIn publication state.

The system MUST provide the operator console exclusively as a deployable UI artifact or service distinct from the FastAPI worker API process (BL-034 / US-093 + US-096). The worker API MUST NOT serve the former embedded console SPA at `GET /flow-a/console/linkedin-variant-supervision` (or its asset paths) as a supported or compatibility production path. Requests to those former console URLs MUST fail closed with a clear operator-visible decommission outcome (not a silent partial UI).

The pending-supervision GET MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git, and MUST NOT invoke US-017 mutation routes (`POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`) on the server.

The console page MAY call authenticated US-017 mutation routes for edit, defer, and cancel (US-039 + US-040).

Browser calls from the operator UI MUST use the typed API client with a configured absolute worker API base URL. The client MUST NOT introduce a filesystem source of truth in the browser.

#### Scenario: Authenticated read returns pending rows

- **WHEN** an authenticated client requests `GET /flow-a/linkedin-variants/pending-supervision` while pending variants exist
- **THEN** the response includes the required per-variant fields and performs no campaign or calendar file mutation

#### Scenario: Unauthenticated read is rejected

- **WHEN** a client requests `GET /flow-a/linkedin-variants/pending-supervision` without a valid API key
- **THEN** the worker rejects the request with the existing unauthorized semantics and does not return variant payloads

#### Scenario: Read path does not mutate

- **WHEN** `GET /flow-a/linkedin-variants/pending-supervision` is called repeatedly against the same editorial base
- **THEN** campaign metadata and calendar files remain byte-identical aside from unrelated concurrent operators

#### Scenario: Separated UI consumes pending-supervision over HTTP

- **WHEN** an operator uses the separated operator UI configured with a valid worker API base URL
- **THEN** the console loads pending-supervision (and related console data) through authenticated worker HTTP via the typed client and does not read editorial mounts from the browser

#### Scenario: Former embedded console URL fails closed

- **WHEN** a client requests `GET /flow-a/console/linkedin-variant-supervision` (or a former console asset path under that prefix) on the worker API
- **THEN** the worker does not return the Vite SPA shell or console static assets and instead returns a clear operator-visible decommission outcome

### Requirement: Static console HTML MUST NOT embed secrets or secret-like placeholders

Frontend source for the supervision console and the built static assets of the separated operator UI artifact (including `index.html` and bundled JavaScript/CSS) MUST NOT contain API keys, bearer tokens, OAuth tokens, or placeholders that look like real secrets (including but not limited to `CHANGE_ME`, `sk-` prefixed samples, `Bearer ` token samples, or hardcoded `X-API-Key` values).

Operators MUST supply credentials at runtime through the typed API-client auth boundary (browser prompt or local-only in-memory configuration). Credentials MUST NOT be persisted in browser storage as part of US-040A. Documentation examples MUST use clearly non-secret wording (for example “your API key”) without embedding fake credential strings that resemble production secrets.

#### Scenario: Separated UI built assets secrets audit passes

- **WHEN** the committed frontend source or built separated-UI console assets are scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in those assets

#### Scenario: Frontend source secrets audit passes

- **WHEN** the React + TypeScript frontend source for the supervision console is scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in the source

### Requirement: Console is delivered as static build artifacts from the worker

The modernized console MUST produce static build artifacts (`index.html` and associated assets) from the approved React + TypeScript + Vite toolchain.

For BL-034 / US-096, those artifacts MUST be served exclusively from the separated operator UI artifact or service (distinct from the FastAPI worker API process). The worker API image/process MUST NOT ship operator-console static assets and MUST NOT require embedding the SPA (`build:embedded`, copying console assets into `src/.../static/`, or equivalent) for a successful API build.

#### Scenario: Separated UI serves the Vite-built SPA shell

- **WHEN** an operator opens the separated operator UI service URL
- **THEN** the UI returns the Vite-built console shell HTML that loads its static assets and consumes worker HTTP APIs through the typed client

#### Scenario: Worker API build does not require frontend embed

- **WHEN** an operator builds the worker API image or package after US-096
- **THEN** the build succeeds without a frontend production embed step and without copying console SPA assets into the worker package static tree

#### Scenario: Worker does not ship console static assets

- **WHEN** an operator inspects the worker API image or installed package after US-096
- **THEN** operator-console SPA assets for the former embedded path are not present as a served or shipped UI surface

### Requirement: Typed client supports configurable worker API base URL

The supervision console typed HTTP client (`SupervisionApiClient` or equivalent boundary) MUST accept a configurable absolute worker API base URL for the separated operator UI and MUST join that base URL with existing root-relative worker route paths for all console reads and mutations.

Separated-UI mode MUST NOT silently use relative paths when the API base URL is missing or invalid (fail closed per operator-ui-deployment). Worker-embedded same-origin relative API mode MUST NOT remain a supported production delivery mode after US-096.

Business screen components MUST continue to call the worker only through this typed client boundary so future Google/OIDC auth (BL-035) can replace the auth provider without rewriting business screens.

#### Scenario: Client prefixes routes with configured base URL

- **WHEN** the typed client is constructed with API base URL `http://192.168.0.194:8010` and requests schedule visibility
- **THEN** the browser HTTP call targets that worker origin with the existing schedule-visibility path and does not treat the UI origin as the API host

#### Scenario: Business screens stay behind the typed client

- **WHEN** a console business screen performs a supervision read or mutation after US-096
- **THEN** the call goes through the typed client boundary rather than ad-hoc fetch URLs or filesystem access

### Requirement: Separated console shows environment identity and pairing blocks

When the console runs as the separated operator UI, it MUST display the active paired environment (`uat` or `prod`) after successful UI↔API environment pairing.

When environment label configuration is missing/invalid or UI↔API pairing fails (including mismatched or unreadable API `deployment_environment`), the console MUST show a clear operator-visible blocked state and MUST NOT proceed with authenticated supervision reads or mutations. Messages MUST name relevant configuration keys without including API keys, bearer tokens, or other secrets.

There is no supported embedded worker-console mode that skips pairing after US-096.

#### Scenario: Paired console shows environment badge

- **WHEN** the separated UI successfully pairs with the worker API
- **THEN** the operator can see the active environment identity (`uat` or `prod`) in the console chrome or equivalent visible surface

#### Scenario: Pairing mismatch blocks authenticated use

- **WHEN** the separated UI env label does not match the API `deployment_environment`
- **THEN** the console shows a blocked/pairing error and does not call authenticated supervision or mutation endpoints

### Requirement: Same-origin default and documented CORS readiness

Browser calls from the supervision console to worker APIs MUST use the typed client with a configured absolute worker API base URL on the supported separated UI path (BL-034 / US-096). Worker-served same-origin relative console delivery MUST NOT remain the default or supported production path.

Cross-origin browser calls from the separated UI origin to the worker MUST continue to rely on the documented worker CORS allowlist (`SILVERMAN_OPERATOR_UI_ORIGINS` or equivalent). US-040D MUST NOT enable permissive public CORS as part of auth readiness; public exposure remains a separate security change (BL-026 / BL-035).

#### Scenario: Separated console API calls use absolute worker base URL

- **WHEN** the built separated console calls pending-supervision, schedule-visibility, or mutation endpoints with a valid absolute API base URL
- **THEN** those calls target that worker origin and do not assume the UI origin is the API host

#### Scenario: Public CORS activation is not implied by readiness

- **WHEN** US-040D auth readiness is implemented
- **THEN** documentation states that any cross-origin CORS policy for public exposure requires a separate security change and is not activated by this slice

## ADDED Requirements

### Requirement: Former embedded console routes fail closed with operator-visible messaging

After US-096, the worker MUST NOT return the operator-console SPA shell or its hashed static assets for former embedded console URLs, including `GET /flow-a/console/linkedin-variant-supervision` and asset paths under that prefix.

The worker MUST respond with a clear operator-visible decommission outcome (HTML and/or structured error body) that does not include secrets and that directs operators to the supported separated operator UI on the LAN UI port (default `8011`) without inventing public internet hosting.

#### Scenario: Console index path is decommissioned

- **WHEN** a client requests `GET /flow-a/console/linkedin-variant-supervision` on the worker API after US-096
- **THEN** the response is not the Vite console `index.html` SPA and clearly communicates that the embedded console is decommissioned

#### Scenario: Former console asset path is decommissioned

- **WHEN** a client requests a former path under `/flow-a/console/linkedin-variant-supervision/assets/` on the worker API after US-096
- **THEN** the worker does not serve console JavaScript/CSS assets and returns a clear fail-closed outcome
