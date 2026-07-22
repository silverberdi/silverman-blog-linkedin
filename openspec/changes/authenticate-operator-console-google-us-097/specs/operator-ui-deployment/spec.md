## ADDED Requirements

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
