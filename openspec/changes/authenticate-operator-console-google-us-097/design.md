## Context

BL-034 separated Silverman Authority Manager onto `:8011` with an injectable `AuthProvider` / typed client (US-040D readiness). Live LAN still uses `MemoryBearerAuthProvider` (worker API-key paste) for sign-in. **BL-035 / US-097** activates Google (OIDC) identity + a fail-closed email allowlist on that separated UI path so only approved Google accounts can authenticate—without public Cloudflare topology (US-099) and without claiming full console→API JWT replacement (US-098).

Authority: US-097 ACs in `docs/product/user-stories.md`; BL-035 Story 1 scope in `docs/product/backlog.md`; progress gates in `docs/product/progress-checklist.md`. Preserve BL-034 contracts in `operator-ui-deployment` / `linkedin-variant-supervision-console` and CURRENT-STATE topology (`:8011` UI → `:8010` API).

## Goals / Non-Goals

**Goals:**

- Google OIDC sign-in from the separated operator UI without worker API-key paste for the **sign-in step**.
- Fail-closed allowlist exactly: `silverio.bernal@gmail.com`, `ltmoralesp84@gmail.com`.
- Non-allowlisted Google identities → clear `forbidden` / denied (no silent authenticated-empty console).
- Unauthenticated → non-mutating; US-040D vocabulary (`anonymous`, `authenticated`, `expired`, `forbidden`, blocked).
- Google client secrets / refresh tokens / API keys via env/secrets only — never in frontend source, rendered HTML, logs, or docs.
- Extend `AuthProvider` seam; no Flow/LinkedIn business-screen rewrite.
- Tests + CURRENT-STATE (capability/topology pointers) for demonstrated US-097 outcomes only; do not mark Story accepted.

**Non-Goals:**

- US-098: operator JWT replacing browser API key for console→API; full issuer/audience JWT policy beyond identity/allowlist needs.
- US-099: Cloudflare Tunnel front-only public topology; private UI→API hop; public hostname/CORS for tunnel exposure.
- BL-034 Story accepted for US-093/US-094/US-095.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; n8n Execute Command; making UI an n8n target; breaking n8n→worker API-key auth (ADR-0001).
- Full BL-029 CI/UAT stand-up; unrelated backlog.

## Decisions

### D1 — Extend injectable `AuthProvider`; do not rewrite business screens

**Choice:** Add a Google OIDC-capable `AuthProvider` implementation (name TBD at apply) that satisfies `signIn()`, `hasCredential()`, `canMutate()`, `clear()`, `getRequestHeaders()` / `getCredentialsMode()`. Wire it as the default separated-UI sign-in path when Google auth is configured/enabled. Keep calendar/control-center components on `useSupervisionStore` / typed client only.

**Why:** US-040D / US-093 ACs already require a swappable provider; US-097 AC requires no business-screen rewrite.

**Alternatives considered:** Rewrite AppShell/modals to call Google SDK directly (rejected — breaks seam); keep paste-only and add a parallel login page outside AuthProvider (rejected — duplicates session vocabulary).

### D2 — Server-side OIDC code exchange + allowlist (fail closed)

**Choice:** Browser starts Google OIDC (authorization code + PKCE preferred). **Token/code exchange and email allowlist enforcement run server-side** on a minimal auth surface owned by the worker (preferred) or an equally fail-closed UI-adjacent BFF that is not an n8n target. Client secret and any refresh tokens stay in env/secrets only.

Allowlist is exactly the two US-097 emails (normative constant and/or env that MUST resolve to that closed set). Any other Google identity → denied/`forbidden` with operator-visible copy. Missing/misconfigured Google env when Google sign-in is the active path → fail closed (clear blocked messaging), not open anonymous console.

**Why:** Client-only allowlist is forgeable; ACs require fail-closed allowlist and secrets-out-of-frontend.

**Alternatives considered:** Frontend-only Google Identity Services + client email check (rejected — not fail closed); full IdP/user-management product (rejected — out of scope).

### D3 — Session states map to US-040D vocabulary

**Choice:**

| Outcome | Session state | `canMutate` |
|---------|---------------|-------------|
| No Google session | `anonymous` | false |
| Allowlisted Google identity established | `authenticated` | true (mutable operator) |
| Google identity authenticated but not allowlisted | `forbidden` | false |
| Prior session invalidated (401 / cleared) | `expired` (or return to anonymous after clear) | false |

Non-allowlisted success at Google IdP MUST NOT look like a normal authenticated empty console.

**Why:** Matches US-097 ACs 3–4 and US-040D vocabulary already in AppShell/banners.

### D4 — US-097 vs US-098 auth boundary (smallest coherent bridge)

**Choice:**

- **US-097 owns:** Google sign-in UX, OIDC exchange, allowlist, AuthProvider session identity, operator-visible denied/anonymous states, env-only Google config, minimal worker/BFF endpoints needed for that identity path.
- **Transitional bridge (in scope for US-097 only as needed):** After allowlisted Google identity, AuthProvider holds an **operator identity session** (HttpOnly cookie with `credentials: "include"` preferred, or opaque session token via headers) so the sign-in step needs no API-key paste. Worker MAY accept that identity session **in addition to** existing API-key auth for browser console calls so LAN operators are not forced to paste the machine key after Google sign-in. n8n continues API-key only.
- **US-098 owns:** Formal operator JWT (issuer/audience/expiry), **removing** browser use of the worker API key on the Google console path, and tightening worker validation beyond identity/allowlist.

**Why:** AC1 forbids API-key paste for the sign-in step; deferring all worker acceptance to US-098 would leave allowlisted operators authenticated in UI but unable to exercise the console without paste—confusing vs “mutating capabilities” gating. Dual-accept (API key **or** operator identity session) keeps ADR-0001 machine path intact while enabling Story 1.

**Alternatives considered:** UI-only Google gate with MemoryBearer still required for every mutation (weaker AC1 experience); full US-098 JWT cutover in this change (rejected — explicit non-goal).

### D5 — Configuration via env/secrets; public vs secret vars

**Choice:** Document env var **names** only (placeholders in `deploy/server/` examples). Typical split:

| Kind | Examples (names illustrative at apply) | Placement |
|------|----------------------------------------|-----------|
| Non-secret / public-safe | Google OAuth client ID, redirect URI, enable flag | UI runtime config and/or worker env |
| Secret | Google OAuth client secret, any session signing key | Worker/BFF secrets only — never `config.js` / SPA bundle |

Frontend MUST NOT embed client secrets, refresh tokens, worker API keys, or session signing material. Logs/errors MUST NOT print secrets.

**Why:** US-097 AC5; aligns with existing US-093 runtime `config.js` pattern for non-secrets.

### D6 — LAN activation only; public URL stays deferred

**Choice:** Implement and document Google sign-in for the **existing LAN** separated UI origin (`:8011`). Redirect URIs target that LAN (or local-dev) origin. Do **not** publish Cloudflare Tunnel, public hostname, or tunnel CORS in this change (US-099).

**Why:** US-097 is identity Story 1; US-099 owns front-only public topology.

### D7 — Preserve BL-034 / ADR-0001 / publication guards

**Choice:** No change to UI/API ports contract beyond auth; no embedded-console revival; n8n→worker HTTP only; no Execute Command; no `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation; no Flow A/B business rewrites.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Dual-auth bridge blurs into US-098 | Spec/tasks label bridge explicitly; US-098 change owns JWT-only console path and “no API key in browser” enforcement |
| Google redirect URI mismatch on LAN | Document exact redirect URI env; fail closed with clear config error |
| Allowlist drift | Normative emails fixed in specs + product ACs; tests assert exact set |
| Accidental secret leakage in SPA | Secrets audit tests; client secret only server-side |
| Treating US-097 as Story accepted after code | Product checklist updates only for demonstrated gates; Story accepted remains operator gate |

## Migration Plan

1. Approve proposal → `/opsx-apply` on a feature branch (not `main`).
2. Implement AuthProvider + server allowlist/OIDC + tests.
3. Document env names; update CURRENT-STATE capability note (Google identity on LAN UI — not public topology, not US-098 complete).
4. `/opsx-verify` → commit → sync → archive (separate approvals).
5. Follow-on proposes: US-098, then US-099.

## Open Questions

None blocking propose. At apply time, confirm Google Cloud OAuth client redirect URI(s) for LAN `:8011` with the operator (operational secret/setup outside committed docs).
