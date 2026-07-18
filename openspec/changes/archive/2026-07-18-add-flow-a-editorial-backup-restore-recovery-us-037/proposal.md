## Why

US-036 defined editorial backup **scope**, **retention**, and **integrity verification** under `metadata/backups/`, but operators still cannot prove that a pass-integrity package can restore editorial state, and there is no recovery runbook. US-037 (BL-014 story 2) closes that gap with restoration drills and a documented recovery procedure — without reopening the US-036 contracts.

## Goals

- Define and automate **restoration drills** against verified US-036 packages under `metadata/backups/` (prefer fixtures / non-production trees first).
- Document the **operator recovery procedure** (runbook) for restoring editorial state from a pass-integrity backup.
- Ensure **protected classes** match US-036 included scope: editorial-calendar, metadata/campaigns, metadata/runs, blog-posts/*, linkedin-posts/*, prompts, co-located images/binaries.
- Communicate restore outcomes with **pass / fail / blocked** (or equivalent) and secret-safe reporting.
- Prefer **docs + library/CLI** over new primary FastAPI routes; n8n MUST NOT use Execute Command (ADR-0001).
- Leave **US-037 / BL-014 open** until later acceptance after demonstrated ACs; proposal alone does not accept the story or close the backlog item.

## Non-Goals

- Reopen or alter **US-036** scope/retention/integrity contracts except **additive** restore references (pointer that restore belongs here).
- Reopen **BL-013** / US-033–US-035 concurrency work.
- Treat the public **GitHub Pages checkout** as the editorial restore source of truth.
- Restore **secrets** (`.env`, tokens) into editorial trees; secret-safe reports only.
- **Git push**, deploy, or production n8n activation inside this change.
- Live restore mutation of **production** editorial state without explicit operator approval and controlled procedure — fail closed by default; prefer dry-run / fixture restore first.
- Shared-stack **backup-runner**, worker source/Docker images, or claiming **BL-014 closed** from proposal alone.
- New primary worker HTTP endpoints for restore unless apply proves an unavoidable gap (default: none).

## Backlog / acceptance criteria

| ID | In scope | Notes |
|----|----------|-------|
| **BL-014** | Partial (story 2 only) | Completion outcome requires both stories; leave closed unchecked |
| **US-036** | No (prerequisite only) | Archived/synced; do not reopen contracts except additive restore pointer |
| **US-037** | Yes | All six acceptance criteria |
| **BL-013** | No | Closed; do not reopen |

**US-037 acceptance criteria addressed:**

1. Test restoration → automated restore drills against pass-integrity packages (fixtures first; dry-run before any live mutation).
2. Document the recovery procedure → operator runbook for restore from a verified backup.
3. Protect calendar, campaigns, runs, posts, images, and LinkedIn artifacts → restore covers US-036 included scope classes (and fails/blocked when package/integrity/guards prevent safe restore).
4. Outcome visible and understandable to the intended user → runbook + structured restore report.
5. Failures or blocked states clearly communicated → stable reason codes / messages, secret-safe.
6. Existing completed work not duplicated or unintentionally changed → no US-036 contract rewrite; no BL-013 reopen; no Flow A lifecycle/publication behavior changes.

**Intentionally excluded:** US-036 scope/retention/integrity redefinition; live production restore without explicit approval; shared-stack/secret restore; claiming BL-014 closed.

## What Changes

- Add an operator-facing **recovery procedure** document under `docs/operations/` (restore drills + live restore gates, referencing US-036 integrity as prerequisite).
- Add a new OpenSpec capability `editorial-backup-restore-recovery` that normatively requires restore-drill behavior, protected-class coverage, recovery runbook, secret-safe pass/fail/blocked outcomes, and fail-closed live-mutation defaults.
- Extend the existing editorial backup library/CLI with **restore / restore-drill** operations that:
  - require a US-036 integrity `pass` (or equivalent precheck) before mutating a restore target;
  - prefer writing into a **fixture / staging target tree** (or dry-run) rather than production editorial trees;
  - never restore secrets or treat public checkout as source of truth.
- Add automated tests for restore drill pass/fail/blocked paths and protected-class coverage on fixtures.
- Optionally add a **small additive** delta to `editorial-backup-scope-retention-integrity` that points operators to US-037 for restore (no scope/retention/integrity requirement changes).
- After demonstrated ACs only (post-apply / acceptance): update CURRENT-STATE and product progress for US-037 in progress — **do not** mark US-037 Story accepted or BL-014 closed from proposal or incomplete apply alone.
- GLOSSARY already distinguishes US-036 integrity vs US-037 restoration; update only if restore outcome language needs a short pointer.

## Capabilities

### New Capabilities

- `editorial-backup-restore-recovery`: Operator-visible contracts for editorial-state **restoration testing** and **recovery procedure** (BL-014 / US-037) — restore drills against verified packages under `metadata/backups/`, protected US-036 scope classes, dry-run / fixture-first defaults, fail-closed live mutation, secret-safe `pass` / `fail` / `blocked` reporting, and an explicit boundary that US-036 remains definition/verify only.

### Modified Capabilities

- `editorial-backup-scope-retention-integrity`: **Additive only** — clarify that restoration drills and the recovery procedure are owned by US-037 / `editorial-backup-restore-recovery`, without changing scope, retention, integrity verification, package layout, or reason-code contracts.

## Impact

- **Product:** Advances BL-014 / US-037 only; leaves US-037 Story accepted and BL-014 closed unchecked until later operator acceptance.
- **Docs:** New recovery runbook; CURRENT-STATE / progress updates only after demonstrated criteria (still leave story/backlog open until acceptance).
- **OpenSpec:** New restore/recovery capability; optional additive pointer delta on US-036 capability.
- **Worker:** Prefer library + CLI extension of `scripts/editorial_backup.py` / `editorial_backup_integrity.py` (or sibling restore module); **no** new primary HTTP routes by default; **no** unattended production restore mutation.
- **Filesystem:** Reads pass-integrity packages under `metadata/backups/`; restore drills write to fixture/staging targets by default; live production tree mutation only under explicit operator approval + documented fail-closed gates.
- **Preserved:** US-036 integrity contracts; ADR-0001; BL-013 concurrency; Flow A lifecycle, LinkedIn publication guards, operational status/alerts unchanged.
- **Out of band:** Shared-stack backup-runner, GitHub Pages as restore SoT, secret stores, deploy/push/n8n activation.
