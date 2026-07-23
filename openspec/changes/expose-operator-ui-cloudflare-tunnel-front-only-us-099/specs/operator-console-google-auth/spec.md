## MODIFIED Requirements

### Requirement: US-097 outcomes are visible; public topology deferred

Google sign-in success, forbidden/deny, and anonymous blocked states MUST be visible and understandable to the operator on the separated UI.

US-097 alone MUST NOT activate Cloudflare Tunnel front-only public topology. Public front-only exposure is owned by US-099. CURRENT-STATE updates for US-097 MUST describe Google identity activation on the separated LAN UI without claiming Story accepted.

#### Scenario: Operator sees sign-in and deny outcomes

- **WHEN** an operator uses Google sign-in on the separated UI
- **THEN** success (allowlisted) and deny (non-allowlisted) outcomes are clearly communicated in the UI

#### Scenario: US-097 does not itself activate public tunnel topology

- **WHEN** US-097 is implemented in isolation from US-099
- **THEN** docs do not claim Cloudflare Tunnel front-only public exposure solely from US-097

### Requirement: US-098 outcomes visible; public topology still deferred

Operator JWT console→API success, auth failure, expired-session, and anonymous blocked states MUST be visible and understandable on the separated UI. CURRENT-STATE updates for US-098 MUST describe JWT/session console→API cutover without claiming Story accepted. Public front-only exposure remains owned by US-099.

#### Scenario: Operator sees JWT-path auth outcomes

- **WHEN** an operator uses the Google-enabled console with operator JWT/session auth
- **THEN** authenticated success, auth failure, and expired-session outcomes are clearly communicated

#### Scenario: US-098 does not itself activate public tunnel topology

- **WHEN** US-098 is implemented in isolation from US-099
- **THEN** docs do not claim Cloudflare Tunnel front-only public exposure solely from US-098

## ADDED Requirements

### Requirement: Public UI URL preserves Google and JWT fail-closed outcomes (US-099)

When Cloudflare Tunnel front-only public UI topology (US-099) is active, operators MUST use the public UI URL with Google sign-in. Unauthenticated and non-allowlisted access via that URL MUST fail closed with clear messaging. Operator JWT/session console→API behavior (US-098) MUST remain intact through the private UI→API hop. Any cookie SameSite/Secure/Path adjustment required by the public topology MUST be minimal and documented and MUST NOT rewrite allowlist membership or JWT issuer/audience/expiry validation rules.

#### Scenario: Public URL anonymous visitor cannot mutate

- **WHEN** an operator opens the public Cloudflare UI URL without a valid operator session
- **THEN** the UI presents an unauthenticated blocked state and does not grant mutating capability

#### Scenario: Non-allowlisted Google identity denied on public URL

- **WHEN** a non-allowlisted Google identity completes OIDC via the public UI URL
- **THEN** the console presents a clear forbidden/denied outcome and does not mint a mutable operator session

#### Scenario: Allowlisted Google sign-in works on public URL

- **WHEN** an allowlisted operator signs in with Google via the public UI URL under US-099 topology
- **THEN** the console can enter an authenticated mutating-capable state using the operator JWT/session credential through the private hop without pasting the worker API key
