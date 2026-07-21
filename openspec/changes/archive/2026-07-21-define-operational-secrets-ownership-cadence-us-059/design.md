## Context

P6 **BL-024 / US-059** asks the system owner to **define ownership and rotation cadence** for operational secrets so credentials remain current, protected, and auditable. US-057 rotation is waived/deferred; US-058 permissions + secrets-absence review is Story accepted (2026-07-21). BL-024 closes when US-059 is Story accepted.

Operator-approved cadence defaults (2026-07-21): worker API key + n8n `worker_api_key` every **90 days** (or on suspected exposure); provider keys (DeepSeek/ComfyUI) every **180 days**; LinkedIn OAuth client secret **180 days** / tokens on refresh-failure or reauth (BL-025 owns lifecycle detail); GitHub Pages deploy key every **1 year**; US-058-style re-audit every **90 days**. Owner: system owner (solo deployment).

Constraints: docs/procedure-first; MUST NOT execute live rotations in this change; MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; prefer one SoT under `docs/operations/`.

## Goals / Non-Goals

**Goals:**

- Normative ownership + cadence table for operational secret classes.
- Blocked/deferred vocabulary when a due rotation/review cannot be completed.
- Visibility via CURRENT-STATE / GLOSSARY / product pointers.
- Enable BL-024 closure after US-059 Story accepted.

**Non-Goals:**

- Live key rotation execution.
- Secrets vault / automated rotation cron in the worker.
- BL-025 LinkedIn token lifecycle rewrite; BL-026 exposure review.
- Flow A/B or LinkedIn enablement changes.

## Decisions

1. **Docs/procedure-first** — Same pattern as US-053–US-058: written SoT now; Story accepted when owner confirms the published ownership/cadence matches decisions (no forced rotation run).
2. **Canonical artifact** — `docs/operations/operational-secrets-ownership-cadence.md`; thin pointer from US-058 procedure (do not duplicate permissions checklist).
3. **Capability** — `operational-secrets-ownership-cadence` (new); no MODIFIED deltas on US-058 capability.
4. **Approved intervals** — Encode the operator-approved table; on-suspicion always overrides calendar.
5. **Execution reference** — Point to existing Worker API key rotation section when a rotation is approved; US-059 does not re-author rotation steps.
6. **BL-024 close** — After US-059 Story accepted, update product docs to close BL-024 (US-057 waived + US-058 + US-059 accepted).

## Risks / Trade-offs

- [Risk] Cadence published but never followed → Mitigation: CURRENT-STATE notes procedure published; optional calendar reminder is operator-owned; blocked/deferred vocabulary for missed due dates.
- [Risk] Scope creep into BL-025 → Mitigation: LinkedIn token rows point to BL-025 for lifecycle mechanics.
- [Trade-off] Manual cadence vs automated reminders — manual-first matches thin scope.

## Migration Plan

1. `/opsx-apply` writes ops procedure + pointers; product Work started → Story accepted when owner confirms.
2. Close BL-024 in product docs after US-059 acceptance.
3. Rollback: revert commits; no runtime flag changes.

## Open Questions

- None material — intervals and ownership approved by operator 2026-07-21.
