## Why

Editorial Flow A state now spans campaigns, runs, calendar, blog/LinkedIn artifacts, and images under the editorial mount, but `metadata/backups/` is only an expected empty folder with no defined scope, retention, or integrity contract. Operators cannot yet trust a backup as restorable. US-036 (BL-014 story 1) defines that contract and verification before US-037 restoration drills.

## Goals

- Define the normative **backup scope** for editorial state needed to recover the system.
- Define **retention** (what is kept, how long / how many generations, what is excluded).
- Define and automate **backup integrity verification** with operator-visible, secret-safe outcomes.
- Keep failures and blocked states clearly communicated.
- Prefer documentation + contracts + automated integrity checks over new runtime mutation paths.
- Prefer existing folders/helpers (`metadata/backups/`); no new primary HTTP endpoints unless inspection proves an unavoidable worker gap.
- Leave US-036 / BL-014 open until later acceptance; proposal alone does not accept the story.

## Non-Goals

- **US-037** restoration testing, recovery procedure documentation that mutates editorial state, or live restore drills.
- Live restore drills that mutate production editorial state.
- Git push, deploy, production n8n activation, or enablement-flag changes.
- Reopening **BL-013** / US-033–US-035 concurrency work (fixture-accepted; cite only as preserved context).
- New primary worker HTTP endpoints for backup create/restore unless an unavoidable gap is proven during apply (default: none).
- Backing up secrets (`.env`, API keys, LinkedIn tokens), the public GitHub Pages checkout as a substitute for editorial source, or n8n/postgres stack backups (owned by shared `local-ai-stack` backup-runner).
- Claiming BL-014 complete or marking US-036 accepted from this proposal.

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-014** | Partial (story 1 only) | Full completion outcome remains after US-037 |
| **US-036** | Yes | All six acceptance criteria |
| **US-037** | No | Intentionally excluded — restoration test + recovery procedure |
| **BL-013** | No | Closed; do not reopen or change concurrency contracts |

**US-036 acceptance criteria addressed:**

1. Define backup scope → normative scope inventory (included / excluded paths and artifact classes).
2. Define retention → retention policy for generations under `metadata/backups/` (and any companion manifests).
3. Verify backup integrity → automated integrity check with pass/fail/blocked outcomes.
4. Outcome visible and understandable to the intended user → operator doc + structured integrity report.
5. Failures or blocked states clearly communicated → stable reason codes / messages, secret-safe.
6. Existing completed work not duplicated or unintentionally changed → no BL-013 reopen; no Flow A lifecycle/publication behavior changes.

**Intentionally excluded (US-037):** Test restoration; document the full recovery procedure; protect-via-restore drills for calendar/campaigns/runs/posts/images/LinkedIn artifacts as live mutation exercises.

## What Changes

- Add an operator-facing editorial backup policy document under `docs/operations/` defining scope, retention, integrity verification, visibility, and blocked/failure communication for US-036.
- Add a new OpenSpec capability `editorial-backup-scope-retention-integrity` that normatively requires the policy artifact, scope/retention contracts, integrity verification behavior, and secret-safe reporting.
- Clarify that `metadata/backups/` is the canonical backup root for editorial-state backup artifacts (manifests + archives), without inventing a second primary layout.
- Add automated integrity verification (library + CLI/script and tests) that validates a backup package against the contract without mutating production editorial state.
- Optionally clarify `worker-foundation` documentation of `metadata/backups/` purpose only if requirements must change beyond “folder exists”; prefer additive capability over broadening folder validation into backup logic.
- After demonstrated ACs only (post-apply / acceptance): update CURRENT-STATE and product progress for US-036 in progress — **do not** mark US-036 or BL-014 accepted from proposal or incomplete apply alone.
- Glossary pointer for backup vs restore layers if needed for operator clarity (US-036 definition vs US-037 restoration).

## Capabilities

### New Capabilities

- `editorial-backup-scope-retention-integrity`: Operator-visible contracts for editorial-state backup **scope**, **retention**, and **integrity verification** — including what must/must-not be backed up, where backups live under `metadata/backups/`, retention bounds, automated integrity checks with secret-safe pass/fail/blocked outcomes, and explicit boundary that restoration testing and recovery procedures belong to US-037.

### Modified Capabilities

- `worker-foundation`: Clarify that `metadata/backups/` is the designated root for editorial backup packages/manifests (purpose of the existing expected folder). Do **not** change health/folder validation into backup creation, restore, or mutation behavior. No new env vars or endpoints required for US-036 unless apply proves an unavoidable gap.

## Impact

- **Product:** Advances BL-014 / US-036 only; leaves US-037 and BL-014 open until restoration story acceptance.
- **Docs:** New operator backup policy; CURRENT-STATE / progress updates only after demonstrated criteria (still leave story open until operator acceptance).
- **OpenSpec:** New capability; small additive clarification delta for `worker-foundation`.
- **Worker:** Prefer a read-only integrity verifier module + tests (and optional CLI entry under `scripts/` or `python -m`); **no** new primary HTTP routes by default; **no** production restore mutation in this change.
- **Filesystem:** Uses existing `metadata/backups/`; may define expected backup package layout (manifest + content) under that root.
- **Preserved:** ADR-0001; BL-013 concurrency contracts; Flow A lifecycle, LinkedIn publication guards, operational status/alerts, incomplete-campaign recovery behavior unchanged.
- **Out of band:** Shared-stack backup-runner, GitHub Pages repo backups, and secret stores remain outside editorial backup scope.
