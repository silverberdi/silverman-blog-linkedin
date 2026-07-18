# Editorial Backup Restore and Recovery Procedure (US-037)

Operator recovery procedure for **BL-014 / US-037** only: **test restoration**
and **recover editorial state** from a verified backup package under
`metadata/backups/`.

## Status

- **Accepted 2026-07-18** against automated fixture restore drills and this
  runbook.
- **BL-014 closed 2026-07-18** after US-036 + US-037 acceptance.
- Live production restore remains fail-closed and confirmation-gated; acceptance
  did **not** require mutating a production editorial mount. Evidence:
  [bl-014-editorial-backup-restore-acceptance-2026-07-18.md](bl-014-editorial-backup-restore-acceptance-2026-07-18.md).

**US-036 boundary:** integrity verification (`pass` / `fail` / `blocked`),
scope, retention, and package layout remain US-036 — see
[editorial-backup-scope-retention-integrity.md](editorial-backup-scope-retention-integrity.md).
US-037 consumes packages that already integrity-`pass`; it does not redefine
verify contracts.

Policy terms: [GLOSSARY.md](../GLOSSARY.md) (editorial backup integrity vs
restoration / recovery procedure). Change artifacts (archived):
`openspec/changes/archive/2026-07-18-add-flow-a-editorial-backup-restore-recovery-us-037/`.

## Purpose

Protect recovery of the editorial system by:

1. Running **fixture / dry-run restore drills** against integrity-`pass` packages.
2. Documenting **fail-closed live restore** gates (explicit confirmation).
3. Restoring **protected classes** matching US-036 included scope.
4. Communicating restore outcomes as `pass` / `fail` / `blocked` with stable
   `restore_*` reason codes (secret-safe).

Restore runs via the Python library and CLI (`scripts/editorial_backup.py`
restore subcommands). There are **no** new primary FastAPI restore routes.
n8n must **not** use Execute Command for restore (ADR-0001).

Git push, GitHub Pages deploy, and LinkedIn API publication are **not** part
of editorial restore.

## Prerequisites

Before any restore mutation (fixture drill or live):

1. Identify `backup_id` under `{editorial_base}/metadata/backups/<backup_id>/`.
2. Run US-036 integrity verification and obtain `status == "pass"`:

```bash
python scripts/editorial_backup.py verify \
  --base-path /path/to/editorial \
  --backup-id editorial-backup-20260718T120000Z-ab12cd
```

3. Choose target type:
   - **Fixture / staging** — preferred for drills (`restore-drill --target-base ...`).
   - **Live editorial mount** — only with explicit confirmation and a fresh
     pre-restore backup (see Live restore below).

Integrity not-`pass`, missing package, or missing live confirmation → restore
`blocked` (no target writes).

## Fixture and dry-run restore drills

Prefer automated fixtures and dry-run before any production mutation.

### Dry-run (no writes)

```bash
python scripts/editorial_backup.py restore-dry-run \
  --base-path /path/to/editorial \
  --backup-id editorial-backup-20260718T120000Z-ab12cd \
  --target-base /path/to/fixture-or-staging
```

Plans coverage against the package; does not write into the target tree.

### Restore-drill (explicit target)

```bash
python scripts/editorial_backup.py restore-drill \
  --base-path /path/to/editorial \
  --backup-id editorial-backup-20260718T120000Z-ab12cd \
  --target-base /path/to/fixture-or-staging
```

Materializes package `content/` into the **explicit** `--target-base` only.
Never implies overwrite of the production editorial mount. If
`--target-base` resolves to the same path as `--base-path` (package host),
the operation is **blocked** as an unsafe live-looking target unless a live
restore with confirmation is used instead.

Automated tests demonstrate drills against temporary fixture trees (campaigns,
calendar, LinkedIn artifacts, co-located images when present).

## Live restore (fail-closed)

Live overwrite of a production editorial base requires:

1. Fresh integrity-`pass` package (and preferably a new backup taken immediately
   before restore for rollback evidence).
2. Explicit CLI confirmation: `--i-understand-live-restore`.
3. Operator acknowledgment that restore does **not** publish the blog or LinkedIn.

```bash
python scripts/editorial_backup.py restore \
  --base-path /path/to/editorial \
  --backup-id editorial-backup-20260718T120000Z-ab12cd \
  --target-base /path/to/editorial \
  --i-understand-live-restore
```

Without `--i-understand-live-restore`, live restore is **blocked**
(`restore_live_confirmation_required`) and no production files are written.

Default posture: refuse unattended / automation-driven production mutation.

## Protected classes (US-036 included scope)

When present in the pass-integrity package, restore covers:

| Relative path / class | Notes |
|----------------------|--------|
| `blog-posts/{ready,queued,processed,error}/` | Editorial sources |
| `linkedin-posts/{review,approved,published}/` | Distribution artifacts |
| `metadata/campaigns/` | Campaign lifecycle |
| `metadata/runs/` | Run records |
| `editorial-calendar/` (including `calendar.json`) | Planning state |
| `prompts/` | Prompt assets |
| Images/binaries **inside** those trees | Co-located media |

## Exclusions

| Exclusion | Why |
|-----------|-----|
| Secrets (`.env`, tokens, credential files) | Never restore into editorial trees; secret-safe reports only |
| Public GitHub Pages checkout | Handoff / live site ≠ editorial restore source of truth |
| Shared-stack services / backup-runner | Outside editorial mount |
| Recursive `metadata/backups/` package contents as source | Packages are read-only restore inputs; restore does not mutate them |

## Restore outcomes

| Status | Meaning |
|--------|---------|
| `pass` | Dry-run validated or restore/drill completed with post-checks OK |
| `fail` | Contract violation after starting (e.g. postcheck hash mismatch, secret path write attempt) |
| `blocked` | Prerequisite or policy gate refused (integrity not pass, missing package, live confirmation required, unsafe target) |

### Stable reason codes (`restore_*`)

| Code | Typical status |
|------|----------------|
| `restore_integrity_not_pass` | `blocked` |
| `restore_package_missing` | `blocked` |
| `restore_live_confirmation_required` | `blocked` |
| `restore_target_unsafe` | `blocked` |
| `restore_secret_path_refused` | `fail` / `blocked` |
| `restore_postcheck_hash_mismatch` | `fail` |
| `restore_scope_class_incomplete` | `fail` |

Library result shape (secret-safe): `status`, `reason_codes` (empty on clean
`pass`), summary counts (`files_planned`, `files_restored`, `mismatch_count`),
relative paths only — no content bodies, tokens, or `.env` values.

```python
from silverman_blog_linkedin.editorial_backup_restore import restore_editorial_backup

result = restore_editorial_backup(
    base_path,
    backup_id,
    mode="restore_drill",
    target_base=fixture_base,
)
# result.status in {"pass", "fail", "blocked"}
```

## Operator visibility

Operators interpret outcomes from:

1. This recovery procedure (gates, protected classes, exclusions).
2. Structured CLI/library JSON: `status`, `reason_codes`, summary counts,
   relative paths only.
3. US-036 integrity reports for the prerequisite verify step.

## Explicit non-goals of restore

- Git commit/push to the public blog remote
- GitHub Pages deploy / “site is live”
- LinkedIn API publication
- Restoring secrets or treating the public checkout as restore SoT
- New primary worker HTTP restore endpoints
- Claiming US-037 Story accepted or BL-014 closed from this runbook text alone
  without the acceptance record (acceptance is recorded in
  [bl-014-editorial-backup-restore-acceptance-2026-07-18.md](bl-014-editorial-backup-restore-acceptance-2026-07-18.md))

## Related

- US-036 policy: [editorial-backup-scope-retention-integrity.md](editorial-backup-scope-retention-integrity.md)
- GLOSSARY: integrity (US-036) vs restoration/recovery (US-037)
- CLI: `scripts/editorial_backup.py` (`restore-dry-run`, `restore-drill`, `restore`)
