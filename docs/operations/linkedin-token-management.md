# LinkedIn token management (US-060 / US-061 / BL-025)

**Scope:** Operator-facing LinkedIn OAuth **token lifecycle** — secure storage, renewal/expiration, revocation (**US-060**); invalid-token detection, development vs production separation, recovery (**US-061**).
**Status:** Procedure **published** (documentation/contract). Ratifies existing worker behavior under `linkedin-oauth-token-lifecycle`. Operator-accepted with BL-025 closure 2026-07-21.
**Authority:** Complements [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md), [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md), and canonical spec `openspec/specs/linkedin-oauth-token-lifecycle/`.
**OpenSpec:** capability `linkedin-token-management` (change `formalize-linkedin-token-management-us-060-061`).

This document does **not** mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, does **not** require inventing an invalid token when status is healthy, and does **not** change Flow A/B pipelines. Setup steps for the LinkedIn Developer App remain in prerequisites; this SoT owns the **management contract**.

---

## 1. What this is (and is not)

| This document | MUST NOT mean |
|---------------|---------------|
| Operator contract for LinkedIn tokens (store / renew / revoke / detect / recover) | A rewrite of publish-due, queue, or n8n workflows |
| Ratification of existing OAuth endpoints + token store | A secrets vault or second LinkedIn app (optional later) |
| Explicit callout when refresh token is missing | “Tokens are invalid today” — healthy access token may still exist |
| BL-025 closed when stories accepted | Forced reauth or client-secret rotation on apply |

---

## 2. Outcome vocabulary (no secret values)

| State | Meaning |
|-------|---------|
| `healthy` | Token store configured; token present; access token usable (or refresh succeeds); publication may still be enablement-gated separately |
| `action_required` | Reauthorization or operator remediation needed (e.g. missing/expired refresh, revoked grant) — stable codes such as `linkedin_oauth_reauthorization_required` |
| `blocked` | Cannot complete a check (no server access, status endpoint unavailable) — record non-secret reason |

`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` is an **enablement** block, not the same as an invalid token.

---

## 3. Secure storage (US-060)

| Item | Expected location / form | Rules |
|------|--------------------------|-------|
| Client id / secret | Server-local `.env`: `SILVERMAN_LINKEDIN_CLIENT_ID`, `SILVERMAN_LINKEDIN_CLIENT_SECRET` | Never commit; never in HTTP responses/logs |
| Redirect URI | `SILVERMAN_LINKEDIN_REDIRECT_URI` (prod: `https://api.silverman.pro/linkedin/oauth/callback`) | Registered on LinkedIn Developer App |
| Token store | `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` → host `…/secrets/linkedin-oauth/` (dir **`700`**), files **`600`** | Outside editorial git mount; atomic writes |
| Fallback env token | `SILVERMAN_LINKEDIN_ACCESS_TOKEN` + `SILVERMAN_LINKEDIN_MEMBER_URN` | **Fallback only** when store empty — not primary production path |

Diagnostics (`GET /linkedin/oauth/status`) MUST report metadata only — never `access_token`, `refresh_token`, or `client_secret`.

---

## 4. Renewal and expiration (US-060)

1. Before real LinkedIn API publish, the token provider resolves a valid access token.
2. If access token is within refresh skew of expiry **and** a refresh token exists → refresh grant → update store → continue.
3. If refresh token is **missing**, expired, revoked, or refresh fails → **`action_required`** (reauthorization). Do **not** call LinkedIn publication APIs.
4. **Known production gap (recorded 2026-07-21):** token store may show `token_present: true` with **`refresh_token_present: false`**. While the access token remains unexpired, LinkedIn can work; **when access expires, operator MUST reauthorize** (section 8). This gap alone does not mean “invalid today.”

---

## 5. Revocation (US-060)

| Action | How |
|--------|-----|
| Stop using current grant | Clear or replace token-store files on the server (modes `600`); do not commit contents |
| Revoke at LinkedIn | Remove app access from LinkedIn account / Developer portal as needed |
| Restore | Run recovery (section 8) — authorize → callback → status |

Revocation MUST NOT paste token values into git, chat, or docs.

---

## 6. Detect invalid tokens (US-061)

| Signal | Where | Operator reading |
|--------|-------|------------------|
| Status metadata | `GET /linkedin/oauth/status` (API key) | `token_present`, `access_token_expires_at`, `refresh_token_present`, scopes, `member_urn`, `publication_enabled`, errors — **no cleartext tokens** |
| Provider fail-closed | Publish / token provider | `action_required` / `linkedin_oauth_reauthorization_required` (and related token invalid/expired codes on publication) |
| Healthy now | Same status | Valid for Story accepted documentation — detection paths remain defined for when status degrades |

**MUST NOT:** Deliberately corrupt a working token solely to “prove” US-061.

---

## 7. Development vs production credentials (US-061)

| Environment | Expectation |
|-------------|-------------|
| **Production** (`192.168.0.194` worker) | Server `.env` + host `secrets/linkedin-oauth/` mounts; Cloudflare callback URL |
| **Local / development** | Separate `.env` and local token-store path (or placeholders); do not copy production token files into the repo or laptop casually |
| **LinkedIn Developer App** | One production app is acceptable for this solo deployment; a second “dev” app is **optional**, not required by this procedure |

Never commit real client secrets or token stores. Example files use placeholders only.

---

## 8. Recovery runbook (US-061)

1. Confirm enablement intent separately (`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`) — do not flip it casually.
2. `GET /linkedin/oauth/status` — note metadata only (`action_required`? refresh present?).
3. `GET /linkedin/oauth/authorize` (API key) → open `authorization_url` → LinkedIn consent.
4. Complete `GET /linkedin/oauth/callback` success page (no token values shown).
5. Re-check `/linkedin/oauth/status` — `token_present`, expiry, preferably `refresh_token_present: true` after a full grant.
6. Optional: dry-run publish-due (`dry_run: true`) — must not refresh/publish as real when dry-run per existing contracts.
7. If still `action_required` → `blocked` or escalate with non-secret error codes only.

---

## 9. Related documents

- Prerequisites / app setup: [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md)
- Secrets cadence (client secret / token store rows): [operational-secrets-ownership-cadence.md](operational-secrets-ownership-cadence.md)
- Product: [backlog.md](../product/backlog.md) BL-025, [user-stories.md](../product/user-stories.md) US-060 / US-061
