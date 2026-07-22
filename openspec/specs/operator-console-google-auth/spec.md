# operator-console-google-auth

## Purpose

Google (OIDC) identity authentication and email allowlist for the separated Silverman Authority Manager operator UI (BL-035 / US-097): allowlisted operators sign in without pasting a worker API key, non-allowlisted identities fail closed with a clear forbidden outcome, secrets stay in env/server configuration, and n8n → worker API-key auth remains intact (ADR-0001). Formal JWT-only console→API cutover remains US-098; public Cloudflare Tunnel front-only exposure remains US-099.

## Requirements

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

After an allowlisted Google identity is established, the AuthProvider MUST hold an operator JWT (or equivalent secure session credential) so browser console→API calls do **not** send the worker API key. The credential MUST be issued and validated for the signed-in allowlisted identity (signature, expiry, issuer, audience, and allowlist membership).

The worker MUST continue to accept existing API-key authentication for machine clients (n8n → worker HTTP). Enabling Google console auth MUST NOT break that path, MUST NOT introduce n8n Execute Command, and MUST NOT make the UI an n8n execution target.

When Google console auth is enabled, the Google console path MUST use operator-credential-only auth for browser→worker calls (no worker API key in request headers from that path). Invalid or missing operator credentials MUST fail closed with a clear auth failure.

#### Scenario: Google console path does not send worker API key

- **WHEN** an allowlisted operator has completed Google sign-in on the Google-enabled separated UI
- **THEN** subsequent browser→worker capability calls authenticate with the operator JWT/session credential and do not include the worker API key in Authorization headers

#### Scenario: n8n API-key path remains valid

- **WHEN** Google console identity auth is enabled for the separated UI
- **THEN** n8n → worker authenticated HTTP calls using the existing API key continue to succeed under ADR-0001

#### Scenario: Invalid operator credential is rejected

- **WHEN** a console request presents an expired, tampered, wrong-issuer, wrong-audience, or non-allowlisted operator credential
- **THEN** the worker rejects the request with a clear auth failure (fail closed) and does not grant mutating or authenticated console capability

### Requirement: Operator JWT issuance and validation (US-098)

The worker MUST mint an operator JWT (or equivalent secure session credential with issuer, audience, expiry, and allowlisted email identity) after successful allowlisted Google OIDC completion. Validation MUST verify cryptographic integrity, `exp`, configured `iss` and `aud`, and that the email is on the US-097 allowlist. Secrets used for signing MUST remain env/server-only.

#### Scenario: Allowlisted identity receives valid operator credential

- **WHEN** an allowlisted Google identity completes OIDC successfully
- **THEN** the worker issues an operator JWT/session credential bound to that identity with issuer, audience, and expiry suitable for console→API use

#### Scenario: Tampered or wrong issuer/audience fails closed

- **WHEN** a request presents an operator credential with invalid signature, wrong issuer, or wrong audience
- **THEN** the worker rejects the request with a clear auth failure and does not treat the caller as an authenticated operator

### Requirement: Operator sign-out clears console credential

Operator sign-out / session clear on the Google console path MUST return the UI to a non-mutating unauthenticated state and MUST stop sending the operator credential on subsequent worker calls (including clearing the HttpOnly session cookie when cookie transport is used).

#### Scenario: Sign-out stops operator credential

- **WHEN** an authenticated Google-path operator clears the session / signs out
- **THEN** `canMutate` is false, the UI presents an unauthenticated state, and further browser→worker calls do not send a valid operator credential

### Requirement: US-097 outcomes are visible; public topology deferred

Google sign-in success, forbidden/deny, and anonymous blocked states MUST be visible and understandable to the operator on the separated UI.

US-097 MUST NOT activate Cloudflare Tunnel front-only public topology, public UI hostname exposure, or tunnel-oriented CORS changes (US-099). CURRENT-STATE updates for this story MUST describe Google identity activation on the separated LAN UI without claiming public console exposure or Story accepted.

#### Scenario: Operator sees sign-in and deny outcomes

- **WHEN** an operator uses Google sign-in on the separated UI
- **THEN** success (allowlisted) and deny (non-allowlisted) outcomes are clearly communicated in the UI

#### Scenario: Public tunnel topology remains deferred

- **WHEN** US-097 is implemented
- **THEN** docs do not claim Cloudflare Tunnel front-only public exposure or US-099 completion

### Requirement: US-098 outcomes visible; public topology still deferred

Operator JWT console→API success, auth failure, expired-session, and anonymous blocked states MUST be visible and understandable on the separated UI. CURRENT-STATE updates for US-098 MUST describe JWT/session console→API cutover on the separated LAN UI without claiming Cloudflare Tunnel front-only public exposure (US-099) or Story accepted.

#### Scenario: Operator sees JWT-path auth outcomes

- **WHEN** an operator uses the Google-enabled console with operator JWT/session auth
- **THEN** authenticated success, auth failure, and expired-session outcomes are clearly communicated

#### Scenario: Public tunnel topology remains deferred after US-098

- **WHEN** US-098 is implemented
- **THEN** docs do not claim Cloudflare Tunnel front-only public exposure or US-099 completion
