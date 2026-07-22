## MODIFIED Requirements

### Requirement: Topology docs distinguish Google identity from public exposure

Operator-facing deployment documentation and CURRENT-STATE topology pointers SHALL briefly state when Google (OIDC) identity/allowlist is activated on the separated LAN UI (`:8011`) and when operator JWT/session console→API auth (US-098) is active, without claiming that the console is publicly exposed via Cloudflare Tunnel (US-099).

#### Scenario: CURRENT-STATE records Google identity and JWT cutover without public claim

- **WHEN** US-098 docs updates are applied after implementation
- **THEN** CURRENT-STATE (or linked ops doc) records Google identity/allowlist plus operator JWT/session console→API on the separated UI and explicitly does not claim US-099 public front-only topology or Story accepted solely from implementation

#### Scenario: Env examples remain secrets-safe for JWT signing

- **WHEN** an operator reads deploy env examples for Google console auth and operator JWT/session signing
- **THEN** examples name configuration keys (including issuer/audience/signing secret names as applicable) and use non-secret placeholders without real secrets or API keys
