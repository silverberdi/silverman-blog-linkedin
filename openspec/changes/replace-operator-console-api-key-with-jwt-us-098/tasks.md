## 1. Baseline and scope guardrails

- [x] 1.1 Confirm US-098 ACs only (user-stories / backlog BL-035 Story 2 / progress-checklist); do not invent ACs; do not mark Story accepted
- [x] 1.2 Confirm US-097 Google OIDC + allowlist + AuthProvider baseline remains intact (verify hold only — no OIDC/allowlist rework)
- [x] 1.3 Confirm non-goals: US-099 tunnel/topology; BL-034 Story accepted; publication-flag mutation; n8n Execute Command; UI as n8n target; full BL-029

## 2. Worker operator JWT mint and validation

- [x] 2.1 Upgrade operator session credential to signed JWT (HMAC) with email/sub, iss, aud, exp/iat; keep HttpOnly cookie transport preferred
- [x] 2.2 Configure issuer/audience (env or fixed constants) + signing secret server-only; fail closed when Google auth enabled but JWT config incomplete
- [x] 2.3 Mint operator JWT after allowlisted Google OIDC callback; refuse mint for non-allowlisted emails
- [x] 2.4 Validate operator JWT on protected routes: signature, exp, iss, aud, allowlist — clear 401 on failure (no secrets in bodies/logs)
- [x] 2.5 Keep n8n → worker Bearer API-key path working (ADR-0001); Google-path browser must not rely on sending the worker API key
- [x] 2.6 Ensure `/auth/logout` clears HttpOnly operator cookie; subsequent requests without valid JWT/API key fail closed

## 3. Separated UI AuthProvider (Google path)

- [x] 3.1 Ensure `GoogleOidcAuthProvider` / typed client on Google path sends operator credential via `credentials: "include"` and never puts worker API key in Authorization headers
- [x] 3.2 Keep `MemoryBearerAuthProvider` for tests / Google-disabled local fallback only — not default when Google auth enabled
- [x] 3.3 Sign-out / `clear()` returns anonymous non-mutating state and stops sending operator credential
- [x] 3.4 Map expired/invalid operator credential (HTTP 401) to expired-session guidance without discarding unsaved schedule-editor draft (US-040D hold)
- [x] 3.5 Do not rewrite calendar/control-center business screens; AuthProvider / store seam only

## 4. Tests

- [x] 4.1 Pytest: JWT mint for allowlisted identity; reject expired, tampered, wrong iss, wrong aud, non-allowlisted email
- [x] 4.2 Pytest: n8n/machine API-key auth still succeeds when Google console auth is enabled
- [x] 4.3 Pytest: protected route without API key and without valid operator JWT returns clear 401
- [x] 4.4 Vitest US-098: Google path does not send worker API key; operator credential used; clear-session stops credential; expired-session messaging hold
- [x] 4.5 Re-run applicable US-093 / US-094 / US-095 / US-097 Vitest holds; keep green without claiming US-099 or Story accepted
- [x] 4.6 Secrets audit: no JWT signing secrets, API keys, or client secrets in frontend source/built assets/docs examples

## 5. Docs and product status (demonstrated only)

- [x] 5.1 Update `docs/CURRENT-STATE.md`: US-098 operator JWT/session console→API on separated LAN UI; not US-099; not Story accepted
- [x] 5.2 Update deploy env examples / ops pointers for issuer/audience/signing secret **names** with placeholders only
- [x] 5.3 Align `docs/operations/service-permissions-and-exposure.md` auth expectations (console JWT vs machine API key) without public-exposure claim
- [x] 5.4 Update `docs/product/user-stories.md` / `progress-checklist.md` / `backlog.md` status lines only for US-098 gates actually demonstrated (e.g. work started / outcome demonstrated); leave Story accepted and acceptance-criteria-validated unchecked
- [x] 5.5 `git diff --check` clean on touched paths; no secrets staged

## 6. Business validation

- [x] 6.1 Trace each US-098 AC to a test or documented evidence artifact; record any gap without inventing ACs
- [x] 6.2 Confirm n8n API-key path and Google console JWT path are both demonstrated; UI is not an n8n target
- [x] 6.3 Confirm Story accepted remains unchecked for US-098 / BL-035; US-099 still deferred
