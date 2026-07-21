## Context

BL-025 asks for formal LinkedIn token management (US-060 store/renew/revoke; US-061 detect invalid / separate credentials / recovery). Worker already implements OAuth authorize/callback/status, file token store (`chmod 600`), refresh-before-publish when refresh token exists, and fail-closed `linkedin_oauth_reauthorization_required`. Operator docs are split across `linkedin-publication-prerequisites.md` and the oauth lifecycle spec. Production currently has a valid access token but **no refresh token** (CURRENT-STATE / US-058 status) — healthy today, reauth required when access expires.

Operator direction (2026-07-21): work US-060+US-061 together; LinkedIn connection works; do not require inventing an invalid token for acceptance; prefer docs/contract SoT at `docs/operations/linkedin-token-management.md`.

## Goals / Non-Goals

**Goals:**

- One operator SoT covering US-060 + US-061 ACs.
- Ratify existing behavior; document refresh-token gap and recovery.
- Close BL-025 after Story accepted.
- Vocabulary without secret values.

**Non-Goals:**

- New OAuth implementation; forced reauth; enablement mutation; BL-026; secrets vault; second LinkedIn app unless chosen later.

## Decisions

1. **Docs/procedure-first single SoT** — `docs/operations/linkedin-token-management.md`; prerequisites keep deploy detail with thin pointer.
2. **New capability `linkedin-token-management`** — product/operator contract; do not MODIFY `linkedin-oauth-token-lifecycle` unless a true requirement conflict appears (none expected).
3. **Healthy-now is OK for US-061** — detection/recovery documented; optional `oauth/status` metadata evidence; no forced invalidation.
4. **Dev vs prod** — document separation by environment files/stores (server vs local); do not require a second Developer App in this change.
5. **BL-025 close** — both stories accepted together when SoT + pointers land and owner confirms.

## Risks / Trade-offs

- [Risk] Duplication with prerequisites → Mitigation: SoT owns lifecycle narrative; prerequisites keep setup steps + pointer.
- [Risk] Refresh-token gap forgotten → Mitigation: CURRENT-STATE + SoT explicit callout.
- [Trade-off] Docs-only vs code to obtain refresh token → docs-only now; reauth when expiry approaches is operator action.

## Migration Plan

1. Apply writes SoT + pointers; mark US-060/061 accepted; close BL-025.
2. No deploy required for docs; optional status check.
3. Rollback: revert commits.

## Open Questions

- None — SoT outline operator-approved 2026-07-21.
