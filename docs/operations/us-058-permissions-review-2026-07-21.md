# US-058 operational secrets permissions review — evidence 2026-07-21

**BANNER — no secret values in this file.** Env var names, path classes, and permission modes only.

**Normative procedure:** [operational-secrets-permissions-review.md](operational-secrets-permissions-review.md).

| Field | Value |
|-------|-------|
| Review date (UTC) | `2026-07-21T17:44:27Z` (server host `ubuntu` / `192.168.0.194`) |
| Recorded by | Operator-assisted agent session (SSH secret-safe audit) |
| Scope | BL-024 / US-058 permissions + secrets-absence |
| Server / environment | `/home/silverman/silverman-blog-linkedin-worker` + `/home/silverman/n8n-imports` |
| Overall outcome | `confirmed clean` (after remediations 2026-07-21: A3/P2/P6 n8n-imports cleanup + P5 deploy-key/known_hosts file layout + GitHub deploy key verified) |

**Story accepted:** operator-accepted 2026-07-21 (US-058).

**Not performed:** US-057 key rotation of `SILVERMAN_BLOG_LINKEDIN_API_KEY` / n8n `worker_api_key`; `.env` rewrite of API keys; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` change; US-059 cadence definition.

**Remediation applied (finding #1):** Deleted live-looking / prepared / live / bulk dump JSON under `/home/silverman/n8n-imports/` (11 files). Kept only `*.source.json` placeholders. Post-clean classify: `remaining_LIVE_LOOKING_files=0`. Smoke: Silverman workflows still listed in n8n; `GET /health` → 200.

**Remediation applied (finding #2 / P5):** Removed empty Docker-created dirs; generated durable host **files** `secrets/github-pages-deploy-key` + `secrets/known_hosts` mode `600`; recreated worker container. Mounts verified as files (`:ro`). `/health` → 200. Operator registered new public key as GitHub Deploy Key (write) on `silverberdi.github.io` 2026-07-21. Verified from container: SSH auth success message for `silverberdi/silverberdi.github.io`; `git ls-remote origin main` OK.

---

## Permissions checklist (procedure §4)

| ID | Surface | Outcome | Notes (names / path classes / modes only) |
|----|---------|---------|-------------------------------------------|
| P1 | Worker process / container secret access | `confirmed clean` | Host `.env` mode `600` `silverman:silverman`, not world-readable. Expected secret-bearing keys present as non-placeholder on server (names only): `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `DEEPSEEK_API_KEY`, `SILVERMAN_CALENDAR_DATABASE_URL`, `SILVERMAN_LINKEDIN_CLIENT_ID`, `SILVERMAN_LINKEDIN_CLIENT_SECRET`, `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH`, `SILVERMAN_COMFYUI_API_KEY`, `GIT_SSH_COMMAND`. Fallback `SILVERMAN_LINKEDIN_ACCESS_TOKEN` missing (OK). Worker container present; env injected via compose `.env`. |
| P2 | n8n credential / `worker_api_key` holders | `confirmed clean` (after remediation) | n8n listens on `192.168.0.194:5678`. Silverman workflows present. Live-looking on-disk copies under `n8n-imports/` **deleted** 2026-07-21; only `*.source.json` placeholders remain. Repo `n8n/workflows/*.json` remain `CHANGE_ME_WORKER_API_KEY`. |
| P3 | Docker / compose mounts | `confirmed clean` | Narrow mounts: `secrets/linkedin-oauth` → `/secrets/linkedin-oauth`; deploy-key + known_hosts as separate binds (`Mode=ro`); editorial → `/data/...`; public blog → `/public-blog`. No secrets stored on editorial/public mounts. |
| P4 | OAuth / token files + secrets directory | `confirmed clean` | Host `secrets/` mode `700`. `secrets/linkedin-oauth/` mode `700`. Token/state files mode `600`. |
| P5 | Deploy keys / SSH known_hosts | `confirmed clean` | Empty dirs removed. Host files mode `600`. Container mounts files `:ro`. New ed25519 key generated 2026-07-21; public key registered on GitHub. Verified: SSH auth to `silverberdi/silverberdi.github.io` + `git ls-remote origin main` OK. |
| P6 | Related secret-read access | `confirmed clean` (after remediation) | One `.env.bak.*` mode `600` (OK). No accidental secret-named files under editorial/public/worker-data (depth ≤4). `n8n-imports/` plaintext live copies removed; only placeholder sources remain. |

---

## Secrets-absence checklist (procedure §5)

| ID | Surface | Outcome | Notes |
|----|---------|---------|-------|
| A1 | Git / version-controlled files | `confirmed clean` | Mac repo: `.env` gitignored/untracked; no tracked `.env` / `.pem` / deploy-key / oauth-tokens path classes. Committed `n8n/workflows/*.json` use placeholders + expressions only. |
| A2 | Worker logs / HTTP responses | `confirmed clean` | `GET /health` → 200; no suspicious secret patterns. `GET /linkedin/oauth/status` → 200; metadata only (`token_present`, expiry, scopes, `member_urn`, `publication_enabled`) — no access/refresh token or client secret cleartext. Docker log tail: no remaining suspicious token patterns. |
| A3 | n8n workflow exports | `confirmed clean` (after remediation) | Repo + remaining `n8n-imports/*.source.json` use placeholders / no live `worker_api_key`. Previously flagged prepared/live/bulk dumps **deleted** 2026-07-21 (re-classify: 0 LIVE_LOOKING files in that directory). |

---

## Findings / remediation

| # | Finding summary (no values) | Related ID | Remediation next step |
|---|-----------------------------|------------|------------------------|
| 1 | Live-looking `worker_api_key` in `/home/silverman/n8n-imports/` prepared/live/bulk dumps | A3 / P2 / P6 | **Done 2026-07-21:** deleted 11 files; kept 5 `*.source.json` placeholders. Note: future import scripts may recreate `.prepared.json` — delete after import. Optional US-057 rotation still deferred. |
| 2 | `secrets/github-pages-deploy-key` / `known_hosts` were empty dirs `755` | P5 | **Done 2026-07-21:** durable files `600` + worker recreate + GitHub deploy key registered + SSH/`git ls-remote` verified. |

---

## Operator attestation

| Statement | Yes / No / N/A |
|-----------|----------------|
| No secret values were written into this evidence file | Yes |
| No live key rotation / `.env` rewrite / n8n `worker_api_key` mutation was performed as part of this US-058 review | Yes |
| US-059 ownership/cadence was not defined in this review | Yes |
| Story accepted for US-058 is still an explicit gate after this review | Yes — awaiting system-owner acceptance |

---

## Product note

Overall **`finding — remediation required`**. Story accepted remains your gate after you accept this evidence (and optionally remediate finding #1 first). BL-024 / US-059 stay open. US-057 rotation still deferred unless you choose to rotate because of the n8n-imports plaintext copies.
