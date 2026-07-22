## MODIFIED Requirements

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

## ADDED Requirements

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

### Requirement: US-098 outcomes visible; public topology still deferred

Operator JWT console→API success, auth failure, expired-session, and anonymous blocked states MUST be visible and understandable on the separated UI. CURRENT-STATE updates for US-098 MUST describe JWT/session console→API cutover on the separated LAN UI without claiming Cloudflare Tunnel front-only public exposure (US-099) or Story accepted.

#### Scenario: Operator sees JWT-path auth outcomes

- **WHEN** an operator uses the Google-enabled console with operator JWT/session auth
- **THEN** authenticated success, auth failure, and expired-session outcomes are clearly communicated

#### Scenario: Public tunnel topology remains deferred after US-098

- **WHEN** US-098 is implemented
- **THEN** docs do not claim Cloudflare Tunnel front-only public exposure or US-099 completion
