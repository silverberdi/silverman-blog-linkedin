# Operational secrets permissions + secrets-absence review (US-058)

**Scope:** Operator-facing permissions and secrets-absence review for **BL-024 / US-058** (Story 2): review least-privilege access to operational secrets, and confirm secrets are absent from Git, logs/HTTP responses, and n8n workflow exports.
**Status:** Procedure **published** (documentation/contract). Live operator review / **Story accepted** remain **pending**. Publishing this document alone does **not** mean server secrets are confirmed clean, does **not** close BL-024, and does **not** accept US-059.
**Authority:** Complements [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md), [user-stories.md](../product/user-stories.md) US-058, and existing secret-safety norms (no secrets in HTTP responses/docs/commits; env-only keys; ADR-0001 HTTP-only).
**OpenSpec:** capability `operational-secrets-permissions-review` (change `review-operational-secrets-permissions-us-058`).
**Evidence template:** [operational-secrets-permissions-review-TEMPLATE.md](operational-secrets-permissions-review-TEMPLATE.md).

This document is the shared written meaning of US-058 for the system owner and operator. It does **not** change Flow A publish/package/schedule, Flow B discover/draft/gap-trigger/promote, n8n orchestration behavior, LinkedIn publish-due, OAuth lifecycle formalization (BL-025), or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

---

## 1. What this is (and is not)

| This document | MUST NOT mean |
|---------------|---------------|
| Least-privilege permissions checklist for secret-bearing surfaces | A secrets-management platform, vault product, or new auth middleware |
| Secrets-absence checklist for Git, logs/HTTP responses, and n8n exports | Live key rotation (US-057) or ownership/cadence definition (US-059) |
| Outcome vocabulary: `blocked` / `confirmed clean` / `finding — remediation required` | “Secrets confirmed clean on the server” from docs alone |
| Procedure published in CURRENT-STATE | Story accepted, BL-024 closed, or BL-026 full exposure review completed |

**Independence (normative):**

| Related work | Relationship to this procedure |
|--------------|--------------------------------|
| **US-057** (rotate keys) | Closed/waived 2026-07-21 — rotation **deferred**, **not** performed. This procedure MUST NOT rotate live keys, rewrite server `.env`, or mutate n8n `worker_api_key`. If a finding implies rotation, record `finding — remediation required` and defer execution to an approved rotation path — do not silently rotate. |
| **US-059** (ownership + rotation cadence) | Out of scope — leave open. Do not invent cadence tables here. |
| **BL-024** | Remains open until US-058 **and** US-059 are Story accepted. |
| **BL-025** | LinkedIn token lifecycle formalization — out of scope; leave open. |
| **BL-026** | Service permissions/exposure (ports, ComfyUI, public checkout attack surface) — adjacent; **not** required to complete US-058. Stay secrets-focused. |
| **Flow A / Flow B** | No pipeline behavior changes. |
| **`SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`** | MUST NOT be mutated by this review. |

**Context only (not required US-058 steps):** historical [Worker API key rotation](../deployment/ubuntu-server-worker-deployment.md#worker-api-key-rotation) and `deploy/server/verify-worker-api-key-rotation.sh`. Do **not** invoke them as part of this review.

---

## 2. Outcome vocabulary

Record one outcome per checklist item (and an overall review outcome). **Never print secret values** — use env var **names**, path classes, and permission modes only.

| Outcome | Meaning |
|---------|---------|
| `blocked` | Check **cannot** be completed (no server access, export unavailable, mount not inspectable, UI credential store inaccessible). Record a non-secret reason. |
| `confirmed clean` | Check **completed**; no secret exposure found and permissions match expected least privilege for that surface. |
| `finding — remediation required` | Exposure or excessive permission found. Record env var names / path classes / modes only — **never** values. |

**Rules:**

- Incomplete or `blocked` checks MUST NOT be recorded as `confirmed clean`.
- Overall review MUST NOT be claimed fully `confirmed clean` while any required check remains `blocked`.
- Deferred US-057 rotation MUST NOT by itself be recorded as a US-058 secrets-absence failure.
- Optional automated scan aids (e.g. ripgrep for placeholder patterns) MAY help; they are **not** required to publish or run this procedure.

---

## 3. Expected secret locations (never commit real values)

| Location (class) | Typical path / form | Notes |
|------------------|---------------------|-------|
| Server-local worker `.env` | Host: `/home/silverman/silverman-blog-linkedin-worker/.env` | Real keys live here only; never commit. Source template: `deploy/server/silverman-worker.env.example` (placeholders). |
| Host secrets directory | `/home/silverman/silverman-blog-linkedin-worker/secrets/` | Expected dir mode **`700`**; token/key files **`600`**. Mounted into container as `/secrets`. |
| OAuth / token store | Host: `.../secrets/linkedin-oauth-tokens.json`, `linkedin-oauth-state.json`; container: `/secrets/...` via `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` | See [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md). |
| Deploy / SSH key material | Under secrets dir (or documented mount); used for Git publication when enabled | Read-only mount into container; never commit private keys. Related: `known_hosts` for SSH — treat as operational config, not a secret dump target. |
| n8n credentials / workflow variables | n8n UI / credential store; workflow **Set Configuration** fields such as `worker_api_key` | Must match worker `SILVERMAN_BLOG_LINKEDIN_API_KEY` when used; must **not** appear as live values in committed workflow JSON. |
| Version-controlled placeholders | `CHANGE_ME_*`, env example files, n8n expressions referencing credential **names** | Allowed. Real Bearer tokens / API keys / client secrets are **not**. |

**MUST NOT:** Commit `.env`, dump `.env` into docs/chat/PRs, or paste live tokens into evidence templates committed to git.

---

## 4. Permissions review checklist (least privilege)

For each row: inspect who/what can read the secret surface; compare to expected location and mode; record outcome with env var **names** / path classes only.

| # | Surface | What to review | Expected least privilege (guidance) |
|---|---------|----------------|-------------------------------------|
| P1 | **Worker process / container** | Which env vars and mounts the worker container can read (`SILVERMAN_BLOG_LINKEDIN_API_KEY`, LinkedIn OAuth vars, `SILVERMAN_CALENDAR_DATABASE_URL`, optional DeepSeek/ComfyUI keys, token store path) | Only the worker service account / compose service needs these; no world-readable `.env` on the host; secrets mount not shared more broadly than documented |
| P2 | **n8n credential / variable holders** | Who can open n8n and read `worker_api_key` (and other secret-bearing credential nodes); which workflows reference it | Limit n8n admin/editor access; credentials held in n8n store / Set Configuration — not duplicated into unrelated workflows as cleartext |
| P3 | **Docker / compose mounts** | Compose mounts for `.env`, `/secrets`, editorial data, public blog checkout | Secrets mounts as narrow as documented (e.g. secrets dir → `/secrets`); editorial/public mounts are **not** secret stores — do not store keys there |
| P4 | **OAuth / token files + secrets dir** | Host `secrets/` directory mode; token/state file modes; container path alignment with `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` | Dir **`700`**, files **`600`** where supported; only worker (and operator with explicit need) can read |
| P5 | **Deploy keys / SSH known_hosts** | Deploy private key presence, mount read-only flags, who can read the key file on the host | Private key under secrets (or documented path), read-only into container when Git publication is used; never in git; `known_hosts` not used as a credentials dump |
| P6 | **Related secret-read access** | Other operators, backup copies of `.env`, shared SMB/NFS paths, CI, or chat logs that might hold live values | No unnecessary copies; backups of `.env` stay off git and off shared editorial mounts |

**BL-026 note:** Open ports, ComfyUI exposure, and public checkout attack surface are **not** required US-058 checks. Record them only as optional adjacent notes pointing to BL-026 — do not block US-058 completion on a full exposure review.

---

## 5. Secrets-absence checklist (Git, logs, workflow exports)

| # | Surface | What to confirm | Pass guidance |
|---|---------|-----------------|---------------|
| A1 | **Git / version control** | No real `.env` contents; no live API keys, OAuth tokens, client secrets, or deploy private keys in committed files (including docs, examples, and `n8n/workflows/*.json`) | Placeholders (`CHANGE_ME_*`, example values) and env var **names** only; `.env` gitignored / absent from tree |
| A2 | **Worker logs and HTTP responses** | Spot-check recent worker logs and representative authenticated/error responses: no Bearer token values, no client secrets, no token-store cleartext | Env var names and stable error codes only (existing secret-safety norms) |
| A3 | **n8n workflow exports** | Exported / committed workflow JSON uses placeholders or expressions referencing credential names (e.g. `worker_api_key`) — not live key material or OAuth tokens | Re-export check: if an export contains a live-looking secret, record `finding — remediation required` with **field/node names only** |

**Optional aids (not required):** search the repo for accidental patterns (e.g. long hex strings in workflow JSON) using tools that print matches carefully — prefer confirming absence of known placeholder violations over dumping potential secret material into chat.

**Rotation scripts:** `verify-worker-api-key-rotation.sh` is context for US-057-style rotation validation; it MUST NOT be required to complete this absence checklist, and running it is **not** part of US-058.

---

## 6. How to run the review (operator)

1. Copy [operational-secrets-permissions-review-TEMPLATE.md](operational-secrets-permissions-review-TEMPLATE.md) to an operator-owned dated evidence file **or** a private tracker. Prefer keeping filled evidence **out of git** if it could leak context; if committing a sanitized copy, use env var names only.
2. Complete **§4** permissions rows (P1–P6) and **§5** absence rows (A1–A3). Mark each `blocked` / `confirmed clean` / `finding — remediation required`.
3. Set overall outcome:
   - All required checks `confirmed clean` → overall `confirmed clean`.
   - Any required check `blocked` → overall **not** fully clean (record overall as `blocked` or mixed with findings — never claim full clean).
   - Any `finding — remediation required` → overall includes findings; remediate without pasting secret values into git.
4. If remediation needs key rotation, **stop** and schedule an approved rotation (US-057-style) — do **not** rotate inside this review.
5. Story accepted for US-058 remains an **explicit operator gate** after this live review (or after recording blocked checks where access is unavailable).

---

## 7. Failure / blocked communication (examples)

| Situation | Record as | Example note (no values) |
|-----------|-----------|--------------------------|
| No SSH/LAN access to `192.168.0.194` | `blocked` | “Host secrets directory not inspectable — no server access” |
| n8n UI unreachable | `blocked` | “Cannot review `worker_api_key` holders — n8n unavailable” |
| Committed workflow contains live-looking API key field | `finding — remediation required` | “`n8n/workflows/….json` Set Configuration field `worker_api_key` appears to embed a live value — replace with placeholder / credential reference” |
| Host `secrets/` is `755` / world-readable | `finding — remediation required` | “Host secrets dir mode wider than expected `700`” |
| Permissions and absence checks all pass | `confirmed clean` | “P1–P6 and A1–A3 completed; no exposure found” |

---

## 8. Related documents

- Deploy + historical rotation: [ubuntu-server-worker-deployment.md](../deployment/ubuntu-server-worker-deployment.md)
- LinkedIn OAuth / token store paths: [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md)
- Product: [backlog.md](../product/backlog.md) BL-024, [user-stories.md](../product/user-stories.md) US-058
