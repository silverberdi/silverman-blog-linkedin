## MODIFIED Requirements

### Requirement: Worker HTTP is the source of truth for console data

The supervision console MUST obtain pending-variant, calendar-alignment, and blocked-state display data through authenticated worker HTTP. The browser or operator UI MUST NOT treat raw mount file paths as the source of truth.

The worker MUST expose the thin authenticated read-only aggregation endpoint `GET /flow-a/linkedin-variants/pending-supervision` that returns the required per-variant fields without mutating campaign metadata, calendar files, or LinkedIn publication state.

The system MUST provide a supported production path that serves the operator console as a deployable UI artifact or service distinct from the FastAPI worker API process (BL-034 / US-093). The console MAY continue to be reachable at `GET /flow-a/console/linkedin-variant-supervision` as an optional compatibility path served by the worker, or via a documented compatible replacement / redirect that preserves understandable operator access. Same-origin static delivery inside the worker image MUST NOT be the only supported production path.

The pending-supervision GET MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git, and MUST NOT invoke US-017 mutation routes (`POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`) on the server.

The console page MAY call authenticated US-017 mutation routes for edit, defer, and cancel (US-039 + US-040).

When the console runs as the separated UI, browser calls MUST use the typed API client with a configured absolute worker API base URL. The client MUST NOT introduce a filesystem source of truth in the browser.

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

#### Scenario: Compatibility console path remains understandable when retained

- **WHEN** the deployment retains `GET /flow-a/console/linkedin-variant-supervision` (or a documented compatible replacement)
- **THEN** an operator can still open an understandable console entry URL without inspecting raw mount files

### Requirement: Console is delivered as static build artifacts from the worker

The modernized console MUST produce static build artifacts (`index.html` and associated assets) from the approved React + TypeScript + Vite toolchain.

For BL-034 / US-093, the supported production delivery path MUST include serving those artifacts from a deployable UI artifact or service that is distinct from the FastAPI worker API process. Production deployment of the operator console MUST NOT require that the only supported path is embedding and serving those assets solely from the worker HTTP process.

The worker MAY continue to expose the operator console at `GET /flow-a/console/linkedin-variant-supervision`, or provide a documented compatible replacement or redirect, as an optional compatibility path during migration. Compatibility retention MUST NOT be documented as the only supported production path after US-093.

#### Scenario: Separated UI serves the Vite-built SPA shell

- **WHEN** an operator opens the separated operator UI service URL
- **THEN** the UI returns the Vite-built console shell HTML that loads its static assets and consumes worker HTTP APIs through the typed client

#### Scenario: Worker-embedded console is not the only supported path

- **WHEN** an operator reviews US-093 production deployment guidance
- **THEN** the guidance documents a UI artifact/service distinct from the worker API as a supported production path and does not state that worker-embedded static files are the only supported production path

## ADDED Requirements

### Requirement: Typed client supports configurable worker API base URL

The supervision console typed HTTP client (`SupervisionApiClient` or equivalent boundary) MUST accept a configurable absolute worker API base URL for separated-UI deployments and MUST join that base URL with existing root-relative worker route paths for all console reads and mutations.

Same-origin relative requests remain acceptable only for an explicitly retained worker-embedded compatibility mode. Separated-UI mode MUST NOT silently use relative paths when the API base URL is missing or invalid (fail closed per operator-ui-deployment).

Business screen components MUST continue to call the worker only through this typed client boundary so future Google/OIDC auth (BL-035) can replace the auth provider without rewriting business screens.

#### Scenario: Client prefixes routes with configured base URL

- **WHEN** the typed client is constructed with API base URL `http://192.168.0.194:8010` and requests schedule visibility
- **THEN** the browser HTTP call targets that worker origin with the existing schedule-visibility path and does not treat the UI origin as the API host

#### Scenario: Business screens stay behind the typed client

- **WHEN** a console business screen performs a supervision read or mutation after US-093
- **THEN** the call goes through the typed client boundary rather than ad-hoc fetch URLs or filesystem access

### Requirement: Separated console surfaces configuration and API blocked states

When the separated operator UI cannot proceed because API base URL configuration is missing/invalid, or because worker HTTP calls fail due to network/CORS/unauthorized conditions already modeled by the client error vocabulary, the console MUST communicate a clear operator-visible blocked or error state. Messages MUST NOT include API keys, bearer tokens, or other secrets.

#### Scenario: Configuration block is operator-visible

- **WHEN** separated-UI API base URL configuration is missing or invalid
- **THEN** the operator sees a clear blocked/configuration message naming the required config key(s) without secret values

#### Scenario: Unauthorized API call remains understandable

- **WHEN** the separated UI calls the worker without valid credentials
- **THEN** the console presents the existing unauthorized / sign-in blocked semantics without exposing secrets
