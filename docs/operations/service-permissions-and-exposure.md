# Service permissions and exposure (US-062 / US-063 / BL-026)

**Scope:** Operator-facing **service permissions and exposure** review — least privilege, open ports, authentication (**US-062**); allowed paths, secrets separation, documented accepted exposure (**US-063**).
**Status:** Procedure **published** (documentation/contract). Live review evidence: [us-062-us-063-service-exposure-review-2026-07-21.md](us-062-us-063-service-exposure-review-2026-07-21.md).
**Authority:** Complements [operational-secrets-permissions-review.md](operational-secrets-permissions-review.md) (US-058 secrets), [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md).
**OpenSpec:** capability `service-permissions-and-exposure` (change `review-service-permissions-exposure-us-062-063`).

Does **not** mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or redesign `local-ai-stack`. Google identity/allowlist (US-097) and operator JWT console→API (US-098) apply on LAN and on the public UI URL when US-099 is active. **US-099** front-only public Authority Manager UI (Cloudflare Tunnel or equivalent → separated UI only, private worker API, private UI→API hop) is **implemented in repo**; live tunnel hostname activation is operator-owned (record in RUNTIME-STATE when live). Publishing the worker API on the public internet remains **out of accepted exposure**.

---

## 1. Accepted exposure (operator policy 2026-07-21; US-099-aligned)

| Surface | Accepted now | Notes |
|---------|--------------|-------|
| Worker HTTP `:8010` | **LAN / private-network only** (`192.168.0.194`) | API-key on non-callback routes; **not** an accepted public Authority Manager API hostname |
| Operator UI `:8011` | **LAN** + **optional public front-only** under US-099 | Separated Authority Manager SPA; same-origin private hop to private worker; **not** an n8n target |
| n8n `:5678` | **LAN only** | Not internet-public for silverman ops |
| Authority Manager / console | **LAN** always; **public UI-only** when US-099 tunnel is live | Via `:8011` / public UI hostname → UI service only. Google OIDC (US-097) + operator JWT (US-098) apply. Worker API stays private |
| LinkedIn OAuth callback | **Exception:** public Cloudflare hostname → worker callback path **only** for LinkedIn reauth | Distinct from Authority Manager UI tunnel; not a general “public API” |
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

- Worker host port `8010` (LAN / private — do **not** publish as public Authority Manager API)
- Operator UI host port `8011` (US-093 separated console; may be Cloudflare front-only under US-099 — UI only)
- n8n host port `5678` (and note if bound to LAN IP vs `0.0.0.0`)
- Do **not** require hardening every Avatares/`local-ai-stack` port in this story; record adjacency only if clearly silverman-related

### Authentication

- Worker: Bearer `SILVERMAN_BLOG_LINKEDIN_API_KEY` on protected routes (n8n / machine clients, ADR-0001); OAuth **callback** is the intentional public exception path for LinkedIn reauth
- Worker (US-097 / US-098): when Google operator auth is enabled, protected routes accept **either** machine API-key Bearer **or** allowlisted operator JWT (HttpOnly `silverman_operator_session` cookie with `iss`/`aud`/`exp`). Google-path browser console MUST NOT send the worker API key; Google client secret / JWT signing stay in worker env only
- n8n: LAN UI; credentials not in git exports (placeholders) — see US-058
- Console: separated UI only (embedded worker console decommissioned); Google OIDC (US-097) + operator JWT (US-098); public UI URL via tunnel only when US-099 is live — worker API stays private

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

Section 1 is the normative inventory. **Public** Authority Manager exposure is **front-only UI** under **US-099** (worker API stays private). Google identity/allowlist is **US-097** and operator JWT console→API is **US-098** (BL-035 Stories 1–2).

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
