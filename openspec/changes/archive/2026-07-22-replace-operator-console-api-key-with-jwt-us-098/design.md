## Context

US-097 delivered Google OIDC + allowlist on the separated Authority Manager (`:8011` → `:8010`) with an HMAC-sealed HttpOnly `silverman_operator_session` cookie and **dual-accept** worker auth (Bearer API key **or** operator session). That bridge lets allowlisted operators supervise without pasting the machine key, but CURRENT-STATE and specs explicitly defer **US-098**: formal operator JWT (issuer/audience/expiry), Google-path console→API without worker API key in the browser, and fail-closed rejection of invalid operator credentials.

Authority: US-098 ACs only (`docs/product/user-stories.md`); BL-035 Story 2 (`docs/product/backlog.md`); progress gates (`docs/product/progress-checklist.md`). Preserve US-097 identity/allowlist and BL-034 AuthProvider / typed-client contracts. Do not invent ACs; do not mark Story accepted in propose/apply docs.

## Goals / Non-Goals

**Goals:**

- Google console path: browser→worker calls send an operator JWT (or equivalent secure session credential) for the signed-in allowlisted identity — **not** the worker API key.
- Worker fail-closed rejects missing/invalid operator credentials (expired, tampered, wrong issuer/audience, email not allowlisted) with a clear auth failure.
- n8n → worker continues API-key auth (ADR-0001); UI is never an n8n target; Google enablement does not break machine clients.
- Preserve injectable `AuthProvider` / typed client; replace paste-API-key on the Google path without rewriting calendar/control-center screens.
- Sign-out / session clear → non-mutating unauthenticated UI; stop sending operator credential.
- Visible outcomes + expired-session guidance without losing unsaved-edit context (US-040D).
- Docs/tests for demonstrated US-098 outcomes only; Story accepted unchecked.

**Non-Goals:**

- US-097 OIDC/allowlist rework; US-099 Cloudflare Tunnel / private hop / public CORS.
- BL-034 Story accepted; mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; n8n Execute Command.
- Full BL-029 CI/UAT; unrelated backlog; inventing ACs absent from product files.

## Decisions

### D1 — Upgrade US-097 session seal to operator JWT claims (HttpOnly cookie transport)

**Choice:** Keep HttpOnly cookie transport (`credentials: "include"`) already used by `GoogleOidcAuthProvider`. Upgrade the sealed cookie value from opaque HMAC payload to a **signed JWT** (HMAC-SHA256) with at least:

| Claim | Purpose |
|-------|---------|
| `email` / `sub` | Allowlisted operator identity |
| `iss` | Fixed issuer (config; e.g. worker-owned operator-auth issuer string) |
| `aud` | Fixed audience for console→worker (config) |
| `exp` / `iat` | Expiry / issued-at |

Worker validation MUST check signature, `exp`, `iss`, `aud`, and allowlist membership — fail closed on any failure. Signing secret stays server-only (`SILVERMAN_OPERATOR_SESSION_SECRET` or dedicated JWT secret env — name at apply; never in SPA/`config.js`).

**Why:** US-098 AC allows “JWT or equivalent”; iss/aud are explicit in the AC. Cookie + JWT satisfies “browser does not send worker API key” without introducing JS-accessible tokens. Smallest cutover from US-097 cookie bridge.

**Alternatives considered:** Authorization Bearer JWT in SPA memory (rejected — XSS can exfiltrate; larger AuthProvider change); opaque server-side session store (rejected — new persistence; out of smallest slice); leave HMAC seal without iss/aud (rejected — AC requires issuer/audience).

### D2 — Worker auth: API key for machines; operator JWT for Google console path

**Choice:** When validating protected worker routes:

1. Accept valid Bearer **API key** → machine/n8n path (unchanged ADR-0001).
2. Else accept valid **operator JWT** (cookie preferred; optional Bearer operator JWT only if clearly distinct from API-key comparison — prefer cookie-only for operator credential to avoid confusing API key with JWT in the same header).
3. Else **401** with clear unauthorized detail (no secrets).

On the **Google-enabled console path**, `GoogleOidcAuthProvider.getRequestHeaders()` MUST continue to return **no** `Authorization` worker API key; requests use `credentials: "include"` only. `MemoryBearerAuthProvider` MAY remain for tests and Google-disabled local fallback — MUST NOT be the default when Google auth is enabled.

**Why:** Removes browser API-key use on the Google path (US-098) while preserving dual * mechanis m* at the worker (API key **or** operator JWT) so n8n is unbroken. This replaces the US-097 “transitional dual-accept bridge” semantics (browser may use either after Google) with JWT-only for that console path.

**Alternatives considered:** Reject all API keys when Google enabled (rejected — breaks n8n); require browser to send both Google identity and API key (rejected — AC forbids API key in browser on this path).

### D3 — Preserve AuthProvider / typed client; no business-screen rewrite

**Choice:** Extend `GoogleOidcAuthProvider` + logout/`clear()` + session restore only. Calendar/control-center keep calling the typed client / store. Expired JWT → worker 401 → existing expired-session vocabulary + unsaved-edit preservation (US-040D).

**Why:** US-098 AC4–7; US-040D / BL-034 seam already proven.

### D4 — Sign-out clears server cookie and local session state

**Choice:** `clear()` / sign-out continues to POST `/auth/logout` (or equivalent), deletes HttpOnly operator cookie, sets UI to anonymous/`canMutate` false, and subsequent typed-client calls do not send the operator credential.

**Why:** US-098 AC5.

### D5 — Configuration and secrets hygiene

**Choice:** Document env **names** + placeholders only for JWT issuer, audience, session/JWT signing secret, and existing Google OIDC vars. No secrets in frontend, docs, logs, or HTTP bodies. Reuse US-097 enablement flag (`SILVERMAN_OPERATOR_GOOGLE_AUTH_ENABLED`) so JWT mint/validate activates with Google console auth.

**Why:** Fail closed; matches project secrets rules.

### D6 — Docs honesty; US-099 still deferred

**Choice:** CURRENT-STATE records US-098 JWT/session console→API cutover on separated LAN UI; explicitly not Cloudflare front-only public topology; not Story accepted. Product checklist: work-started / outcome-demonstrated only when shown; Story accepted unchecked.

**Why:** Precise status language; US-099 non-goal.

### D7 — Preserve publication guards and ADR-0001

**Choice:** No `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation; no n8n Execute Command; no UI-as-n8n-target; US-094 pairing semantics unchanged unless an auth-topology adjustment is explicitly documented (default: no pairing change).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Cookie JWT still dual-accepted with API key at worker → stolen API key usable from browser | Accept for LAN; US-099 keeps API private; AC targets console not shipping API key |
| Iss/aud misconfig locks out operators | Fail closed with clear `/auth/google/status` / blocked messaging; env examples document required keys |
| Session migration breaks existing US-097 cookies | On apply: mint new JWT shape after Google callback; old cookies fail closed → re-auth (document briefly) |
| Confusing API-key Bearer with operator JWT Bearer | Prefer HttpOnly cookie for operator JWT; do not put worker API key in Google provider headers |
| Accidental Story accepted | Propose/tasks forbid marking Story accepted |

## Migration Plan

1. Approve propose → `/opsx-apply` on feature branch (not `main`).
2. Implement JWT mint/validate + AuthProvider holds + tests.
3. Update CURRENT-STATE / env examples / product status lines (demonstrated gates only).
4. `/opsx-verify` → implementation commit → sync → archive (separate approvals).
5. Follow-on: `/opsx-propose` for US-099.

Rollback: revert change; US-097 dual-accept cookie path returns (operators re-auth). No editorial data migration.

## Open Questions

None blocking propose. At apply: confirm issuer/audience string constants and whether signing secret reuses `SILVERMAN_OPERATOR_SESSION_SECRET` or a dedicated env name (prefer reuse unless conflict discovered).
