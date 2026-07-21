## Why

BL-024 Story 3 (**US-059**) still lacks a written ownership and rotation-cadence contract for operational secrets. US-057 rotation remains deferred/waived; US-058 permissions + secrets-absence review is Story accepted. Without a thin ownership/cadence SoT, the system owner has no shared schedule or accountability for when keys are reviewed or rotated — and BL-024 cannot close.

## What Changes

- Publish an operator-facing **operational secrets ownership + rotation cadence** procedure under `docs/operations/` covering who owns each secret class and the approved review/rotation intervals (operator-approved 2026-07-21: 90 / 180 / 365 days + on suspected exposure).
- Document blocked / deferred vocabulary when a scheduled rotation cannot be completed (mirror US-057 deferred style — no silent skip).
- Introduce capability `operational-secrets-ownership-cadence` as documentation/contract (no secrets vault, no live rotation execution, no auth middleware rewrite).
- Cross-link from CURRENT-STATE / GLOSSARY / light product pointers; leave BL-025 LinkedIn token lifecycle and BL-026 exposure review untouched.
- After Story accepted for US-059, **BL-024 may close** (US-057 waived + US-058 accepted + US-059 accepted).

### Goals

- Satisfy **BL-024 / US-059** acceptance criteria as a thin ownership + cadence procedure + documentation/contract.
- Name owners (system owner / Silverio for this solo deployment) and cadences for worker API key + n8n `worker_api_key`, provider keys, LinkedIn OAuth client/token-store class, GitHub Pages deploy key, and periodic US-058-style re-audit.
- Make the outcome visible; communicate failures/blocked/deferred clearly without printing secret values.
- Preserve completed work — no Flow A/B behavior changes; no US-057 forced rotation; no `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation.

### Non-goals

- Performing live key rotation (US-057 stays deferred unless separately approved).
- Reopening US-058 permissions checklist as a rewrite.
- Closing **BL-025 / US-060+** or implementing full LinkedIn token lifecycle (point only).
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or auto-publishing LinkedIn.
- Committing real secrets; inventing a secrets-management platform or mandatory rotation cron in the worker.
- Broad security redesign or unrelated `src/` refactors (default: docs/procedure-only).

### Acceptance criteria addressed

| US-059 criterion | How this change addresses it |
|---|---|
| Define ownership and rotation cadence | Normative ops table: owner + interval per secret class |
| Outcome visible and understandable | Ops artifact + CURRENT-STATE / GLOSSARY / product pointers |
| Failures or blocked states clearly communicated | Deferred / blocked vocabulary when cadence cannot be met |
| Existing completed work not duplicated or unintentionally changed | Docs/contract-first; no pipeline/enablement/rotation execution |

### Intentionally excluded

- Live rotation execution (US-057).
- BL-025 full OAuth lifecycle formalization.
- BL-026 service exposure review.
- Automated rotation workers or calendar bots.

## Capabilities

### New Capabilities

- `operational-secrets-ownership-cadence`: Operator-visible normative ownership and rotation-cadence procedure for **BL-024 / US-059** — who owns each operational secret class and how often to review/rotate (including on-suspicion triggers and blocked/deferred vocabulary) — without requiring live rotation, a secrets vault, US-058 checklist rewrite, BL-025 lifecycle rewrite, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

### Modified Capabilities

- (none — documentation/contract capability; US-058 permissions-review and deployment rotation docs remain pointers only)

## Impact

- **Product:** Completes **BL-024 / US-059**; enables BL-024 closure after Story accepted; does not reopen US-057 rotation.
- **Docs:** New ops SoT under `docs/operations/`; CURRENT-STATE / GLOSSARY / light product pointers; optional thin link from US-058 procedure.
- **OpenSpec:** New capability after sync; no requirement deltas that rewrite Flow A/B, LinkedIn publication, or worker auth behavior.
- **Worker / n8n / Docker / enablement:** No required runtime behavior changes.
- **Preserved:** ADR-0001; ADR-0002; US-058 procedure; historical rotation runbook as execution reference only.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-024 / US-059** | Primary — define ownership and rotation cadence |
| US-057 | Closed/waived — rotation deferred; do not execute in this change |
| US-058 | Story accepted 2026-07-21 — permissions review SoT; re-audit cadence references it |
| BL-024 | Close after US-059 Story accepted |
| BL-025 / US-060+ | Out of scope — LinkedIn token lifecycle |
| BL-026 | Adjacent — do not absorb |
| Historical Worker API key rotation docs | Execution reference when a rotation is approved — not US-059 itself |
