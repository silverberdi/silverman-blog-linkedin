## MODIFIED Requirements

### Requirement: Focused separated-UI capability regression matrix

After operator UI/API separation (US-093) and environment pairing (US-094), the system SHALL provide a focused regression/smoke program that demonstrates day-to-day operator supervision remains available on the supported production path: separated operator UI → worker API over HTTP using `SILVERMAN_OPERATOR_UI_API_BASE_URL` (and paired environment labels where required), including when that base is same-origin / private-hop under US-099 front-only public topology.

The minimum matrix MUST cover all of the following:

1. Typed client absolute or same-origin base-URL behavior in separated mode (no unintended relative fallback when separated config is invalid).
2. Schedule visibility read via the typed client against the configured worker origin / private hop.
3. Pending-supervision / LinkedIn control-center read (BL-032 Story-accepted path) via the typed client.
4. At least one representative authenticated mutation already Story accepted under BL-032, preferring a dry-run-safe or clearly gated action (for example postpone/defer with `dry_run: true`), without inventing new endpoints.
5. US-040D auth session gating on the separated UI: sign-in, `canMutate`, and clear session. When Google (OIDC) auth is enabled (US-097/US-098), the matrix MUST cover Google sign-in / allowlist deny / anonymous non-mutate holds without requiring worker API-key paste, and MUST cover Google-path console→API using operator JWT/session (not worker API key) plus clear-session stopping the credential.
6. Retention of US-093 configuration fail-closed and US-094 pairing fail-closed operator-visible blocked states.
7. Confirmation that ADR-0001 remains intact (n8n → worker HTTP only on the private API) and that this program does not mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or rewrite Flow/LinkedIn business contracts.
8. When US-099 is enabled, confirmation that the public path does not require a public worker API hostname and that evidence does not claim the worker API is internet-published.

Evidence MUST be collectible via automated tests and/or controlled local/LAN/public-UI smoke. Documentation of evidence MUST NOT mark Story accepted solely because tests were written.

#### Scenario: Absolute or same-origin base URL used for schedule visibility

- **WHEN** the separated UI typed client is configured with a valid worker API base (absolute LAN or same-origin private hop) and requests schedule visibility
- **THEN** the HTTP call targets the configured base’s `/flow-a/schedule-visibility` path and does not fall back to an unintended unsupported origin

#### Scenario: Google path uses operator JWT not worker API key

- **WHEN** Google auth is enabled and an allowlisted session exercises a typed-client worker call
- **THEN** the call authenticates with the operator JWT/session credential and does not send the worker API key

#### Scenario: US-099 regression does not claim public API or Story accepted

- **WHEN** US-099 front-only holds are recorded in docs or checklists
- **THEN** the record does not claim the worker API is internet-published and does not claim Story accepted without the operator acceptance gate

### Requirement: Separated-UI regression preserves non-goals

The US-095 regression program MUST NOT stand up full BL-029 CI/UAT beyond what the matrix needs, MUST NOT introduce n8n Execute Command, MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and MUST NOT redesign US-093 packaging or US-094 pairing semantics (verify hold only).

Google/OIDC console identity, operator JWT console→API auth, and front-only public UI topology (BL-035 / US-097/US-098/US-099) are owned by their OpenSpec changes; the US-095 matrix MUST remain compatible with those holds when enabled and MUST NOT mark Story accepted solely from regression updates.

US-096 hard decommission of the embedded worker console is intentionally out of scope for the US-095 program itself; after US-096 lands, regression holds for the separated path MUST remain applicable and MUST NOT depend on restoring the embedded console.

#### Scenario: Publication enablement unchanged by regression program

- **WHEN** US-095 changes are reviewed for publication guards
- **THEN** `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not mutated as part of the regression program

#### Scenario: Regression does not claim Story accepted

- **WHEN** Google identity, operator JWT, and US-099 front-only holds are present and regression holds are updated
- **THEN** evidence does not mark Story accepted solely from those holds
