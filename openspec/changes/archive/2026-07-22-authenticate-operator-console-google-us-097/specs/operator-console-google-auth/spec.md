## ADDED Requirements

### Requirement: Google OIDC sign-in without worker API-key paste

The separated Silverman Authority Manager UI (`:8011` path) SHALL allow operators to start a Google (OIDC) sign-in and complete authentication for an allowlisted identity without pasting a worker API key for that sign-in step.

Sign-in MUST run through the injectable `AuthProvider` / typed client boundary. Calendar and control-center business screens MUST NOT be rewritten solely to integrate Google login.

#### Scenario: Operator completes Google sign-in without API-key paste

- **WHEN** an allowlisted operator starts Google (OIDC) sign-in from the separated operator UI and Google authentication succeeds
- **THEN** the console establishes an authenticated session without prompting for or requiring a worker API key paste during that sign-in step

#### Scenario: Sign-in uses AuthProvider boundary

- **WHEN** Google OIDC sign-in is invoked from the separated UI
- **THEN** authentication is initiated through the injectable `AuthProvider` seam rather than ad-hoc Google calls from calendar/control-center business components

### Requirement: Fail-closed Google email allowlist

Access via Google sign-in MUST be allowlisted to exactly these Google account emails (case-normalized comparison permitted):

- `silverio.bernal@gmail.com`
- `ltmoralesp84@gmail.com`

Any other authenticated Google identity MUST be denied (fail closed). Allowlist enforcement MUST occur server-side on the OIDC/identity path; client-only allowlist checks MUST NOT be the sole authorization gate.

#### Scenario: Allowlisted email may authenticate

- **WHEN** a Google identity with email `silverio.bernal@gmail.com` or `ltmoralesp84@gmail.com` completes OIDC successfully
- **THEN** the operator console may enter an authenticated mutable session state (`canMutate` true) for that identity

#### Scenario: Non-allowlisted Google identity is denied

- **WHEN** a Google identity with any other email completes OIDC successfully at Google
- **THEN** the console does not grant an authenticated mutable session and fails closed for that identity

### Requirement: Non-allowlisted Google identity shows clear forbidden outcome

When a Google identity authenticates at Google but is not on the allowlist, the separated operator UI MUST present a clear operator-visible denied/forbidden outcome using US-040D session vocabulary (at least `forbidden`).

The UI MUST NOT present a silent empty console that appears normally authenticated for that identity.

#### Scenario: Forbidden state is distinct and visible

- **WHEN** a non-allowlisted Google identity completes OIDC at Google
- **THEN** the operator sees a forbidden/denied message distinct from anonymous and authenticated states and does not see a normal authenticated empty supervision console

### Requirement: Unauthenticated visitors cannot mutate

Unauthenticated (anonymous) visitors on the separated operator UI MUST NOT reach mutating console capabilities. Mutation controls MUST remain non-executable while `canMutate` is false.

Anonymous and blocked/forbidden states MUST remain understandable using US-040D session vocabulary (`anonymous`, `authenticated`, `expired`, `forbidden`, and existing blocked messaging patterns).

#### Scenario: Anonymous cannot mutate

- **WHEN** the separated UI session is anonymous (no credential / no Google session)
- **THEN** the console does not execute mutating actions and communicates that authentication is required

#### Scenario: Forbidden cannot mutate

- **WHEN** the session is forbidden (including non-allowlisted Google identity)
- **THEN** `canMutate` is false and mutating console capabilities are not executable

### Requirement: Google client configuration is env/secrets only

Google OIDC client configuration MUST use environment variables and/or server secrets only. Frontend source, rendered HTML, bundled assets, logs, HTTP error bodies, and committed docs MUST NOT contain Google client secrets, refresh tokens, worker API keys, session signing secrets, or secret-like placeholders for those values.

Non-secret values (for example public OAuth client ID, redirect URI, enablement flag) MAY appear in runtime-injected UI config using non-secret placeholders in examples.

#### Scenario: Client secret absent from frontend artifacts

- **WHEN** frontend source and built separated-UI assets are scanned for Google client secrets, refresh tokens, and worker API keys
- **THEN** no such secret values are present

#### Scenario: Docs and examples use placeholders only

- **WHEN** an operator reads deploy env examples for Google OIDC
- **THEN** examples name configuration keys and use non-secret placeholders without real client secrets or API keys

### Requirement: Identity session bridge preserves n8n API-key auth

After an allowlisted Google identity is established, the AuthProvider MAY hold an operator identity session (cookie or opaque token) so browser console use does not require API-key paste for the sign-in step.

The worker MUST continue to accept existing API-key authentication for machine clients (n8n → worker HTTP). Enabling Google console identity MUST NOT break that path, MUST NOT introduce n8n Execute Command, and MUST NOT make the UI an n8n execution target.

Formal replacement of browser API-key use with operator JWT-only console→API auth (issuer/audience policy, removing dual-accept) remains out of scope for US-097 and belongs to US-098.

#### Scenario: n8n API-key path remains valid

- **WHEN** Google console identity auth is enabled for the separated UI
- **THEN** n8n → worker authenticated HTTP calls using the existing API key continue to succeed under ADR-0001

#### Scenario: US-098 JWT cutover not claimed by US-097

- **WHEN** US-097 identity/allowlist work is complete
- **THEN** documentation does not claim that browser console→API auth is JWT-only or that worker API-key use in the browser is fully removed (US-098)

### Requirement: US-097 outcomes are visible; public topology deferred

Google sign-in success, forbidden/deny, and anonymous blocked states MUST be visible and understandable to the operator on the separated UI.

US-097 MUST NOT activate Cloudflare Tunnel front-only public topology, public UI hostname exposure, or tunnel-oriented CORS changes (US-099). CURRENT-STATE updates for this story MUST describe Google identity activation on the separated LAN UI without claiming public console exposure or Story accepted.

#### Scenario: Operator sees sign-in and deny outcomes

- **WHEN** an operator uses Google sign-in on the separated UI
- **THEN** success (allowlisted) and deny (non-allowlisted) outcomes are clearly communicated in the UI

#### Scenario: Public tunnel topology remains deferred

- **WHEN** US-097 is implemented
- **THEN** docs do not claim Cloudflare Tunnel front-only public exposure or US-099 completion
