## Why

BL-024 Story 2 (**US-058**) still lacks a written, operator-facing procedure to **review permissions** on operational secrets and to **confirm secrets are absent** from Git, logs, and n8n workflow exports. US-057 key rotation was closed/waived 2026-07-21 (deferred — not performed); secure-storage / permissions / absence review remains open. Without a thin review contract, operators risk ad-hoc scans, pasting credentials into evidence, or conflating this story with live rotation (US-057) or ownership/cadence (US-059).

## What Changes

- Publish an operator-facing **operational secrets permissions + secrets-absence review** procedure under `docs/operations/` (or a clearly linked sibling under `docs/deployment/` if a thin cross-link is cleaner) covering least-privilege review for worker, n8n, Docker/compose, shared mounts, OAuth/token files, deploy keys, and related service access.
- Document a written checklist to confirm secrets are absent from Git, logs/HTTP responses, and workflow exports (placeholders / env var names only — never real `worker_api_key` / tokens).
- Introduce capability `operational-secrets-permissions-review` as documentation/contract requirements (no secrets-management platform, no live key rotation, no auth middleware rewrite).
- Cross-link from CURRENT-STATE / GLOSSARY / light product pointers so the system owner can open and understand the review; optional evidence template that instructs: keep secrets out of git; use env var names only.
- Leave US-057 rotation deferred, US-059 ownership/cadence open, BL-024 open, BL-025 LinkedIn token lifecycle untouched, and Flow A/B / LinkedIn enablement unchanged.

### Goals

- Satisfy **BL-024 / US-058** acceptance criteria as a thin operator permissions + secrets-absence review procedure + documentation/contract (Story accepted still requires operator review after apply).
- Review permissions — least-privilege checklist: who/what can read secrets; expected locations (server-local `.env`, secrets dirs — never commit real values).
- Confirm secrets are absent from Git, logs, and workflow exports — repo scan expectations, log/response secret-safety, n8n export hygiene.
- Make the outcome visible and understandable to the system owner / operator.
- Communicate failures / blocked states clearly (`blocked` when a check cannot be completed vs `confirmed clean` vs `finding — remediation required`) without printing secret values.
- Reuse existing secret-safety norms (no secrets in HTTP responses/docs/commits; env-only keys; ADR-0001 HTTP-only; LinkedIn publication enablement unchanged). Historical rotation procedure and `deploy/server/verify-worker-api-key-rotation.sh` may be referenced as context only.
- Preserve existing completed work — no Flow A/B behavior changes; no US-057 rotation; no US-059 cadence; no BL-025 rewrite; no BL-020/022/023 reopen.

### Non-goals

- Performing live key rotation (US-057 deferred; stays deferred) — do not rotate live keys, rewrite server `.env`, or mutate n8n `worker_api_key`.
- **US-059** — ownership and rotation cadence.
- Closing **BL-024** or marking US-057 / US-059 Story accepted.
- Closing **BL-025 / US-060+** or implementing full LinkedIn token lifecycle.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or auto-publishing LinkedIn.
- Committing real secrets, dumping `.env`, or pasting credentials into docs/logs/exports.
- Broad security redesign, new auth middleware, or unrelated `src/` refactors (default: docs/procedure-only).
- Deploy / push / claiming Story accepted by proposal alone.
- Inventing a secrets-management platform or mandatory automated secret-scanner CI product in this change.

### Acceptance criteria addressed

| US-058 criterion | How this change addresses it |
|---|---|
| Review permissions | Normative ops procedure + least-privilege checklist (worker, n8n, Docker/compose, mounts, OAuth/token files, deploy keys, related access) |
| Confirm secrets absent from Git, logs, and workflow exports | Written checklist/procedure for repo scan, log/response safety, n8n export hygiene |
| Outcome visible and understandable to intended user | Ops artifact + CURRENT-STATE / GLOSSARY / light product pointers |
| Failures or blocked states clearly communicated | Explicit vocabulary: blocked (cannot complete) vs confirmed clean vs finding requiring remediation — no secret values |
| Existing completed work not duplicated or unintentionally changed | Docs/contract-first; no Flow A/B rewrite; no US-057 rotation; US-059 / BL-024 / BL-025 left open as specified |

### Intentionally excluded

- US-057 live key rotation (waived/deferred — do not reopen).
- US-059 ownership + rotation cadence.
- BL-025 LinkedIn token lifecycle formalization.
- Live deploy, Story accepted, or BL-024 close without operator gate.

## Capabilities

### New Capabilities

- `operational-secrets-permissions-review`: Operator-visible normative procedure for **BL-024 / US-058** — review permissions on operational secrets (least privilege; expected locations; who/what can read) and confirm secrets are absent from Git, logs, and n8n workflow exports — including blocked/clean/finding vocabulary and optional evidence template (env var names only) — without requiring live key rotation, a secrets-management platform, auth middleware rewrite, US-059 cadence ownership, or changes to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

### Modified Capabilities

- (none — documentation/contract capability; existing deployment rotation section, Flow A/B, LinkedIn publication, and OAuth lifecycle specs unchanged in requirements; rotation docs remain historical/context pointers only)

## Impact

- **Product:** Advances **BL-024 / US-058** only; leaves US-059 and BL-024 open; does not reopen US-057 rotation; does not mark Story accepted by proposal alone.
- **Docs:** New ops procedure under `docs/operations/` (preferred) with optional thin pointer from `docs/deployment/`; CURRENT-STATE capability-language pointer; GLOSSARY entries as needed; light product cross-links; optional checklist/evidence template.
- **OpenSpec:** New capability under `openspec/specs/` after sync; no requirement deltas that rewrite Flow A/B, LinkedIn publication, or worker auth behavior.
- **Worker / n8n / Docker / enablement:** No required runtime behavior changes; no `.env` mutation; no n8n credential edits; no LinkedIn enablement mutation.
- **Preserved:** ADR-0001 (n8n → HTTP only); ADR-0002 (blog canonical); existing secret-safety norms; historical API-key rotation procedure as context only; US-057 waived status; BL-025 deferred.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-024 / US-058** | Primary — review permissions; confirm secrets absent from Git, logs, workflow exports |
| US-057 | Closed/waived 2026-07-21 — rotation deferred; do **not** reopen or execute rotation in this change |
| US-059 | Explicit follow-up — ownership and rotation cadence; leave open |
| BL-024 | Must remain open until US-058 and US-059 Story accepted |
| BL-025 / US-060+ | Out of scope — LinkedIn token lifecycle; leave open |
| BL-026 | Adjacent (service permissions/exposure) — do not absorb; US-058 stays secrets-focused |
| Historical rotation procedure / `verify-worker-api-key-rotation.sh` | Context only — not US-058 deliverable |
| ADR-0001 / ADR-0002 | HTTP-only orchestration; blog canonical |
