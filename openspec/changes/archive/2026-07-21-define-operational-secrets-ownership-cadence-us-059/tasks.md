## 1. Normative ownership + cadence procedure

- [x] 1.1 Create `docs/operations/operational-secrets-ownership-cadence.md` with ownership + cadence table (worker API key + n8n `worker_api_key` paired @ 90d; provider keys @ 180d; LinkedIn client secret @ 180d / tokens on refresh-failure→BL-025; deploy key @ 1y; US-058 re-audit @ 90d; on-suspicion immediate); owner = system owner; blocked/deferred vocabulary; independence from live rotation apply; pointers to US-058 procedure and historical Worker API key rotation runbook
- [x] 1.2 Add thin cross-link from `docs/operations/operational-secrets-permissions-review.md` to the US-059 ownership/cadence SoT (no checklist duplication)

## 2. Glossary and status pointers

- [x] 2.1 Add concise `docs/GLOSSARY.md` entry for operational secrets ownership/cadence (US-059)
- [x] 2.2 Update `docs/CURRENT-STATE.md`: US-059 procedure published; after Story accepted note BL-024 closable/closed; US-057 remains deferred; do not reopen US-058 as incomplete
- [x] 2.3 Cross-link lightly from `docs/product/backlog.md` / `docs/product/user-stories.md` BL-024 / US-059

## 3. Product progress

- [x] 3.1 Mark US-059 Work started → Story accepted when artifacts match approved table; close BL-024 (all stories done) in progress-checklist and backlog
- [x] 3.2 Check US-059 acceptance criteria in `docs/product/user-stories.md` as Story accepted
- [x] 3.3 Confirm no live key rotation, no `.env`/n8n mutation, no LinkedIn enablement mutation, no Flow A/B changes were introduced

## 4. Verification

- [x] 4.1 Walk US-059 ACs against docs; `git diff --check`; secrets audit (env var names only)
- [x] 4.2 Business validation: system owner recognizes ownership table + cadences + blocked/deferred vocabulary
