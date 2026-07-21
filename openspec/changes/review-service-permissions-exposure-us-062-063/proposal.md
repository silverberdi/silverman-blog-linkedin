## Why

BL-026 (**US-062** + **US-063**) still lacks an operator-facing contract for **service permissions and exposure**: least privilege, open ports, authentication, allowed paths, secrets separation, and an explicit **accepted exposure** inventory. US-058 covered secrets-focused permissions; BL-026 is the adjacent attack-surface review for worker, n8n, Comfy Cloud/DeepSeek clients, Docker mounts, shared filesystem, and public checkout. Without a SoT, LAN-only intent vs exceptional OAuth callback can drift undocumented.

## What Changes

- Publish `docs/operations/service-permissions-and-exposure.md` as the BL-026 / US-062+US-063 SoT.
- Encode operator-approved **accepted exposure** (2026-07-21): worker + n8n + Authority Manager **LAN-only**; LinkedIn OAuth callback via Cloudflare **exceptional** (reauth only); Comfy Cloud + DeepSeek as **outbound API clients** (no inbound ComfyUI port); secrets separation ratified from US-058; console public + Google auth **future / out of scope**.
- Run a live LAN review on `192.168.0.194` (ports, auth spot-check, mounts/paths) and record evidence with blocked/clean/finding vocabulary (no secrets).
- Capability `service-permissions-and-exposure` (docs/contract); CURRENT-STATE / GLOSSARY / product pointers; close BL-026 when both stories accepted.
- Thin pointer from US-058 (adjacent, not duplicate).

### Goals

- Satisfy US-062 (least privilege, open ports, authentication) and US-063 (allowed paths, separate secrets, document accepted exposure).
- Make outcomes visible; communicate findings without secret values.
- Preserve completed work; no LinkedIn enablement mutation; no internet exposure of the console.

### Non-goals

- Exposing Authority Manager / console publicly or activating Google/OIDC (future iteration).
- Broad `local-ai-stack` redesign; closing unrelated Avatares surfaces beyond documenting adjacency.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Reopening BL-024/025; inventing a WAF/VPN product.
- Hosting inbound ComfyUI on this server (Comfy Cloud outbound only).

### Acceptance criteria addressed

| Story | Criterion | How |
|-------|-----------|-----|
| US-062 | Apply least privilege | SoT + live mount/auth review |
| US-062 | Review open ports | SoT inventory + live `ss`/listen check |
| US-062 | Review authentication | API key / n8n LAN expectations documented + spot-check |
| US-063 | Review allowed paths | Mount/path inventory + live confirm |
| US-063 | Separate secrets | Ratify US-058 secrets layout |
| US-063 | Document accepted exposure | Explicit accepted-exposure table (option 1 OAuth) |
| Both | Visible / blocked / no churn | Pointers + vocabulary + docs/live evidence |

## Capabilities

### New Capabilities

- `service-permissions-and-exposure`: Operator-visible normative permissions and exposure review for **BL-026 / US-062 + US-063** — least privilege, open ports, authentication, allowed paths, secrets separation (ratifying US-058), and documented accepted exposure (LAN-first; exceptional OAuth callback) — without public console exposure, enablement mutation, or a network-security platform.

### Modified Capabilities

- (none)

## Impact

- **Product:** Closes **BL-026** after US-062 + US-063 Story accepted.
- **Docs:** New ops SoT + live evidence; CURRENT-STATE / GLOSSARY / product.
- **Runtime:** Review-only by default; remediations only for clear safe findings (same discipline as US-058).
- **Preserved:** US-058 secrets SoT; BL-025 token SoT; ADR-0001.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-026 / US-062 / US-063** | Primary |
| US-058 | Secrets least-privilege — ratify, do not duplicate |
| US-040D | Public URL / Google auth readiness — future, out of scope |
| BL-024 / BL-025 | Closed — do not reopen |
