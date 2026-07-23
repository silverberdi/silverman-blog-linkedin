## ADDED Requirements

### Requirement: Cloudflare Tunnel front-only public UI topology (US-099)

The supported public topology for Silverman Authority Manager MUST publish **only** the separated operator UI via Cloudflare Tunnel (or equivalent public ingress). The worker API MUST remain LAN / private-network only and MUST NOT be published as a public internet hostname for Authority Manager operations.

#### Scenario: Public ingress targets UI only

- **WHEN** US-099 front-only public topology is activated
- **THEN** the public Cloudflare (or equivalent) hostname reaches the separated operator UI service and does not publish the worker API as a public Authority Manager API hostname

#### Scenario: Worker API remains private

- **WHEN** an operator reviews accepted exposure after US-099 activation
- **THEN** the worker API is documented as LAN / private-network only for console and n8n use and is not an accepted public internet surface for Authority Manager

### Requirement: Private UI→API hop without public API base URL

The internet-facing console MUST NOT require operators to configure a publicly routable worker API base URL in the browser. UI→API traffic MUST use a private hop (same-origin reverse proxy, internal Docker DNS, or equivalent) so the API hostname is not internet-exposed.

#### Scenario: Browser uses same-origin or private API base

- **WHEN** an operator uses the public Cloudflare UI URL with US-099 topology active
- **THEN** the typed client targets a same-origin or otherwise private API base and does not require a publicly routable worker API hostname in browser configuration

### Requirement: Public UI origin CORS allowlist without wildcard

CORS / origin allowlisting and tunnel hostname configuration MUST match the public UI origin. Permissive `*` CORS MUST NOT be introduced for this exposure.

#### Scenario: Public UI origin is explicitly allowlisted

- **WHEN** residual cross-origin browser→worker calls are used with a public UI origin
- **THEN** `SILVERMAN_OPERATOR_UI_ORIGINS` (or equivalent) includes that exact public origin and CORS permits it according to the allowlist

#### Scenario: Wildcard CORS remains forbidden

- **WHEN** US-099 public topology configuration is reviewed
- **THEN** the worker does not advertise Access-Control-Allow-Origin `*` for Authority Manager console exposure

## MODIFIED Requirements

### Requirement: Topology docs distinguish Google identity from public exposure

Operator-facing deployment documentation and CURRENT-STATE topology pointers SHALL briefly state when Google (OIDC) identity/allowlist is activated, when operator JWT/session console→API auth (US-098) is active, and when Cloudflare Tunnel front-only public UI exposure (US-099) is active—with the worker API remaining private. Documentation MUST NOT claim Story accepted solely from implementation.

#### Scenario: CURRENT-STATE records front-only public UI without public API

- **WHEN** US-099 docs updates are applied after implementation
- **THEN** CURRENT-STATE (or linked ops doc) records front-only public UI exposure via Cloudflare Tunnel (or equivalent), private worker API, private UI→API hop, and Google allowlist/JWT console auth without claiming the worker API is internet-public or Story accepted solely from implementation

#### Scenario: Env examples remain secrets-safe for public topology

- **WHEN** an operator reads deploy env examples for public UI origin, CORS allowlist, and tunnel-related settings
- **THEN** examples name configuration keys and use non-secret placeholders without real secrets, API keys, or tunnel tokens

### Requirement: Topology documentation for separated UI

Operator-facing deployment documentation and CURRENT-STATE topology pointers SHALL briefly describe the separated UI service alongside the worker API (including LAN ports or equivalent and, when US-099 is active, the public UI hostname), state that the worker remains the HTTP API source of truth and is API-only for operator console purposes after US-096, and state that the UI is a client only.

Documentation SHALL describe UAT vs prod UI↔API pairing (env var names and default overlays) per US-094. Documentation MUST NOT present the embedded worker console as a supported or compatibility production path. Documentation MUST NOT claim full BL-029 CI/UAT stand-up is complete merely because pairing defaults or public UI topology exist.

When US-099 is active, documentation MUST describe front-only public UI exposure + private API + private UI→API hop without embedding secrets.

RUNTIME-STATE SHALL be updated when live deployment flags or topology for pairing, console delivery, or public front-only exposure change on a running stack.

#### Scenario: CURRENT-STATE points to UI + API topology

- **WHEN** an operator reads CURRENT-STATE runtime topology after US-096 docs updates
- **THEN** the document (or a linked operator deploy doc) identifies the worker API endpoint and the separated operator UI endpoint as distinct services, describes UAT/prod pairing configuration by env var name, and does not list worker-embedded console serving as a supported or compatibility production path

#### Scenario: RUNTIME-STATE updated when live topology changes

- **WHEN** an operator applies US-099 front-only public topology (or pairing) configuration on a live deployed stack
- **THEN** RUNTIME-STATE (or the linked live-ops note) records the non-secret topology in effect without secret values

#### Scenario: Docs describe front-only public UI when US-099 active

- **WHEN** US-099 is implemented and documented
- **THEN** CURRENT-STATE or ubuntu deploy docs describe Cloudflare Tunnel (or equivalent) UI-only public exposure and private worker API without printing secrets
