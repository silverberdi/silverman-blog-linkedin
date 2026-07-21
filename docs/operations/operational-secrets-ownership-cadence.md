# Operational secrets ownership + rotation cadence (US-059)

**Scope:** Operator-facing **ownership** and **rotation/review cadence** for operational secrets — **BL-024 / US-059** (Story 3).
**Status:** Procedure **published** (documentation/contract). Operator-approved intervals 2026-07-21.
**Authority:** Complements [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md), [user-stories.md](../product/user-stories.md) US-059, and [operational-secrets-permissions-review.md](operational-secrets-permissions-review.md) (US-058).
**OpenSpec:** capability `operational-secrets-ownership-cadence` (change `define-operational-secrets-ownership-cadence-us-059`).

This document does **not** rotate keys by itself. When a rotation is approved, use the existing [Worker API key rotation](../deployment/ubuntu-server-worker-deployment.md#worker-api-key-rotation) runbook (and related provider/GitHub steps). US-057 remains deferred until a separate rotation is approved. Does **not** mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or change Flow A/B behavior.

---

## 1. Ownership

| Role | Responsibility |
|------|----------------|
| **System owner** (this deployment: Silverio / solo operator) | Owns all operational secret classes below; schedules reviews/rotations; records deferred/blocked outcomes; keeps real values out of git |

There is no separate secrets team in this deployment. If that changes, update this table via a new OpenSpec change.

---

## 2. Cadence table (operator-approved 2026-07-21)

Intervals are calendar defaults. **On suspected exposure** always overrides and is **immediate**.

| Secret class | Env var / path class (names only) | Owner | Review / rotate cadence | Notes |
|--------------|-----------------------------------|-------|-------------------------|-------|
| Worker API key **paired with** n8n `worker_api_key` | `SILVERMAN_BLOG_LINKEDIN_API_KEY` + n8n Set Configuration `worker_api_key` | System owner | **90 days**, or on suspected exposure | Rotate **together** (worker first, then n8n). Runbook: deployment Worker API key rotation. |
| Provider API keys | `DEEPSEEK_API_KEY`, `SILVERMAN_COMFYUI_API_KEY` (and related Comfy auth vars) | System owner | **180 days**, or on suspected exposure / provider revoke | Rotate at provider console; update server `.env` only. |
| LinkedIn OAuth client secret | `SILVERMAN_LINKEDIN_CLIENT_SECRET` (+ client id as non-secret identifier) | System owner | **180 days**, or on suspected exposure | Token **store** refresh/reauth mechanics → **BL-025** (do not redefine here). |
| LinkedIn token store | `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH` / `secrets/linkedin-oauth/*` | System owner | On refresh failure / reauthorization required | Lifecycle SoT: [linkedin-token-management.md](linkedin-token-management.md) (BL-025). |
| GitHub Pages deploy key | `secrets/github-pages-deploy-key` (+ `known_hosts`) | System owner | **1 year**, or on loss of access / machine change | Register public key as GitHub deploy key (write); never commit private key. |
| Permissions + absence re-audit | US-058 procedure | System owner | **90 days** | Re-run [operational-secrets-permissions-review.md](operational-secrets-permissions-review.md); do not paste values into evidence. |
| Inventory / password manager | (operator-private) | System owner | Keep current with each rotation | Store values only in password manager — never in git. |

---

## 3. Blocked / deferred vocabulary

When a due review or rotation cannot be completed:

| Outcome | Meaning |
|---------|---------|
| `blocked` | Cannot complete (no server access, provider outage, GitHub unavailable) — record non-secret reason |
| `deferred` | Operator consciously postpones (same pattern as US-057 waived rotation) — record reason and next review date |
| `completed` | Review or rotation finished; record date only (no secret values) |

Missed due dates MUST NOT be silently skipped. Deferred ≠ rotated.

---

## 4. Independence

| Topic | Rule |
|-------|------|
| US-057 | Remains deferred until separately approved; this doc does not force rotation |
| US-058 | Permissions checklist remains the re-audit SoT; this doc only schedules it |
| BL-025 | LinkedIn token lifecycle detail stays there |
| BL-026 | Service exposure — closed 2026-07-21; see [service-permissions-and-exposure.md](service-permissions-and-exposure.md) |
| Enablement | MUST NOT change `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as part of cadence work |
| Pipelines | No Flow A/B behavior changes |

---

## 5. Related documents

- US-058 review: [operational-secrets-permissions-review.md](operational-secrets-permissions-review.md)
- Rotation runbook: [ubuntu-server-worker-deployment.md](../deployment/ubuntu-server-worker-deployment.md#worker-api-key-rotation)
- Product: [backlog.md](../product/backlog.md) BL-024, [user-stories.md](../product/user-stories.md) US-059
