# Operational secrets permissions review — evidence template (US-058)

**BANNER — DO NOT COMMIT REAL SECRETS**

- Never paste API keys, Bearer tokens, OAuth client secrets, refresh tokens, deploy private keys, or `.env` contents into this file.
- In committed evidence, use **env var names** and path classes only (e.g. `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `worker_api_key`, host `secrets/` dir).
- Prefer keeping filled copies **out of git** (password manager, encrypted notes, or private tracker). If you commit a sanitized copy under `docs/operations/`, scrub values first.

**Normative procedure:** [operational-secrets-permissions-review.md](operational-secrets-permissions-review.md).
**Outcome vocabulary (per check):** `blocked` | `confirmed clean` | `finding — remediation required` — see procedure §2.
**Usage:** Copy this template to a dated operator-owned file (e.g. `us-058-permissions-review-YYYY-MM-DD.md`) or private tracker; fill outcomes without secret values.

**Out of scope for this review:** live key rotation (US-057 deferred); ownership/cadence (US-059); BL-025 token lifecycle; BL-026 full exposure; mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

---

## Review metadata

| Field | Value |
|-------|-------|
| Review date (UTC or local) | |
| Recorded by | |
| Scope | BL-024 / US-058 permissions + secrets-absence |
| Server / environment | e.g. `192.168.0.194` worker deploy dir (or `blocked` — no access) |
| Overall outcome | `blocked` / `confirmed clean` / `finding — remediation required` (or mixed — explain without values) |

---

## Permissions checklist (procedure §4)

| ID | Surface | Outcome | Notes (env var names / path classes / modes only) |
|----|---------|---------|-----------------------------------------------------|
| P1 | Worker process / container secret access | | |
| P2 | n8n credential / `worker_api_key` holders | | |
| P3 | Docker / compose mounts (secrets vs editorial/public) | | |
| P4 | OAuth / token files + secrets directory modes | | |
| P5 | Deploy keys / SSH known_hosts | | |
| P6 | Related secret-read access (backups, shares, extras) | | |

---

## Secrets-absence checklist (procedure §5)

| ID | Surface | Outcome | Notes (names / path classes only — no values) |
|----|---------|---------|-----------------------------------------------|
| A1 | Git / version-controlled files | | |
| A2 | Worker logs / HTTP responses | | |
| A3 | n8n workflow exports | | |

---

## Findings / remediation (optional)

| # | Finding summary (no values) | Related ID | Remediation next step (no rotation unless separately approved) |
|---|-----------------------------|------------|----------------------------------------------------------------|
| | | | |

---

## Operator attestation

| Statement | Yes / No / N/A |
|-----------|----------------|
| No secret values were written into this evidence file | |
| No live key rotation / `.env` rewrite / n8n `worker_api_key` mutation was performed as part of this US-058 review | |
| US-059 ownership/cadence was not defined in this review | |
| Story accepted for US-058 is still an explicit gate after this review (or blocked checks were recorded) | |
