# Service permissions and exposure (US-062 / US-063 / BL-026)

**Scope:** Operator-facing **service permissions and exposure** review — least privilege, open ports, authentication (**US-062**); allowed paths, secrets separation, documented accepted exposure (**US-063**).
**Status:** Procedure **published** (documentation/contract). Live review evidence: [us-062-us-063-service-exposure-review-2026-07-21.md](us-062-us-063-service-exposure-review-2026-07-21.md).
**Authority:** Complements [operational-secrets-permissions-review.md](operational-secrets-permissions-review.md) (US-058 secrets), [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md).
**OpenSpec:** capability `service-permissions-and-exposure` (change `review-service-permissions-exposure-us-062-063`).

Does **not** expose Authority Manager publicly (US-099 deferred), mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, or redesign `local-ai-stack`. Google identity/allowlist on the **LAN** separated UI is activated under **BL-035 / US-097** when configured; that is **not** public console exposure.

---

## 1. Accepted exposure (operator policy 2026-07-21)

| Surface | Accepted now | Notes |
|---------|--------------|-------|
| Worker HTTP `:8010` | **LAN only** (`192.168.0.194`) | API-key on non-callback routes |
| Operator UI `:8011` | **LAN only** (`192.168.0.194`) | US-093 separated Authority Manager SPA; browser client → worker API; **not** public console exposure |
| n8n `:5678` | **LAN only** | Not internet-public for silverman ops |
| Authority Manager / console | **LAN only** | Via `:8011` (supported; worker-embedded console decommissioned US-096). Google OIDC identity/allowlist may be active on LAN under **US-097**; **public** URL / Cloudflare front-only = **US-099** (deferred) |
| LinkedIn OAuth callback | **Exception:** public Cloudflare hostname → worker callback path **only** for LinkedIn reauth | Not a general “public API”; other worker routes stay LAN |
| Comfy Cloud / DeepSeek | **Outbound API clients** (keys in `.env`) | No inbound ComfyUI port required on this host |
| Public blog checkout mount | Worker mount to Pages checkout | Public site is the blog; not the worker control plane |
| Secrets | Per **US-058** (`.env` `600`, `secrets/` `700`, files `600`) | Ratified here — do not duplicate full US-058 checklist |

---

## 2. Outcome vocabulary

| Outcome | Meaning |
|---------|---------|
| `blocked` | Check cannot complete (no server access) |
| `confirmed clean` | Matches accepted exposure / least privilege |
| `finding — remediation required` | Unexpected listen, world-readable secret path, missing auth — path/port **names** only |

---

## 3. US-062 — Least privilege, ports, authentication

### Ports (checklist)

Review listening sockets relevant to silverman ops on the deploy host:

- Worker host port `8010`
- Operator UI host port `8011` (US-093 separated console; LAN only — do **not** claim public console exposure)
- n8n host port `5678` (and note if bound to LAN IP vs `0.0.0.0`)
- Do **not** require hardening every Avatares/`local-ai-stack` port in this story; record adjacency only if clearly silverman-related

### Authentication

- Worker: Bearer `SILVERMAN_BLOG_LINKEDIN_API_KEY` on protected routes (n8n / machine clients, ADR-0001); OAuth **callback** is the intentional public exception path for LinkedIn reauth
- Worker (US-097): when Google operator auth is enabled, dual-accept allowlisted HttpOnly operator session **or** API key for browser console routes; Google client secret / session signing stay in worker env only
- n8n: LAN UI; credentials not in git exports (placeholders) — see US-058
- Console: LAN `:8011` separated UI only (embedded worker console decommissioned); Google OIDC identity may be enabled on LAN (US-097); not internet-public until US-099

### Least privilege (services)

- Docker mounts: secrets narrow; editorial/public separate (confirm live)
- No world-readable `.env` / token stores (US-058)

---

## 4. US-063 — Allowed paths, secrets, accepted exposure

### Allowed path / mount classes

| Class | Typical host path | Role |
|-------|-------------------|------|
| Worker deploy | `/home/silverman/silverman-blog-linkedin-worker` | Image/build; `.env` server-local |
| Secrets | `…/secrets/` (+ `linkedin-oauth/`, deploy-key files) | Tokens / SSH — modes per US-058 |
| Editorial data | worker `data/silverman-blog-linkedin` or shared editorial mount | Campaigns/posts — not a secret store |
| Public blog | `/home/silverman/silverberdi.github.io` → `/public-blog` | Pages checkout |
| n8n imports | `/home/silverman/n8n-imports` | Placeholder sources only (no live keys) |

### Separate secrets

Ratify US-058: real values only in server `.env` / secrets mounts; never commit; n8n exports use placeholders.

### Document accepted exposure

Section 1 is the normative inventory. **Public** console exposure requires **US-099** (separate OpenSpec). Google LAN identity/allowlist is **US-097** (BL-035 Story 1) and does not by itself make Authority Manager internet-public.

---

## 5. How to run the live review

1. From LAN, inspect listens (`ss`/`netstat`) for `8010`, `5678`, unexpected silverman-related publics.
2. Spot-check worker `/health` (no secrets); unauthenticated protected route → 401.
3. Confirm mount types (secrets files vs dirs; editorial/public present).
4. Record evidence with vocabulary above — no secret values.
5. Remediate only clear safe findings; do not open new public surfaces.

---

## 6. Related

- Secrets: [operational-secrets-permissions-review.md](operational-secrets-permissions-review.md)
- LinkedIn tokens: [linkedin-token-management.md](linkedin-token-management.md)
- OAuth setup: [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md)
