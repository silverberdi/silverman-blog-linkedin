## ADDED Requirements

### Requirement: Separated UI keeps BL-032 supervision reachable via absolute worker base URL

When Silverman Authority Manager runs as the separated operator UI, core supervision capabilities already Story accepted under BL-032 MUST remain reachable through the typed HTTP client using the configured absolute worker API base URL.

At minimum this includes:

- schedule visibility reads (`GET /flow-a/schedule-visibility`)
- pending-supervision / LinkedIn control-center reads (`GET /flow-a/linkedin-variants/pending-supervision`)
- representative authenticated control-center mutation path(s) already Story accepted (prefer dry-run-safe postpone/defer or equivalently gated existing actions)

Business screen components MUST continue to call the worker only through the typed client boundary. Separated mode MUST NOT silently use relative same-origin API paths when an absolute base URL is configured.

This requirement does not reopen BL-032 product design and does not require inventing new worker endpoints.

#### Scenario: Schedule visibility reachable from separated UI client

- **WHEN** the separated UI is configured with a valid absolute API base URL and requests schedule visibility through the typed client
- **THEN** the client calls the worker schedule-visibility route on that absolute origin

#### Scenario: Pending-supervision reachable from separated UI client

- **WHEN** the separated UI is configured with a valid absolute API base URL and requests pending-supervision through the typed client
- **THEN** the client calls the worker pending-supervision route on that absolute origin

#### Scenario: Representative dry-run mutation reachable from separated UI client

- **WHEN** an authenticated separated-UI session with mutation capability issues a dry-run-safe BL-032 control-center mutation through the typed client
- **THEN** the client posts to the existing worker mutation route on the configured absolute origin

### Requirement: Separated UI preserves US-040D auth handoff for future Google login

On the separated operator UI, authentication MUST remain behind the injectable auth provider / typed client boundary established for US-040D. Operators MUST be able to establish a session (Bearer paste or current local mechanism), observe `canMutate` gating for mutations, and clear the session, without rewriting calendar/control-center business screens.

Google/OIDC login (BL-035) MUST NOT be implemented by this requirement. The boundary MUST remain replaceable later without rewriting business screens.

#### Scenario: Sign-in enables mutation capability without Google

- **WHEN** an operator supplies a valid credential through the existing injectable auth boundary on the separated UI
- **THEN** the console can enter an authenticated mutating-capable state (`canMutate` true) without Google/OIDC UI or protocols

#### Scenario: Clear session disables mutations

- **WHEN** an authenticated separated-UI operator clears the session
- **THEN** mutations are no longer permitted through `canMutate` gating until re-authentication

#### Scenario: Business screens stay auth-provider agnostic

- **WHEN** the auth provider implementation at the API-client boundary is considered for a future Google/OIDC replacement
- **THEN** calendar and control-center business components are not required to be rewritten solely to swap the provider (existing injectable boundary preserved)
