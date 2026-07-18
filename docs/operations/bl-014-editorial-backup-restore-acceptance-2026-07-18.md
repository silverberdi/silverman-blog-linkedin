# BL-014 / US-036 + US-037 — operator acceptance (2026-07-18)

Operator acceptance of **Establish Backup and Restore for Editorial State**
against automated fixture evidence and operator policy/recovery artifacts.

## Status

- **US-036** and **US-037** acceptance criteria **validated** and stories
  **accepted** 2026-07-18 (fixture evidence + operator review of policy/runbook).
- **BL-014 closed 2026-07-18.**
- **Not** a claim that live production restore has been executed on
  `192.168.0.194`. Live restore remains fail-closed and confirmation-gated per
  [editorial-backup-restore-recovery.md](editorial-backup-restore-recovery.md).
- Baseline commit reviewed: `86675bd` (US-037 archived on `main`).

## Evidence

| Artifact | Role |
|----------|------|
| [editorial-backup-scope-retention-integrity.md](editorial-backup-scope-retention-integrity.md) | US-036 operator policy (scope, retention, integrity) |
| [editorial-backup-restore-recovery.md](editorial-backup-restore-recovery.md) | US-037 recovery procedure |
| `tests/test_editorial_backup_integrity.py` | US-036 automated fixtures |
| `tests/test_editorial_backup_restore.py` | US-037 automated restore drills |
| Canonical specs | `openspec/specs/editorial-backup-scope-retention-integrity/`, `openspec/specs/editorial-backup-restore-recovery/` |

**Pytest (acceptance re-run):** `26 passed` at `2026-07-18T14:39:13Z`
(`test_editorial_backup_integrity` + `test_editorial_backup_restore`).

## US-036 acceptance walkthrough

| Criterion | Evidence |
|-----------|----------|
| Define backup scope | Policy included/excluded inventory; `INCLUDED_SCOPE_CLASSES` + builder/verify tests |
| Define retention | Keep 7 most recent pass packages; never auto-delete fail/blocked — prune tests |
| Verify backup integrity | `verify` pass/fail/blocked + stable `backup_*` reason codes |
| Outcome visible/understandable | Policy + CLI/library JSON (`status`, `reason_codes`, counts, relative paths) |
| Failures/blocked clearly communicated | Distinct `pass` / `fail` / `blocked` with reason codes |
| Existing work not duplicated/changed | No primary HTTP backup routes; health unchanged; restore deferred to US-037 |

## US-037 acceptance walkthrough

| Criterion | Evidence |
|-----------|----------|
| Test restoration | Fixture restore-drill `pass`; integrity not-pass / missing package / dry-run / live-without-confirmation → `blocked` |
| Document the recovery procedure | Recovery runbook present with gates, exclusions, reason codes |
| Protect calendar, campaigns, runs, posts, images, LinkedIn | Drill restores US-036 included classes including co-located image |
| Outcome visible/understandable | Runbook + restore report shape (`status`, `restore_*` codes) |
| Failures/blocked clearly communicated | Secret refusal, postcheck mismatch `fail`; prerequisite gates `blocked` |
| Existing work not duplicated/changed | US-036 contracts additive pointer only; no FastAPI restore; no BL-013 reopen |

## Explicit non-claims

- Public GitHub Pages checkout is **not** the editorial restore source of truth.
- Secrets are **not** restored into editorial trees.
- Git push / Pages deploy / LinkedIn API publication are **not** part of restore.
- Shared-stack backup-runner remains out of scope.
- Production live restore was **not** required for this acceptance.
