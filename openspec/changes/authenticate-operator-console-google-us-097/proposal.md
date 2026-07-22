## Why

Silverman Authority Manager on `:8011` still signs operators in by pasting the worker API key (US-040D / BL-034). Before any public front exposure (US-099), operators need Google (OIDC) sign-in with a fail-closed email allowlist so only approved Google accounts can authenticate. **BL-035 / US-097** activates that identity gate without rewriting business screens or claiming Cloudflare / JWT console→API replacement (US-098 / US-099).

## What Changes

- Enable **Google OIDC sign-in** from the separated operator UI (`:8011`) so operators complete the **sign-in step** without pasting a worker API key.
- Enforce a **fail-closed email allowlist** exactly: `silverio.bernal@gmail.com`, `ltmoralesp84@gmail.com`.
- Map non-allowlisted Google identities to a clear operator-visible **denied/forbidden** state (no silent “authenticated empty” console).
- Keep **unauthenticated** visitors non-mutating; preserve US-040D session vocabulary (`anonymous` / `authenticated` / `expired` / `forbidden` / blocked messaging).
- Load Google client configuration from **env/secrets only** — no client secrets, refresh tokens, or API keys in frontend source, rendered HTML, logs, or docs.
- Extend the existing injectable **`AuthProvider` / typed client** seam; do **not** rewrite Flow/LinkedIn business screens.
- Add tests + CURRENT-STATE (and related) docs updates for US-097 demonstrated outcomes only.
- **Non-goals (intentionally excluded):** US-098 operator JWT replacing browser API key for console→API calls; worker JWT validation beyond identity/allowlist needs; US-099 Cloudflare Tunnel front-only topology / public hostname / CORS for tunnel exposure; marking US-093–US-095 or US-097 Story accepted; mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; n8n Execute Command; breaking n8n→worker API-key auth (ADR-0001); full BL-029 CI/UAT; unrelated backlog.

### Goals (US-097 acceptance criteria)

1. Operators can start Google (OIDC) sign-in from the separated operator UI and complete authentication without pasting a worker API key for that sign-in step.
2. Access is allowlisted to exactly `silverio.bernal@gmail.com` and `ltmoralesp84@gmail.com` (fail closed for any other authenticated Google identity).
3. Non-allowlisted Google accounts receive a clear operator-visible denied/forbidden outcome (no silent empty console that looks authenticated).
4. Unauthenticated visitors cannot reach mutating console capabilities; anonymous/blocked states remain understandable (US-040D vocabulary).
5. Google client configuration uses env/secrets only (no client secrets, refresh tokens, or API keys in frontend source, rendered HTML, logs, or docs).
6. The outcome is visible and understandable to the intended user.
7. Failures or blocked states are clearly communicated.
8. Existing completed work is not duplicated or unintentionally changed (no Flow/LinkedIn business-screen rewrite; no n8n Execute Command; no `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation; BL-034 separated UI preserved).

### Non-goals / intentionally excluded ACs

| ID | Exclusion |
|----|-----------|
| **US-098** | Operator JWT/session replacing browser API key for console→API; full worker JWT validation beyond identity/allowlist |
| **US-099** | Cloudflare Tunnel front-only public topology; private UI→API hop; public hostname/CORS for tunnel exposure |
| **BL-034 Story accepted** | US-093 / US-094 / US-095 acceptance gates |
| **Publication flag** | Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` |
| **n8n** | Execute Command; making UI an n8n target; breaking API-key machine auth |
| **BL-029** | Full CI/UAT stand-up |

## Capabilities

### New Capabilities

- `operator-console-google-auth`: Google (OIDC) sign-in for the separated Silverman Authority Manager UI, server-side email allowlist enforcement, fail-closed denied/forbidden handling, env-only Google client configuration, and AuthProvider-backed session states for US-097 identity gating (without US-098/US-099 topology or full console→API credential replacement).

### Modified Capabilities

- `linkedin-variant-supervision-console`: Activate Google/OIDC at the injectable `AuthProvider` boundary for the separated UI sign-in path; supersede “Google deferred / API-key paste as the only local sign-in” language where US-097 replaces that sign-in step; preserve typed client and business-screen agnosticism; keep US-040D session vocabulary.
- `separated-operator-ui-capability-regression`: Narrow the prior “MUST NOT implement Google/OIDC” US-095 hold so US-097 Google sign-in/allowlist is allowed; keep other US-095 non-goals (no full BL-029, no publication-flag mutation, no n8n Execute Command).
- `operator-ui-deployment`: Document env var names (placeholders only) required for Google OIDC client configuration on the separated UI / auth path; no secrets in examples.
- `service-permissions-and-exposure`: Update exposure/auth pointers so Google console **identity activation (US-097)** is no longer “out of scope forever”; keep **public** Authority Manager exposure deferred to US-099 / BL-026 least-privilege intent.

## Impact

- **Frontend (`frontend/linkedin-variant-supervision-console/`):** New/extended `AuthProvider` for Google OIDC sign-in; session-state UX for allowlisted vs denied; no calendar/control-center business-screen rewrite.
- **Worker / auth boundary:** Minimal identity/allowlist validation surface required for US-097 (OIDC callback or equivalent + allowlist). Full console→API JWT replacement remains US-098. n8n→worker API-key auth unchanged (ADR-0001).
- **Deploy / env:** Google OIDC client id/secret (and related) via server env/secrets only; example placeholders; CURRENT-STATE capability note after apply (no live public topology claim).
- **Tests:** Vitest (and worker tests if auth endpoints land) for allowlist success/deny, unauthenticated non-mutate, secrets absence, AuthProvider seam.
- **Product docs after apply:** Progress/checklist may mark work started / demonstrated only when outcomes are shown — **do not** mark US-097 Story accepted in this propose.

## Backlog / story mapping

| ID | Role in this change |
|----|---------------------|
| **BL-035** | Parent epic — Authenticate Operator Console With Google |
| **US-097** | **In scope** — Story 1 (this change) |
| **US-098** | Out of scope — deferred |
| **US-099** | Out of scope — deferred |
| **US-040D** | Readiness boundary to extend (injectable auth / session vocabulary) |
| **BL-034** | Separated UI contracts preserved; not Story-accepted by this change |
