# US-062 / US-063 service permissions and exposure review — evidence 2026-07-21

**BANNER — no secret values in this file.** Port names, path classes, permission modes, and auth outcomes only.

**Normative procedure:** [service-permissions-and-exposure.md](service-permissions-and-exposure.md).

| Field | Value |
|-------|-------|
| Review date (UTC) | `2026-07-21T18:39:50Z` (server host / `192.168.0.194`) |
| Recorded by | Operator-assisted agent session (SSH secret-safe audit) |
| Scope | BL-026 / US-062 + US-063 least privilege, ports, auth, paths, accepted exposure |
| Overall outcome | `confirmed clean` (matches accepted exposure policy; OAuth exception option 1) |

**Story accepted:** operator-accepted 2026-07-21 (US-062 + US-063); **BL-026 closed**.

**Not performed:** Public Authority Manager / console exposure; Google/OIDC activation; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation; secret rotation; reopening BL-024/025.

**Operator policy (accepted exposure):** Worker `:8010`, n8n `:5678`, Authority Manager = **LAN only**. LinkedIn OAuth callback via Cloudflare public hostname = **exception only for LinkedIn reauth**. Comfy Cloud + DeepSeek = outbound API clients. Secrets = US-058 ratified.

---

## US-062 — Least privilege, ports, authentication

| ID | Check | Outcome | Notes (no secrets) |
|----|-------|---------|---------------------|
| E1 | Worker listen `:8010` | `confirmed clean` | Host listens `0.0.0.0:8010` and `[::]:8010` (Docker publish). Accepted as **LAN-only** control plane; not instructed as internet-public API. Public reach limited to Cloudflare tunnel for OAuth callback exception. |
| E2 | n8n listen `:5678` | `confirmed clean` | Bound to `192.168.0.194:5678` (LAN IP). Matches LAN-only policy. |
| E3 | Worker authentication | `confirmed clean` | `GET /health` → 200; `health_status=healthy`; no suspicious secret patterns in body. `GET /linkedin/oauth/status` without auth → **401** (fail-closed on protected route). |
| E4 | Cloudflare tunnel (OAuth exception) | `confirmed clean` | `cloudflared tunnel` process present on host — supports accepted **option 1** (public callback hostname for LinkedIn reauth only). Not treated as general public worker API. |
| E5 | Adjacent listens (context) | `confirmed clean` (adjacency note) | Other host listens observed (`22`, `5432`, `9000`, `9001`, `9443`, Samba, etc.) are **not** silverman control-plane requirements for this story; no remediation in BL-026. No inbound ComfyUI port required (Comfy Cloud outbound). |

---

## US-063 — Allowed paths, secrets separation, accepted exposure

| ID | Check | Outcome | Notes |
|----|-------|---------|-------|
| P1 | Docker mounts | `confirmed clean` | Narrow mounts: deploy-key + known_hosts `:ro` files; `linkedin-oauth` RW; editorial → `/data/...`; public blog → `/public-blog`. |
| P2 | Secrets path classes | `confirmed clean` | Host `.env` mode `600`. `secrets/` `700`; oauth dir `700`; token/state + deploy-key + known_hosts files `600`. Ratifies US-058. |
| P3 | n8n-imports | `confirmed clean` | Only `*.source.json` placeholders remain (5 files); no live-looking dumps. |
| P4 | Accepted exposure documented | `confirmed clean` | SoT §1 records LAN surfaces + OAuth exception option 1 + outbound providers + US-058 secrets. Console public + Google auth = future / out of scope. |

---

## Findings / remediation

| # | Finding | Related ID | Status |
|---|---------|------------|--------|
| — | None requiring remediation for BL-026 acceptance | — | N/A |

**Note:** Worker bind `0.0.0.0:8010` is documented as LAN-accepted Docker publish, not a finding against policy, provided internet exposure remains the Cloudflare OAuth-callback exception only.

---

## Operator attestation

| Statement | Yes / No / N/A |
|-----------|----------------|
| No secret values were written into this evidence file | Yes |
| No public console / Google auth activation performed | Yes |
| No `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation | Yes |
| Accepted exposure includes OAuth exception **option 1** | Yes |
| Story accepted for US-062 + US-063 / BL-026 closed is an explicit operator gate | Yes — operator confirmed option 1; stories accepted with this evidence |

---

## Product note

Overall **`confirmed clean`**. US-062 + US-063 Story accepted; **BL-026 closed 2026-07-21**.
