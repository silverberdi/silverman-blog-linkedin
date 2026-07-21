## Why

BL-025 (**US-060** + **US-061**) still lacks a single operator-facing source of truth for LinkedIn token lifecycle: secure storage, renewal/expiration, revocation, invalid-token detection, recovery, and development vs production separation. Much of this is already implemented (`linkedin-oauth-token-lifecycle`, prerequisites docs, `/linkedin/oauth/status`), but product stories remain open and CURRENT-STATE still notes missing refresh token in production. Without a thin SoT, operators cannot see “secure, predictable, and recoverable” as one contract.

## What Changes

- Publish `docs/operations/linkedin-token-management.md` as the BL-025 / US-060+US-061 operator SoT covering storage, renewal/expiry, revocation, invalid detection, recovery, and dev vs prod separation.
- Ratify existing worker OAuth behavior and deployment docs; call out the known production gap (`refresh_token` absent → reauth when access expires).
- Introduce capability `linkedin-token-management` (documentation/contract) — does not rewrite publication pipelines or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Update CURRENT-STATE / GLOSSARY / product pointers; mark US-060 + US-061 Story accepted and close BL-025 when the SoT matches acceptance criteria.
- Thin cross-link from LinkedIn prerequisites / US-059 cadence row (pointer only).

### Goals

- Satisfy **US-060** (store securely; renewal/expiration; revocation) and **US-061** (detect invalid; separate dev/prod; document recovery) in one coherent procedure.
- Make outcomes visible; communicate healthy / action_required / blocked without printing token values.
- Preserve completed LinkedIn publication work; no enablement mutation; no forced reauth if current status is healthy.

### Non-goals

- Re-implementing OAuth endpoints or publication flow.
- Requiring a live invalid-token incident for Story accepted.
- Rotating LinkedIn client secret or forcing reauth as part of apply.
- Closing BL-026 or expanding into general secrets (BL-024 already closed).
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or auto-publishing LinkedIn.
- Building a secrets vault or separate LinkedIn Developer app unless operator chooses later.

### Acceptance criteria addressed

| Story | Criterion | How addressed |
|-------|-----------|---------------|
| US-060 | Store tokens securely | SoT § storage (paths, modes, env-only secrets) |
| US-060 | Handle renewal and expiration | SoT § renewal (refresh skew; missing refresh → reauth) |
| US-060 | Support revocation | SoT § revocation (store clear + reauth; portal revoke) |
| US-061 | Detect invalid tokens | SoT § detection (`/linkedin/oauth/status`, action_required codes) |
| US-061 | Separate development and production credentials | SoT § env separation |
| US-061 | Document recovery | SoT § recovery runbook |
| Both | Visible / blocked / no unintended churn | Pointers + vocabulary + docs-only scope |

### Intentionally excluded

- Live forced reauthorization when status is healthy.
- Full BL-026 exposure review.
- New worker routes unless a gap is found that cannot be documented (default: none).

## Capabilities

### New Capabilities

- `linkedin-token-management`: Operator-visible normative LinkedIn token management SoT for **BL-025 / US-060 + US-061** — secure storage, renewal/expiration, revocation, invalid-token detection, recovery, and development vs production separation — ratifying existing `linkedin-oauth-token-lifecycle` behavior without requiring live invalid tokens, publication enablement mutation, or a secrets vault.

### Modified Capabilities

- (none — existing `linkedin-oauth-token-lifecycle` remains the implementation/spec authority for worker OAuth mechanics; this change adds the product/operator SoT capability)

## Impact

- **Product:** Closes **BL-025** after US-060 + US-061 Story accepted.
- **Docs:** New ops SoT; CURRENT-STATE / GLOSSARY / product updates; thin pointers from prerequisites / US-059.
- **OpenSpec:** New capability after sync; no requirement rewrite of publish/queue/cancel.
- **Runtime:** No required code changes; optional status check for evidence (metadata only).
- **Preserved:** ADR-0001; LinkedIn publication guards; US-059 cadence pointers to BL-025.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-025 / US-060 / US-061** | Primary — formalize LinkedIn token management |
| `linkedin-oauth-token-lifecycle` | Existing implementation/spec — ratify, do not contradict |
| US-059 | Cadence row points here for LinkedIn token store |
| BL-024 | Closed — do not reopen |
| BL-026 | Out of scope |
