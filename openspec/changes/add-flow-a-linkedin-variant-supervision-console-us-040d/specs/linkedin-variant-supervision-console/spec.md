## MODIFIED Requirements

### Requirement: Browser API access uses a typed client with injectable auth

All browser calls to worker supervision APIs MUST go through a typed API client (or equivalent centralized boundary).

The client MUST centralize request construction, response typing, and error mapping for at least:

- `GET /flow-a/linkedin-variants/pending-supervision`
- `GET /flow-a/schedule-visibility`
- `POST /correct-linkedin-variant`
- `POST /defer-linkedin-variant`
- `POST /cancel-linkedin-publication`
- `POST /editorial-calendar/update-item-schedule`

Auth credentials MUST be injectable at the API-client boundary (for example via an `AuthProvider` headers/credentials provider) so a later Google/OIDC bearer token or secure session cookie can replace the current worker API-key header mechanism without changing list, month calendar, or schedule-editor business components.

The auth/client boundary MUST expose operator session and capability signals sufficient for UI gating, including at least whether a credential is held and whether mutations are allowed (`canMutate`), without requiring calendar components to parse raw HTTP status codes for auth policy.

Frontend source, rendered HTML, logs, and browser storage MUST NOT embed API keys, bearer tokens, OAuth tokens, operational secrets, mount paths, LAN-only host assumptions, or secret-like placeholders.

Until a separate approved security change activates public URL hosting and Google/OIDC authentication, local operations MAY continue to use the existing worker API-key auth mechanism through the same injectable provider.

#### Scenario: Business components do not call fetch directly for worker APIs

- **WHEN** list, calendar, or schedule-editor components load pending supervision or schedule-visibility data or submit edit/defer/cancel/calendar schedule-update
- **THEN** those components use the typed API client rather than ad-hoc `fetch`/`XMLHttpRequest` calls scattered across view code

#### Scenario: Auth provider can be swapped without editing calendar components

- **WHEN** the auth provider implementation is replaced at the API-client boundary with a Google/OIDC bearer or secure session-cookie strategy
- **THEN** list, month calendar, and schedule-editor business components do not require changes to continue calling the same client methods

#### Scenario: Secrets and local-only assumptions are absent from frontend artifacts

- **WHEN** frontend source and built console assets are scanned for API keys, bearer tokens, secret-like placeholders such as `CHANGE_ME`, hardcoded mount paths, or embedded operational secrets
- **THEN** no such values are present

#### Scenario: Local API-key auth still flows through the injectable boundary

- **WHEN** an operator authenticates for local operations using the worker API-key mechanism
- **THEN** credentials are supplied only through the injectable auth provider at runtime and are not hardcoded in source, rendered HTML, or browser storage

## ADDED Requirements

### Requirement: Console represents explicit auth session states

The supervision console MUST represent the following operator-facing session states in the UI, even while the current local implementation uses the existing worker API-key auth mechanism:

- anonymous (no credential held)
- authenticated (credential held and session usable)
- expired-session (prior credential invalidated; re-auth required)
- forbidden (credential present but not authorized)
- service-unavailable (worker/API unreachable or HTTP 5xx)

Session-state presentation MUST be understandable without implying LinkedIn API published, and MUST NOT equate `pending`, `queued`, `cancelled`, `flow_a_complete`, or blog handoff with LinkedIn API published.

#### Scenario: Anonymous state is visible

- **WHEN** the console has no credential held
- **THEN** the UI presents an anonymous/not-authenticated state and does not claim the operator is signed in

#### Scenario: Authenticated state is visible

- **WHEN** a credential is held and the session is usable for worker calls
- **THEN** the UI presents an authenticated state distinct from anonymous and expired-session

#### Scenario: Expired session is visible after unauthorized response

- **WHEN** the typed client receives HTTP 401 and clears the held credential
- **THEN** the UI presents an expired-session state with guidance to re-authenticate

#### Scenario: Forbidden state is visible

- **WHEN** the typed client receives HTTP 403
- **THEN** the UI presents a forbidden/not-authorized state distinct from expired-session

#### Scenario: Service unavailable state is visible

- **WHEN** the typed client encounters a network failure or HTTP 5xx response
- **THEN** the UI presents a service-unavailable state and does not claim the request succeeded

### Requirement: Unauthenticated and read-only sessions cannot mutate schedules

The console MUST prevent unauthenticated sessions and read-only sessions (`canMutate` false) from executing schedule mutations, including:

- LinkedIn variant edit (`POST /correct-linkedin-variant`)
- LinkedIn variant defer/reschedule (`POST /defer-linkedin-variant`)
- LinkedIn variant cancel (`POST /cancel-linkedin-publication`)
- Editorial calendar schedule update (`POST /editorial-calendar/update-item-schedule`)

Mutation commit controls MUST be disabled or otherwise non-executable while `canMutate` is false. The worker remains the authoritative rejector for unauthenticated requests; the UI MUST NOT present a successful mutation when auth is missing or read-only.

#### Scenario: Anonymous session cannot commit schedule mutations

- **WHEN** the session is anonymous
- **THEN** the console does not execute edit/defer/cancel/calendar schedule-update commits and communicates that authentication is required

#### Scenario: Read-only session cannot commit schedule mutations

- **WHEN** the auth provider reports an authenticated but read-only session (`canMutate` false)
- **THEN** the console does not execute schedule mutation commits and communicates that mutation is not allowed

#### Scenario: Authenticated mutable session may attempt mutations via typed client

- **WHEN** the session is authenticated with `canMutate` true
- **THEN** the console may submit schedule mutations through the typed API client subject to existing dry-run and confirmation rules

### Requirement: Mobile session expiry preserves context and unsaved schedule drafts

When a session expires (including on mobile viewports), the console MUST preserve visible list/calendar context and MUST NOT silently discard an unsaved schedule-editor draft.

The console MUST guide the operator back to authentication and, after successful re-auth, MUST allow the operator to resume the preserved schedule draft without forcing a blank editor solely because auth was refreshed.

#### Scenario: Expiry mid-edit keeps schedule draft

- **WHEN** an operator has unsaved schedule-editor fields and the session transitions to expired-session
- **THEN** the unsaved draft remains available in the editor and is not silently cleared by auth expiry alone

#### Scenario: Re-auth guidance after expiry

- **WHEN** the session is expired-session
- **THEN** the UI guides the operator to re-authenticate without claiming mutation success

#### Scenario: Visible context survives expiry

- **WHEN** list or calendar data was already loaded and the session expires
- **THEN** the previously visible context remains on screen (with expired-session messaging) rather than being wiped without explanation

### Requirement: Same-origin default and documented CORS readiness

Browser calls from the supervision console to worker APIs MUST use same-origin relative paths by default while the console is served by the worker.

If a future architecture serves the console from a distinct origin, the project MUST document an explicit CORS allowlist strategy that can be restricted for public exposure (allowed origins, methods, and headers; no wildcard-with-credentials). US-040D MUST NOT enable permissive public CORS as part of readiness.

#### Scenario: Console API calls are same-origin by default

- **WHEN** the built console calls pending-supervision, schedule-visibility, or mutation endpoints
- **THEN** those calls use same-origin relative URLs under the worker host that serves the console

#### Scenario: Public CORS activation is not implied by readiness

- **WHEN** US-040D auth readiness is implemented
- **THEN** documentation states that any cross-origin CORS policy for public exposure requires a separate security change and is not activated by this slice

### Requirement: Public URL and Google authentication activation remain deferred

US-040D MUST document that public deployment (internet exposure of the console URL) and Google/OIDC authentication activation are out of scope for this backlog slice and require a separate approved security OpenSpec change before internet exposure.

US-040D MUST NOT activate public URL hosting, MUST NOT integrate a live Google OAuth/OIDC identity provider, MUST NOT introduce a backend-for-frontend, database, or user-management product, and MUST NOT use n8n Execute Command or browser filesystem writes.

#### Scenario: Activation deferred is recorded

- **WHEN** US-040D implementation is complete
- **THEN** CURRENT-STATE or equivalent operator documentation records that public URL hosting and Google authentication are not activated and require a separate security change before internet exposure

#### Scenario: No live IdP integration in this slice

- **WHEN** an implementer inspects the US-040D change scope
- **THEN** there is no live Google OAuth/OIDC login flow required for local API-key operations through the injectable auth boundary

### Requirement: US-040D scope preserves A–C baselines and defers US-040E

US-040D MUST NOT mark BL-015 closed or US-040D Story accepted by implementation alone.

US-040D MUST preserve the US-040A stack, US-040B list + month schedule visibility baseline, and US-040C shared schedule-editor mutation SoT (US-017 defer for LinkedIn; editorial-calendar schedule-update for blog). It MUST NOT rewrite those baselines except where additive auth-session and capability gating is required.

US-040D MUST NOT implement US-040E polish beyond what auth-readiness UX requires.

US-040D MUST NOT call the LinkedIn publication API, publish blog content, or bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as part of auth-readiness work.

#### Scenario: Later polish remains out of scope

- **WHEN** US-040D implementation is complete
- **THEN** CURRENT-STATE or equivalent status language records US-040E as not implemented (except auth-readiness UX delivered by US-040D) and does not claim BL-015 closed

#### Scenario: Prior console baselines remain first-class

- **WHEN** US-040D auth-readiness surfaces are available
- **THEN** List and Month calendar remain dual first-class views, shared ScheduleEditor remains the schedule mutation surface, and worker HTTP remains the only authz path for console data and mutations

### Requirement: Auth-readiness failures are clearly communicated

Auth and availability failures MUST be clearly communicated to the operator, including at least:

- missing credential / anonymous
- unauthorized / expired-session (HTTP 401)
- forbidden (HTTP 403)
- service unavailable (network or HTTP 5xx)
- validation failures (HTTP 422) that remain distinct from auth failures

Failed auth or blocked mutation attempts MUST NOT be presented as successful schedule or content changes.

#### Scenario: Auth failure is not shown as mutation success

- **WHEN** a mutation attempt fails because the session is anonymous, expired, or forbidden
- **THEN** the console shows a clear failure or blocked state and does not claim the schedule or variant was updated

#### Scenario: Service unavailable is distinct from auth missing

- **WHEN** the worker is unreachable or returns HTTP 5xx
- **THEN** the console communicates service unavailability distinctly from anonymous or expired-session messaging
