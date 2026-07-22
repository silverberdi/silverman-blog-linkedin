## 1. Branch and baseline

- [x] 1.1 Create/switch to `feat/us-097-authenticate-operator-console-google` (or equivalent); do not implement on `main`
- [x] 1.2 Confirm BL-034 separated UI baseline (`:8011` ↔ `:8010`, pairing, CORS, injectable `AuthProvider`) — verify hold only; no US-093/US-094/US-095 redesign; no US-098/US-099 work in this change

## 2. Server: Google OIDC + allowlist identity path

- [x] 2.1 Add fail-closed email allowlist exactly `silverio.bernal@gmail.com` and `ltmoralesp84@gmail.com` (server-side; case-normalized compare OK)
- [x] 2.2 Implement minimal OIDC start + callback (or equivalent) on worker/BFF: authorization-code exchange with PKCE preferred; Google client secret and session signing material from env/secrets only
- [x] 2.3 On allowlisted success, establish operator identity session usable by AuthProvider (HttpOnly cookie preferred or opaque session token); on non-allowlisted Google identity, return clear denied/forbidden (no authenticated-empty session)
- [x] 2.4 If needed for LAN console use without API-key paste after Google sign-in, dual-accept API key **or** operator identity session on browser console routes; keep n8n→worker API-key path unchanged (ADR-0001); do not implement US-098 JWT-only cutover

## 3. Frontend: Google AuthProvider + session UX

- [x] 3.1 Implement Google OIDC `AuthProvider` behind existing injectable seam; `signIn()` must not prompt for worker API-key paste on the Google-enabled path
- [x] 3.2 Wire default separated-UI auth to Google provider when configured/enabled; preserve `MemoryBearerAuthProvider` (or equivalent) for tests/explicit local fallback only
- [x] 3.3 Map session states to US-040D vocabulary: anonymous / authenticated (allowlisted) / forbidden (non-allowlisted) / expired; ensure forbidden is operator-visible and distinct from authenticated empty console
- [x] 3.4 Keep `canMutate` false for anonymous and forbidden; do not rewrite Flow/LinkedIn calendar/control-center business screens

## 4. Configuration and secrets hygiene

- [x] 4.1 Add deploy/server env example entries for Google OIDC keys (client ID, client secret, redirect URI, enablement, session signing as applicable) with non-secret placeholders only
- [x] 4.2 Ensure client secrets / refresh tokens / API keys / session secrets never appear in frontend source, rendered HTML, bundled assets, logs, or docs
- [x] 4.3 Fail closed with clear operator messaging when Google auth is enabled but required env is missing/invalid

## 5. Tests

- [x] 5.1 Vitest: allowlisted Google sign-in establishes authenticated + `canMutate` without API-key paste; clear session returns non-mutating
- [x] 5.2 Vitest: non-allowlisted Google identity → forbidden/denied, not silent authenticated empty console; anonymous cannot mutate
- [x] 5.3 Worker/BFF tests: allowlist exact set; non-allowlisted denied; secrets absent from responses; n8n API-key path still valid
- [x] 5.4 Secrets audit scan on new/modified frontend artifacts (no client secrets / API keys / refresh tokens)
- [x] 5.5 Re-run applicable US-093/US-094/US-095 Vitest holds; keep green without claiming US-098/US-099

## 6. Docs and product progress (no Story accepted)

- [x] 6.1 Update `docs/CURRENT-STATE.md`: Google identity/allowlist on separated LAN UI (US-097); explicitly not public tunnel (US-099), not JWT-only console→API (US-098), not Story accepted
- [x] 6.2 Align `docs/operations/service-permissions-and-exposure.md` and light deploy pointers: Google LAN identity vs public exposure deferred
- [x] 6.3 Update `docs/RUNTIME-STATE.md` only if live flags/topology for Google auth change on a deployed stack
- [x] 6.4 Update `docs/product/user-stories.md` / `progress-checklist.md` / `backlog.md` status lines only for US-097 ACs actually demonstrated (e.g. work started / outcome demonstrated); leave Story accepted unchecked; do not mark US-098/US-099 or BL-034 Story accepted

## 7. Verification and business validation

- [x] 7.1 Run targeted pytest + Vitest for touched modules; fix warnings attributable to this change; `git diff --check` clean; secrets audit on new/modified files
- [x] 7.2 Business validation against US-097 ACs only:
  1. Google OIDC sign-in without API-key paste for sign-in step
  2. Allowlist exactly the two emails (fail closed)
  3. Non-allowlisted → clear forbidden/denied
  4. Unauthenticated cannot mutate; anonymous/blocked understandable
  5. Env/secrets only for Google client config
  6–7. Outcomes and failures visible/clear
  8. No business-screen rewrite; no n8n Execute Command; no publication-flag mutation; BL-034 separated UI preserved
  — Record demonstrated vs still-pending operator gates; **do not** mark Story accepted
