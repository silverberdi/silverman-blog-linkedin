## Context

P6 **BL-024 / US-058** asks the system owner to **review permissions** on operational secrets and **confirm secrets are absent** from Git, logs, and n8n workflow exports so credentials remain protected and auditable. US-057 (rotate keys) was **closed/waived 2026-07-21** — rotation was **not** performed and stays deferred. US-059 (ownership + rotation cadence) remains a later story. BL-024 stays open until US-058 and US-059 are Story accepted.

Existing norms already forbid secrets in HTTP responses, docs, and commits; keys live in server-local `.env` and secrets mounts; ADR-0001 keeps n8n → worker HTTP-only. Historical rotation procedure lives in `docs/deployment/ubuntu-server-worker-deployment.md` (Worker API key rotation) with helper `deploy/server/verify-worker-api-key-rotation.sh` — **context only** for US-058 (review/audit, not rotation). Phase 2 evidence already documented secrets-mount least-privilege concerns; LinkedIn OAuth paths and deploy-key mounts are documented in deployment guides. What is missing is a single operator-facing **permissions + absence** review SoT with clear blocked/clean/finding vocabulary.

Stakeholders: system owner (primary reviewer); operator executing the checklist; later US-059 ownership/cadence consumers.

Constraints: OpenSpec before code; docs/procedure-first; MUST NOT rotate live keys or mutate n8n `worker_api_key`; MUST NOT mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; MUST NOT close BL-024 or mark US-059 accepted; prefer one SoT under `docs/operations/` over a secrets platform; no deploy / Story accepted by apply alone.

## Goals / Non-Goals

**Goals:**

- Normative ops procedure for US-058 permissions review (worker, n8n, Docker/compose, shared mounts, OAuth/token files, deploy keys, related service access).
- Secrets-absence checklist for Git, logs/HTTP responses, and workflow exports (placeholders / env var names only).
- Outcome vocabulary: `blocked` (check cannot complete) vs `confirmed clean` vs `finding — remediation required` — never print secret values.
- Capability contracts + CURRENT-STATE / GLOSSARY / product pointers so the outcome is operator-visible.
- Optional evidence template that forbids committing real secrets.
- US-058 Story accepted remains an operator gate after apply (operator actually runs the review).

**Non-Goals:**

- US-057 live key rotation (deferred; do not execute).
- US-059 ownership and rotation cadence.
- Closing BL-024; marking US-057/US-059 Story accepted.
- BL-025 LinkedIn token lifecycle rewrite.
- New auth middleware, secrets vault product, or mandatory CI secret-scanner platform.
- Flow A/B behavior changes; LinkedIn enablement mutation; broad `src/` refactors.
- Deploy / push as part of this change.

## Decisions

1. **Docs/procedure-first for US-058** — Match US-053/US-054/US-055 pattern: written operator procedure now; live operator review is the Story-accepted gate after apply. No required worker code.
   - Alternative: build automated secret scanner + permission reporter in the worker → rejected (user guardrail: thin docs/procedure; no secrets platform).

2. **Canonical ops artifact** — `docs/operations/operational-secrets-permissions-review.md` as the operator-facing SoT. Thin pointer from `docs/deployment/ubuntu-server-worker-deployment.md` (near existing rotation section) so deploy readers find the review without duplicating rotation steps.
   - Alternative: only extend the rotation section in deployment docs → conflates review with rotation; rejected given US-057 deferred independence.
   - Alternative: put everything only under `docs/deployment/` → acceptable but operations/ matches other operator review procedures (metrics, validation templates).

3. **Single new capability `operational-secrets-permissions-review`** — Documentation/contract requirements with scenarios that verify procedure presence and normative statements (not HTTP). No MODIFIED deltas on `ubuntu-server-worker-deployment`, Flow A/B, LinkedIn publication, or OAuth lifecycle specs.
   - Alternative: bolt US-058 onto `ubuntu-server-worker-deployment` → mixes deploy lifecycle with periodic permissions audit; rejected for story independence and US-059 follow-on clarity.

4. **Permissions scope (secrets-focused, not BL-026)** — Checklist covers who/what can read operational secrets and expected locations/modes (`.env` chmod expectations, secrets dir `700` / files `600`, compose mount narrowing, n8n credential holders, deploy key ro mounts). Do **not** absorb full BL-026 (open ports, ComfyUI exposure, public checkout attack surface) — point to BL-026 as adjacent if needed.
   - Alternative: merge BL-026 into US-058 → scope creep; rejected.

5. **Absence confirmation method** — Written procedure with concrete expectations (e.g. no real values in committed `.env`/workflow JSON; placeholders like `CHANGE_ME_*` or expressions referencing `worker_api_key`; log/response audits use env var names; n8n exports must not embed live Bearer tokens). Optional operator evidence template under `docs/operations/` (copy for dated review). Automated ripgrep/CI MAY be mentioned as optional aids; MUST NOT be required to publish the procedure.
   - Alternative: require new pytest suite that scans entire repo for secret patterns as acceptance → optional later; not required for docs/contract; existing workflow/console secrets audits already cover some surfaces.

6. **Independence from US-057 / US-059** — Procedure MUST state: do not rotate keys as part of this review; if a finding implies rotation, record `finding — remediation required` and defer execution to an approved US-057-style rotation (or future reopen) — do not silently rotate. Ownership/cadence belongs to US-059.
   - Alternative: include cadence tables in US-058 → steals US-059; rejected.

7. **Outcome vocabulary** — Three primary states for each check / overall review:
   - `blocked` — cannot complete (no server access, export unavailable, mount not inspectable)
   - `confirmed clean` — check completed; no secret exposure / permissions match expected least privilege
   - `finding — remediation required` — exposure or excessive permission found; record env var **names** / path classes only — never values
   Incomplete ≠ clean. Deferred rotation (US-057) ≠ US-058 failure.

8. **Product progress discipline** — After apply: mark US-058 Work started when artifacts exist; leave Story accepted / BL-024 / US-059 unchecked until operator gate. Do not check US-058 AC boxes as accepted from docs alone.

## Risks / Trade-offs

- [Risk] Operator pastes real secrets into evidence template committed to git → Mitigation: template banner forbids values; instruct env var names only; CURRENT-STATE / procedure state “never commit real values.”
- [Risk] Apply claimed as Story accepted without running live review → Mitigation: tasks + ops doc state operator review gate; progress checklist leaves Story accepted unchecked.
- [Risk] Accidental reopen of US-057 rotation during apply → Mitigation: explicit non-goals; tasks forbid `.env` / n8n credential mutation; reference rotation docs as context only.
- [Risk] Scope creep into BL-026 / BL-025 → Mitigation: secrets-focused checklist; LinkedIn token lifecycle pointed to BL-025; service exposure to BL-026.
- [Risk] Conflating “procedure published” with “permissions confirmed clean on server” → Mitigation: CURRENT-STATE language: procedure published; live review / Story accepted separate.
- [Trade-off] Manual review vs automated scanner — manual-first is weaker for continuous assurance but matches approved thin scope; US-059 cadence can schedule repeats.

## Migration Plan

1. After explicit approval, `/opsx-apply` writes ops procedure (+ optional evidence template), GLOSSARY/CURRENT-STATE/product pointers, capability via later `/opsx-sync`.
2. No deploy required for docs/contract; live server review is operator-gated and may be blocked without access.
3. Rollback: revert change commit; no data migration; no runtime flag or credential changes.

## Open Questions

- Exact evidence artifact naming (`…-TEMPLATE.md` vs dated copy convention) — resolve at apply with smallest artifact matching metrics-log pattern.
- Whether a one-line pointer in `ubuntu-server-worker-deployment.md` near the rotation section is enough for deploy discoverability — default yes; do not duplicate the full checklist there.
