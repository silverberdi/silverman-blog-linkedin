## MODIFIED Requirements

### Requirement: Public URL and Google authentication activation remain deferred

US-040D readiness documentation historically deferred public deployment and Google/OIDC activation. Under BL-035:

- **US-097** activates Google (OIDC) identity and email allowlist on the separated operator UI (LAN and, when US-099 is active, public UI URL).
- **US-098** activates operator JWT/session console→API auth (no worker API key on the Google browser path).
- **US-099** activates public URL hosting / Cloudflare Tunnel front-only exposure of the operator UI with private worker API and private UI→API hop.
- US-097/US-098/US-099 MUST NOT introduce a general user-management product, MUST NOT use n8n Execute Command, and MUST NOT use browser filesystem writes as the auth source of truth.

#### Scenario: Public URL activation is in scope for US-099

- **WHEN** an implementer inspects the US-099 change scope
- **THEN** front-only Cloudflare Tunnel (or equivalent) public UI exposure with private API and private UI→API hop is required, and the worker API is not published on the public internet

#### Scenario: Google identity activation is in scope for US-097

- **WHEN** an implementer inspects the US-097 change scope
- **THEN** a live Google OAuth/OIDC login flow for allowlisted operators on the separated UI is required, and worker API-key paste is not required for that sign-in step

#### Scenario: Operator JWT console auth is in scope for US-098

- **WHEN** an implementer inspects the US-098 change scope
- **THEN** Google-path browser→worker calls must use operator JWT/session credentials (not the worker API key), and the worker must fail closed on invalid operator credentials

#### Scenario: Public console uses private-hop API base

- **WHEN** US-099 front-only topology is active and the separated UI typed client issues worker capability calls
- **THEN** those calls use a same-origin or otherwise private API base and do not require a publicly routable worker API hostname in the browser
