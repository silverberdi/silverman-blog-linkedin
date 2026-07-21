## Context

BL-026 reduces attack surface for worker, n8n, Comfy/DeepSeek clients, Docker, shared FS, and public checkout. Operator decisions 2026-07-21: LAN-only for worker API, n8n, and Authority Manager; OAuth Cloudflare callback **accepted as exceptional** for LinkedIn reauth only (option 1); Comfy Cloud + DeepSeek API outbound; secrets ratify US-058; console public/Google later.

## Goals / Non-Goals

**Goals:** One SoT + live review evidence; close BL-026 with both stories accepted.

**Non-Goals:** Public console; Google auth activation; enablement mutation; hosting inbound ComfyUI; broad stack firewall redesign.

## Decisions

1. Docs/procedure-first SoT: `docs/operations/service-permissions-and-exposure.md`.
2. Capability `service-permissions-and-exposure` (new).
3. Accepted exposure table is normative operator policy for this change.
4. Live review on `192.168.0.194` required for Story accepted (ports/auth/paths); vocabulary `blocked` / `confirmed clean` / `finding — remediation required`.
5. Remediations only for clear safe findings; do not expose new public surfaces.

## Risks / Trade-offs

- [Risk] OAuth exception misunderstood as “API is public” → Mitigation: SoT states callback-path-only / reauth exception; rest LAN.
- [Risk] local-ai-stack other ports adjacent → Mitigation: document silverman-relevant listens; do not absorb full Avatares hardening.

## Migration Plan

Apply → live evidence → product close BL-026 → sync → archive. Rollback: revert commits.

## Open Questions

None — OAuth option 1 approved.
