## MODIFIED Requirements

### Requirement: Separated UI preserves US-040D auth handoff for future Google login

On the separated operator UI, authentication MUST remain behind the injectable auth provider / typed client boundary established for US-040D. Operators MUST be able to establish a session, observe `canMutate` gating for mutations, and clear the session, without rewriting calendar/control-center business screens.

When Google (OIDC) console authentication is enabled (BL-035 / US-097+US-098), the default separated-UI sign-in path MUST use Google OIDC through that injectable boundary and MUST NOT require worker API-key paste for sign-in or for subsequent console→API calls. Browser→worker calls on that path MUST send an operator JWT (or equivalent secure session credential), not the worker API key. Non-allowlisted Google identities MUST map to a clear forbidden/denied session state.

A transitional MemoryBearer / API-key provider MAY remain available for tests or explicitly documented Google-disabled local fallback, but MUST NOT be required on the enabled Google path and MUST NOT be the default AuthProvider when Google auth is enabled.

#### Scenario: Google sign-in enables mutation capability without API-key paste

- **WHEN** an allowlisted operator signs in with Google via the injectable auth boundary on the separated UI
- **THEN** the console can enter an authenticated mutating-capable state (`canMutate` true) without pasting a worker API key for that sign-in step

#### Scenario: Google path console calls use operator credential not API key

- **WHEN** an allowlisted Google-authenticated session exercises worker capabilities through the typed client
- **THEN** requests authenticate with the operator JWT/session credential and do not send the worker API key

#### Scenario: Clear session disables mutations

- **WHEN** an authenticated separated-UI operator clears the session
- **THEN** mutations are no longer permitted through `canMutate` gating until re-authentication and the operator credential is no longer sent

#### Scenario: Business screens stay auth-provider agnostic

- **WHEN** the auth provider implementation at the API-client boundary uses Google OIDC plus operator JWT/session for console→API
- **THEN** calendar and control-center business components are not required to be rewritten solely to swap or use the provider (existing injectable boundary preserved)

### Requirement: Browser API access uses a typed client with injectable auth

All browser calls to worker supervision APIs MUST go through a typed API client (or equivalent centralized boundary).

The client MUST centralize request construction, response typing, and error mapping for at least:

- `GET /flow-a/linkedin-variants/pending-supervision`
- `GET /flow-a/schedule-visibility`
- `POST /correct-linkedin-variant`
- `POST /defer-linkedin-variant`
- `POST /cancel-linkedin-publication`
- `POST /editorial-calendar/update-item-schedule`

Auth credentials MUST be injectable at the API-client boundary (for example via an `AuthProvider` headers/credentials provider) so Google/OIDC bearer or secure session cookie strategies can supply credentials without changing list, month calendar, or schedule-editor business components.

The auth/client boundary MUST expose operator session and capability signals sufficient for UI gating, including at least whether a credential is held and whether mutations are allowed (`canMutate`), without requiring calendar components to parse raw HTTP status codes for auth policy.

Frontend source, rendered HTML, logs, and browser storage MUST NOT embed API keys, bearer tokens, OAuth client secrets, refresh tokens, operational secrets, mount paths, or secret-like placeholders.

When Google console auth is enabled (US-097/US-098), the separated-UI path MUST NOT paste or send the worker API key for sign-in or console→API calls; operator JWT/session credential is required instead. Machine clients (n8n) continue API-key auth (ADR-0001).

#### Scenario: Business components do not call fetch directly for worker APIs

- **WHEN** list, calendar, or schedule-editor components load pending supervision or schedule-visibility data or submit edit/defer/cancel/calendar schedule-update
- **THEN** those components use the typed API client rather than ad-hoc `fetch`/`XMLHttpRequest` calls scattered across view code

#### Scenario: Auth provider can be swapped without editing calendar components

- **WHEN** the auth provider implementation is replaced at the API-client boundary with a Google/OIDC operator JWT or secure session-cookie strategy
- **THEN** list, month calendar, and schedule-editor business components do not require changes to continue calling the same client methods

#### Scenario: Secrets and local-only assumptions are absent from frontend artifacts

- **WHEN** frontend source and built console assets are scanned for API keys, bearer tokens, Google client secrets, refresh tokens, or secret-like placeholders such as `CHANGE_ME`
- **THEN** no such values are present

#### Scenario: Google sign-in does not require API-key paste

- **WHEN** an operator authenticates on the Google-enabled separated UI path
- **THEN** credentials for the sign-in step are established via Google OIDC through the injectable auth provider and are not obtained by pasting the worker API key

#### Scenario: Google path does not send worker API key on console calls

- **WHEN** the Google-enabled AuthProvider issues typed-client requests after allowlisted sign-in
- **THEN** those requests do not include an Authorization header bearing the worker API key

### Requirement: Console represents explicit auth session states

The supervision console MUST represent the following operator-facing session states in the UI, including under Google (OIDC) identity activation and operator JWT/session console auth (US-097/US-098):

- anonymous (no credential held)
- authenticated (credential held and session usable — allowlisted Google identity with valid operator JWT/session)
- expired-session (prior credential invalidated; re-auth required)
- forbidden (credential/identity present but not authorized — including non-allowlisted Google identity)
- service-unavailable (worker/API unreachable or HTTP 5xx)

Session-state presentation MUST be understandable without implying LinkedIn API published, and MUST NOT equate `pending`, `queued`, `cancelled`, `flow_a_complete`, or blog handoff with LinkedIn API published.

Non-allowlisted Google sign-in MUST surface as `forbidden` (or equivalent clear denied) and MUST NOT silently appear as a normal authenticated empty console.

Expired or invalid operator JWT/session responses MUST surface as `expired-session` (or clear re-auth guidance) without claiming mutation success.

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

- **WHEN** the typed client receives HTTP 403 or Google identity is denied by allowlist
- **THEN** the UI presents a forbidden/not-authorized state distinct from expired-session and authenticated

#### Scenario: Service unavailable state is visible

- **WHEN** the typed client encounters a network failure or HTTP 5xx response
- **THEN** the UI presents a service-unavailable state and does not claim the request succeeded

### Requirement: Public URL and Google authentication activation remain deferred

US-040D readiness documentation historically deferred public deployment and Google/OIDC activation. Under BL-035:

- **US-097** activates Google (OIDC) identity and email allowlist on the separated operator UI (LAN).
- **US-098** activates operator JWT/session console→API auth (no worker API key on the Google browser path).
- **Public URL hosting / Cloudflare Tunnel front-only exposure (US-099)** remains out of scope and MUST NOT be activated by US-097 or US-098.
- US-097/US-098 MUST NOT introduce a general user-management product, MUST NOT use n8n Execute Command, and MUST NOT use browser filesystem writes as the auth source of truth.

#### Scenario: Public URL activation remains deferred after US-098

- **WHEN** US-098 operator JWT console→API activation is complete
- **THEN** CURRENT-STATE or equivalent operator documentation records that public URL hosting / Cloudflare front-only topology is not activated and remains US-099

#### Scenario: Google identity activation is in scope for US-097

- **WHEN** an implementer inspects the US-097 change scope
- **THEN** a live Google OAuth/OIDC login flow for allowlisted operators on the separated UI is required, and worker API-key paste is not required for that sign-in step

#### Scenario: Operator JWT console auth is in scope for US-098

- **WHEN** an implementer inspects the US-098 change scope
- **THEN** Google-path browser→worker calls must use operator JWT/session credentials (not the worker API key), and the worker must fail closed on invalid operator credentials
