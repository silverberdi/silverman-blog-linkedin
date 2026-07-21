## 1. Normative permissions + secrets-absence procedure

- [x] 1.1 Create `docs/operations/operational-secrets-permissions-review.md` covering: least-privilege permissions checklist (worker, n8n including `worker_api_key` holders, Docker/compose mounts, OAuth/token files + secrets dirs, deploy keys / known_hosts, related secret-read access); expected locations (server-local `.env`, host secrets directory / documented container mounts — never commit real values); secrets-absence checklist for Git, logs/HTTP responses, and n8n workflow exports (placeholders / env var names only); outcome vocabulary (`blocked` / `confirmed clean` / `finding — remediation required`) without printing secret values; explicit independence from US-057 live rotation, US-059 ownership/cadence, BL-025 token lifecycle, BL-026 full exposure, Flow A/B behavior, and `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation; context-only pointers to historical Worker API key rotation section and `deploy/server/verify-worker-api-key-rotation.sh` (do not invoke as required US-058 steps)
- [x] 1.2 Add a lightweight optional evidence/checklist template under `docs/operations/` (sibling `…-TEMPLATE.md` or appendix) that instructs: keep secrets out of git; use env var names only in committed evidence; record per-check outcome states from 1.1
- [x] 1.3 Add a thin discoverability cross-link from `docs/deployment/ubuntu-server-worker-deployment.md` (near Worker API key rotation) pointing to the US-058 ops procedure — do not duplicate rotation steps or instruct live key rotation as part of US-058

## 2. Glossary and status pointers

- [x] 2.1 Add concise `docs/GLOSSARY.md` entries as needed for **operational secrets permissions review (US-058)** and the blocked/clean/finding vocabulary — do not redefine `flow_a_complete`, handoff vs published, or LinkedIn enablement
- [x] 2.2 Update `docs/CURRENT-STATE.md` to note operational secrets permissions + secrets-absence review **procedure published** (US-058 docs) and that live operator review / Story accepted remain pending; US-057 rotation remains deferred; US-059 ownership/cadence not defined; do not close BL-024; do not claim secrets confirmed clean on the server from docs alone
- [x] 2.3 Cross-link lightly from `docs/product/backlog.md` / `docs/product/user-stories.md` BL-024 / US-058 section (pointer only) — do not mark Story accepted or close BL-024

## 3. Product progress (post-doc, not Story accepted)

- [x] 3.1 Mark US-058 Work started in `docs/product/progress-checklist.md` after procedure artifacts exist; leave Story accepted / BL-024 / US-059 unchecked
- [x] 3.2 Do **not** check off US-058 acceptance criteria in `docs/product/user-stories.md` as Story accepted; leave checkboxes for operator review after apply (operator runs the live permissions + absence review)
- [x] 3.3 Confirm no live key rotation, no server `.env` rewrite, no n8n `worker_api_key` mutation, no Flow A/B pipeline changes, no LinkedIn enablement mutation, no US-059 cadence definition, and no BL-024 / BL-025 / BL-026 close were introduced by this change

## 4. Verification

- [x] 4.1 Walk US-058 acceptance criteria against the committed docs and record any gap (docs/procedure-first; full pytest not required unless unexpected executable code ships)
- [x] 4.2 Run `git diff --check` on changed files; stage-time secrets audit on new/modified files (no real credentials in docs/templates)
- [x] 4.3 Business validation: system owner can open the US-058 ops procedure and CURRENT-STATE pointer and recognize permissions checklist, secrets-absence checks (Git/logs/exports), and blocked/clean/finding vocabulary — Story accepted remains an explicit operator gate after the live review is performed (or recorded as blocked where access is unavailable)
