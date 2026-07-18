## ADDED Requirements

### Requirement: Console uses an approved modern frontend stack

The Flow A LinkedIn variant supervision console MUST be implemented with the approved modern frontend stack **React + TypeScript + Vite** (or an equivalent stack only if a superseding approved OpenSpec change explicitly replaces this decision).

The stack change MUST be treated as console-layer modernization only. It MUST NOT rewrite worker business logic, n8n workflows, Python utilities beyond static-asset serving, file contracts, publication guards, or existing US-017 HTTP mutation semantics as part of US-040A.

#### Scenario: Stack identity is React TypeScript Vite

- **WHEN** an implementer inspects the supervision console frontend package for US-040A
- **THEN** the package is a React + TypeScript application built with Vite (or documents an approved equivalent replacement change)

#### Scenario: Worker mutation contracts remain unchanged by stack migration

- **WHEN** the modernized console performs edit, defer, or cancel
- **THEN** those actions call the existing authenticated US-017 endpoints without introducing a parallel mutation source of truth

### Requirement: Console is delivered as static build artifacts from the worker

The modernized console MUST produce static build artifacts (`index.html` and associated assets) that the existing worker serves in production.

Production deployment MUST NOT require a separate frontend application server process for the supervision console.

The worker MUST continue to expose the operator console at `GET /flow-a/console/linkedin-variant-supervision`, or MUST provide a documented compatible replacement route that preserves understandable operator access during migration.

#### Scenario: Console route serves built SPA shell

- **WHEN** an operator requests `GET /flow-a/console/linkedin-variant-supervision` (or the documented compatible replacement)
- **THEN** the worker returns the Vite-built console shell HTML that loads same-origin static assets and consumes worker HTTP APIs

#### Scenario: No separate frontend server required

- **WHEN** the worker is deployed with the US-040A console assets included
- **THEN** the console is reachable through the worker HTTP process alone without a second production frontend server

### Requirement: List-oriented pending supervision remains a first-class view

The modernized console MUST preserve the existing list-oriented pending-variant supervision experience as a first-class view, including presentation of pending rows and operator edit, defer, and cancel actions via existing US-017 POSTs with dry-run default and confirmation for real cancel.

The list view MUST NOT be removed, permanently hidden, or degraded to a secondary-only surface by the introduction of calendar scaffolding.

#### Scenario: List view remains primary operational surface

- **WHEN** an operator opens the modernized supervision console
- **THEN** a list-oriented pending-variant supervision view is available as a first-class view and supports the Stories 1–3 supervision actions already delivered

#### Scenario: Calendar scaffold does not replace list

- **WHEN** month calendar view scaffolding is present in the console
- **THEN** the list view remains reachable and continues to present pending supervision rows without requiring calendar interaction

### Requirement: Console UI is componentized with operational screen scaffolding

The modernized console MUST structure the UI as componentized operational screens and MUST include scaffolding (implemented shells and clear extension boundaries) for at least:

- list view
- month calendar view
- item detail
- schedule editor
- status summary
- filters
- confirmation flows
- shared API and error handling

Full month calendar visibility UX and schedule mutation behavior from the calendar remain out of scope for US-040A and MUST NOT be required for US-040A acceptance beyond scaffolding and shared-model readiness.

#### Scenario: Required scaffolds exist in the frontend package

- **WHEN** the US-040A frontend package is inspected
- **THEN** distinct component (or module) boundaries exist for list, month calendar, item detail, schedule editor, status summary, filters, confirmation flows, and shared API/error handling

#### Scenario: Calendar and schedule scaffolds do not imply US-040B or US-040C complete

- **WHEN** the month calendar or schedule editor scaffold is shown without full US-040B/US-040C behavior
- **THEN** the console does not claim those later stories are complete and does not invent a new calendar mutation source of truth

### Requirement: Browser API access uses a typed client with injectable auth

All browser calls to worker supervision APIs MUST go through a typed API client (or equivalent centralized boundary).

The client MUST centralize request construction, response typing, and error mapping for at least:

- `GET /flow-a/linkedin-variants/pending-supervision`
- `POST /correct-linkedin-variant`
- `POST /defer-linkedin-variant`
- `POST /cancel-linkedin-publication`

Auth credentials MUST be injectable at the API-client boundary (for example via a headers provider) so a future Google/OIDC bearer token or secure session cookie (US-040D) can replace the current API-key header mechanism without changing list or calendar business components.

Frontend source, rendered HTML, logs, and browser storage MUST NOT embed API keys, bearer tokens, OAuth tokens, operational secrets, or secret-like placeholders.

#### Scenario: Business components do not call fetch directly for worker APIs

- **WHEN** list or calendar components load pending supervision data or submit edit/defer/cancel
- **THEN** those components use the typed API client rather than ad-hoc `fetch`/`XMLHttpRequest` calls scattered across view code

#### Scenario: Auth provider can be swapped without editing list components

- **WHEN** the auth header provider implementation is replaced at the API-client boundary
- **THEN** list and calendar business components do not require changes to continue calling the same client methods

#### Scenario: Secrets are absent from frontend artifacts

- **WHEN** frontend source and built console assets are scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present

### Requirement: List and calendar share one normalized frontend model

List view and month calendar view MUST be backed by the same worker read models or by one shared normalized frontend model derived from those read models so the views cannot disagree about item identity, state, schedule, or available actions.

US-040A MUST implement the shared model and wire the list view to it. The calendar scaffold MUST consume the same model (even if calendar presentation remains placeholder-level).

#### Scenario: Shared model identity is stable across views

- **WHEN** a pending variant exists in the normalized frontend model
- **THEN** list and calendar scaffolds that render that item use the same campaign id, variant id, schedule, and action availability derived from that model

#### Scenario: List refresh updates the shared model

- **WHEN** pending-supervision data is refreshed after a successful real mutation
- **THEN** the shared model updates and list presentation reflects the new state without a separate divergent calendar cache

### Requirement: Frontend validation covers build and key UX contracts

US-040A MUST include frontend validation appropriate to the React + TypeScript + Vite stack covering at least:

- production build success
- key component behavior for the list-oriented supervision experience
- API error mapping for auth/validation and known supervision failure codes
- desktop viewport usability of the list-oriented console
- mobile viewport usability of the list-oriented console

#### Scenario: Production build succeeds

- **WHEN** the frontend production build command is run for the supervision console
- **THEN** the build completes successfully and emits static artifacts consumable by the worker

#### Scenario: API error mapping is tested

- **WHEN** the typed client receives unauthorized or known US-017 supervision failure responses
- **THEN** automated tests assert those responses map to clear operator-facing error states without silent success

#### Scenario: Desktop and mobile viewports are covered

- **WHEN** frontend validation for US-040A runs
- **THEN** evidence covers both a desktop-width and a mobile-width presentation of the list-oriented console

### Requirement: US-040A scope preserves Stories 1–3 and defers later variants

US-040A MUST NOT mark BL-015 closed or US-040A Story accepted by implementation alone.

US-040A MUST NOT implement US-040B full calendar UX, US-040C calendar schedule mutation / new calendar mutation SoT, US-040D public URL and Google auth activation, or US-040E polish beyond stack-migration needs.

US-040A MUST NOT introduce a backend-for-frontend, database, user-management system, or public hosting change.

US-040A MUST NOT call the LinkedIn publication API, bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, use n8n Execute Command, or read raw mount paths from the browser.

#### Scenario: Later variants remain out of scope

- **WHEN** US-040A implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040B–US-040E as not implemented (except scaffolding/readiness boundaries delivered by US-040A)

#### Scenario: No BFF or public hosting introduced

- **WHEN** US-040A lands
- **THEN** the architecture still uses browser → worker HTTP for console data and mutations without a new BFF, database, or public hosting topology

## MODIFIED Requirements

### Requirement: Worker HTTP is the source of truth for console data

The supervision console MUST obtain pending-variant, calendar-alignment, and blocked-state display data through authenticated worker HTTP. The browser or operator UI MUST NOT treat raw mount file paths as the source of truth.

The worker MUST expose the thin authenticated read-only aggregation endpoint `GET /flow-a/linkedin-variants/pending-supervision` that returns the required per-variant fields without mutating campaign metadata, calendar files, or LinkedIn publication state.

The worker MUST serve the operator console at `GET /flow-a/console/linkedin-variant-supervision` as static build artifacts produced by the approved frontend toolchain (React + TypeScript + Vite), or MUST serve a documented compatible replacement route that preserves understandable operator access. The console MAY be an SPA shell plus hashed static assets; it MUST NOT require a separate production frontend server.

The pending-supervision GET MUST NOT call LinkedIn, DeepSeek, ComfyUI, or Git, and MUST NOT invoke US-017 mutation routes (`POST /correct-linkedin-variant`, `POST /defer-linkedin-variant`, `POST /cancel-linkedin-publication`) on the server.

The console page MAY call authenticated US-017 mutation routes for edit, defer, and cancel (US-039 + US-040).

#### Scenario: Authenticated read returns pending rows

- **WHEN** an authenticated client requests `GET /flow-a/linkedin-variants/pending-supervision` while pending variants exist
- **THEN** the response includes the required per-variant fields and performs no campaign or calendar file mutation

#### Scenario: Unauthenticated read is rejected

- **WHEN** a client requests `GET /flow-a/linkedin-variants/pending-supervision` without a valid API key
- **THEN** the worker rejects the request with the existing unauthorized semantics and does not return variant payloads

#### Scenario: Read path does not mutate

- **WHEN** `GET /flow-a/linkedin-variants/pending-supervision` is called repeatedly against the same editorial base
- **THEN** campaign metadata and calendar files remain byte-identical aside from unrelated concurrent operators

#### Scenario: Console page is served at the fixed path

- **WHEN** an operator requests `GET /flow-a/console/linkedin-variant-supervision`
- **THEN** the worker returns the built static console (SPA shell and associated assets) that consumes the pending-supervision read API and MAY offer edit, defer, and cancel actions that call existing US-017 POSTs

### Requirement: Static console HTML MUST NOT embed secrets or secret-like placeholders

Frontend source for the supervision console and the built static assets served for `GET /flow-a/console/linkedin-variant-supervision` (including `index.html` and bundled JavaScript/CSS) MUST NOT contain API keys, bearer tokens, OAuth tokens, or placeholders that look like real secrets (including but not limited to `CHANGE_ME`, `sk-` prefixed samples, `Bearer ` token samples, or hardcoded `X-API-Key` values).

Operators MUST supply credentials at runtime through the typed API-client auth boundary (browser prompt or local-only in-memory configuration). Credentials MUST NOT be persisted in browser storage as part of US-040A. Documentation examples MUST use clearly non-secret wording (for example “your API key”) without embedding fake credential strings that resemble production secrets.

#### Scenario: Static HTML secrets audit passes

- **WHEN** the committed or built console assets served for the supervision console route are scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in those assets

#### Scenario: Frontend source secrets audit passes

- **WHEN** the React + TypeScript frontend source for the supervision console is scanned for API keys, bearer tokens, and secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present in the source
