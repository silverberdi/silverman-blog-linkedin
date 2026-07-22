## Why

US-097 established Google OIDC identity + allowlist on the separated Authority Manager UI with a transitional dual-accept bridge (worker API key **or** operator session cookie). Public-ready console use still must not put the machine credential used by n8n in the browser. **BL-035 / US-098** replaces that bridge on the Google console path with an operator JWT (or equivalent secure session credential) that the worker validates fail-closed—without rewriting business screens or breaking ADR-0001 machine auth.

## What Changes

- On the Google-authenticated console path, browser→worker calls stop sending the worker API key and instead send an operator JWT (or equivalent secure session credential) issued/validated for the signed-in allowlisted identity.
- Worker rejects console requests lacking a valid operator credential (expired, tampered, wrong issuer/audience, or email not allowlisted) — fail closed with a clear auth failure.
- Machine clients (n8n → worker HTTP) keep existing API-key auth (ADR-0001); Google console auth enablement does not break that path or make the UI an n8n target.
- Injectable `AuthProvider` / typed client boundary (US-040D / BL-034) is preserved; Google/JWT replaces paste-API-key as the Google-path provider without rewriting calendar/control-center screens.
- Operator sign-out / session clear returns the UI to a non-mutating unauthenticated state and stops sending the operator credential.
- Visible outcomes and clear failure/blocked states (including expired-session guidance without losing unsaved-edit context where US-040D already requires it).
- Docs/tests cover demonstrated US-098 outcomes only; **Story accepted remains unchecked**.
- **BREAKING (console Google path only):** When Google console auth is enabled, browser console→API auth is operator-credential-only; remaining dual-accept “API key from browser after Google sign-in” is removed. n8n API-key path is unchanged.

### Goals

- Satisfy **US-098** acceptance criteria in `docs/product/user-stories.md` (BL-035 Story 2 only).
- Tighten/replace the US-097 dual-accept bridge toward operator JWT-only on the Google console path while keeping n8n API-key auth.
- Preserve separated UI + AuthProvider seam; fail closed; no secrets in code, docs, logs, or responses.

### Non-goals (intentionally excluded)

| Item | Reason |
|------|--------|
| **US-097** Google OIDC identity/allowlist rework | Already implemented; preserve |
| **US-099** Cloudflare Tunnel front-only public topology / private UI→API hop / public hostname CORS | Next story |
| BL-034 Story accepted for US-093/US-094/US-095 | Separate operator gate |
| Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | Out of scope |
| n8n Execute Command; making UI an n8n target | ADR-0001 |
| Full BL-029 CI/UAT stand-up | Unrelated |
| Marking US-098 / BL-035 Story accepted | Operator gate after demonstrated ACs |
| Unrelated backlog | Scope discipline |

### Acceptance criteria addressed (US-098)

All US-098 ACs in `docs/product/user-stories.md` are in scope for this change’s demonstrated outcomes (browser no worker API key; worker fail-closed JWT/session validation; n8n API-key retained; AuthProvider boundary; sign-out; visible/failure states; no unintended duplication of completed work).

### Acceptance criteria intentionally excluded

- US-097 ACs (already demonstrated; not reworked here).
- US-099 ACs (public topology).
- Product “Story accepted” / checklist acceptance-validated gates (remain operator-owned).

## Capabilities

### New Capabilities

- None. US-098 advances the existing Google console auth capability rather than introducing a separate capability name.

### Modified Capabilities

- `operator-console-google-auth`: Replace dual-accept bridge language with operator JWT (or equivalent) console→API auth on the Google path; issuer/audience/expiry/allowlist fail-closed validation; sign-out clears credential; n8n API-key path preserved.
- `linkedin-variant-supervision-console`: Require Google-path AuthProvider to send operator credential (not worker API key); preserve typed client / session vocabulary including expired-session unsaved-edit holds; update deferred-US-098 wording.
- `separated-operator-ui-capability-regression`: Extend regression holds for JWT/session console auth without claiming US-099 or Story accepted.
- `operator-ui-deployment`: Document JWT/session console→API activation on separated LAN UI without claiming Cloudflare public topology.
- `service-permissions-and-exposure`: Update authentication expectations for operator JWT/session on console vs API-key for machine clients; still no public Authority Manager exposure (US-099).

## Impact

- **Worker / auth:** Upgrade operator session credential to JWT (or equivalent with issuer/audience/expiry) validation; Google console path accepts operator credential only; n8n continues Bearer API key (`src/silverman_blog_linkedin/auth.py`, `operator_google_auth.py`, related routes).
- **Separated UI:** `GoogleOidcAuthProvider` / AuthProvider wiring — no Authorization: worker API key on Google path; credentials mode / logout clear; calendar/control-center untouched beyond auth seam.
- **Tests:** Vitest US-098 holds + pytest JWT/session validation (expired/tampered/wrong iss/aud/non-allowlisted) + n8n API-key regression; keep US-093/094/095 holds green.
- **Docs:** CURRENT-STATE capability note for US-098 JWT cutover (not US-099, not Story accepted); env examples name signing/issuer keys with placeholders only.
- **Product pointers:** Status lines for US-098 work-started / outcome-demonstrated only when actually shown; Story accepted unchecked.
- **Systems unchanged:** LinkedIn publication enablement; n8n orchestration model; Cloudflare public topology; Flow A/B business screens.
